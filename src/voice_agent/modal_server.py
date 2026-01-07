"""
FastAPI WebSocket Server for Voice Agent (Modal version).
Uses the unified Modal endpoint for all processing.

Implements NeMo-style server-side turn management:
- bot_speaking flag to track agent state
- bot_stop_delay debouncing to prevent echo
- VAD reset on turn complete
"""

import asyncio
import base64
import os
import time
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Configuration
UNIFIED_ENDPOINT = os.environ.get(
    "UNIFIED_ENDPOINT",
    "https://akshaymp-1810--unified-voice-agent-unifiedvoiceagent-process.modal.run",
)
LANGUAGE_CODE = "kn"
LANGUAGE_SCRIPT = "kan_Knda"

# Turn-taking configuration (inspired by NeMo)
BOT_STOP_DELAY = 0.5  # seconds to wait after TTS before accepting new input

app = FastAPI(
    title="Kannada Voice Agent (Modal)",
    description="Real-time Kannada voice assistant deployed on Modal",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "voice-agent-modal"}


async def process_audio_unified(audio_bytes: bytes) -> dict:
    """
    Send audio to the unified Modal endpoint for full pipeline processing.

    Returns:
        dict with transcription, translations, and audio response
    """
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            UNIFIED_ENDPOINT,
            json={
                "audio_b64": audio_b64,
                "language": LANGUAGE_CODE,
                "src_lang": LANGUAGE_SCRIPT,
                "tgt_lang": LANGUAGE_SCRIPT,
            },
        )
        response.raise_for_status()
        return response.json()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice communication."""
    await websocket.accept()
    print("🔌 Client connected")

    try:
        # Initialize VAD
        from .vad import SileroVAD
        import torch

        # Ensure cache dir matches download_vad
        torch.hub.set_dir("/root/.cache/torch")

        vad = SileroVAD()
        print("🎤 VAD Initialized")

        # NeMo-style turn management state
        bot_speaking = False
        bot_stop_time = None

        while True:
            # Receive audio chunk (streaming)
            audio_bytes = await websocket.receive_bytes()

            # Check if bot has finished speaking + delay has passed
            if bot_speaking:
                if bot_stop_time and (time.time() - bot_stop_time > BOT_STOP_DELAY):
                    # Delay passed, ready to accept new input
                    bot_speaking = False
                    bot_stop_time = None
                    print("🎤 Ready for new input (bot_stop_delay passed)")
                else:
                    # Still in "bot speaking" window - discard audio
                    # Don't even feed it to VAD to avoid accumulating stale buffer
                    continue

            # VAD Processing (only when not bot_speaking)
            utterance = vad.process_chunk(audio_bytes)

            if utterance:
                print(f"🎤 Utterance detected: {len(utterance)} bytes")

                # Mark bot as speaking (processing + TTS)
                bot_speaking = True

                # Send processing start event to UI
                await websocket.send_json({"type": "processing_start"})

                try:
                    # Process through unified endpoint
                    result = await process_audio_unified(utterance)

                    # Send timings first if available
                    if "timings" in result:
                        await websocket.send_json(
                            {"type": "timings", "data": result["timings"]}
                        )

                    # Send transcription event
                    await websocket.send_json(
                        {
                            "type": "stt_output",
                            "data": {
                                "transcript": result.get("transcription", ""),
                                "language": LANGUAGE_CODE,
                            },
                        }
                    )

                    # Send translation (indic -> en) event
                    await websocket.send_json(
                        {
                            "type": "translation",
                            "data": {
                                "text": result.get("translated_en", ""),
                                "direction": "indic_to_en",
                            },
                        }
                    )

                    # Send agent response event
                    await websocket.send_json(
                        {
                            "type": "agent_end",
                            "data": {
                                "full_response": result.get("agent_response_en", ""),
                            },
                        }
                    )

                    # Send translation (en -> indic) event
                    await websocket.send_json(
                        {
                            "type": "translation",
                            "data": {
                                "text": result.get("response_indic", ""),
                                "direction": "en_to_indic",
                            },
                        }
                    )

                    # Send TTS audio
                    audio_b64 = result.get("audio_b64", "")
                    if audio_b64:
                        audio_response = base64.b64decode(audio_b64)
                        await websocket.send_json(
                            {"type": "tts_chunk", "data": {"has_audio": True}}
                        )
                        await websocket.send_bytes(audio_response)

                    # Signal turn complete and start bot_stop_delay timer
                    await websocket.send_json({"type": "tts_complete", "data": {}})
                    bot_stop_time = time.time()
                    print(f"✅ Turn Complete - starting {BOT_STOP_DELAY}s delay")

                    # Reset VAD to clear any residual buffered audio
                    vad.reset()

                except Exception as e:
                    print(f"❌ Processing error: {e}")
                    await websocket.send_json(
                        {"type": "error", "data": {"message": str(e)}}
                    )
                    # Reset state on error
                    bot_speaking = False
                    bot_stop_time = None
                    vad.reset()

    except WebSocketDisconnect:
        print("🔌 Client disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")


# Mount static files for frontend
frontend_path = "/root/src/web/dist"
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
else:

    @app.get("/")
    async def home():
        return HTMLResponse(
            "<h1>Voice Agent API</h1>"
            "<p>Frontend not available. Use the /ws WebSocket endpoint.</p>"
            f"<p>Unified endpoint: {UNIFIED_ENDPOINT}</p>"
        )
