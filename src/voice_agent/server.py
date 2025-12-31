"""
FastAPI WebSocket Server for Voice Agent.
Real-time voice communication with pipeline.
"""
import asyncio
import wave
import io
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import AsyncIterator

from .pipeline import full_pipeline
from .events import event_to_dict, TTSChunkEvent
from .config import SAMPLE_RATE


app = FastAPI(
    title="Kannada Voice Agent",
    description="Real-time Kannada voice assistant with Gemini + Google Search",
    version="1.0.0",
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
    return {"status": "healthy", "service": "voice-agent"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice communication."""
    await websocket.accept()
    print("🔌 Client connected")
    
    # Queue for incoming audio chunks
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
    
    async def audio_receiver():
        """Receive audio from WebSocket and queue it."""
        try:
            while True:
                data = await websocket.receive_bytes()
                await audio_queue.put(data)
        except WebSocketDisconnect:
            print("🔌 Client disconnected")
        except Exception as e:
            print(f"Receiver error: {e}")
    
    async def audio_stream() -> AsyncIterator[bytes]:
        """Async generator that yields audio from queue."""
        while True:
            try:
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=120.0)
                yield chunk
            except asyncio.TimeoutError:
                break
    
    # Start receiver task
    receiver_task = asyncio.create_task(audio_receiver())
    
    try:
        # Process audio through pipeline
        async for event in full_pipeline(audio_stream()):
            # Send event as JSON
            await websocket.send_json(event_to_dict(event))
            
            # If TTS audio, also send the raw bytes
            if isinstance(event, TTSChunkEvent) and event.audio:
                await websocket.send_bytes(event.audio)
                
    except WebSocketDisconnect:
        print("🔌 Client disconnected during processing")
    except Exception as e:
        print(f"Pipeline error: {e}")
    finally:
        receiver_task.cancel()
        try:
            await receiver_task
        except asyncio.CancelledError:
            pass



from fastapi.staticfiles import StaticFiles
import os

# Mount static files (at the end to ensure other routes take precedence)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "web", "dist")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
else:
    print(f"⚠️ Frontend not found at {frontend_path}")
    @app.get("/")
    async def home():
        return HTMLResponse("<h1>Frontend build not found. Run 'npm run build' in src/web</h1>")

def main():
    """Run the server."""
    import uvicorn
    print("🚀 Starting Kannada Voice Agent...")
    print("📍 Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
