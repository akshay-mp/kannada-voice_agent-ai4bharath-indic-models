
import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List
from uuid import uuid4

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableGenerator
# from langchain_google_genai import ChatGoogleGenerativeAI  # Commented for quota limits
from langchain_openai import ChatOpenAI
import os
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from starlette.staticfiles import StaticFiles

from elevenlabs_stt import ElevenLabsSTT
from elevenlabs_tts import ElevenLabsTTS
from events import (
    AgentChunkEvent,
    AgentEndEvent,
    ToolCallEvent,
    ToolResultEvent,
    VoiceAgentEvent,
    event_to_dict,
)
from utils import merge_async_iters
from logger import logger
from middleware import RequestLoggerMiddleware
from memory import init_memory, update_user_profile, get_user_profile

load_dotenv()

STATIC_DIR = Path(__file__).parent.parent / "web" / "dist"

if not STATIC_DIR.exists():
    logger.warning(f"Static dir {STATIC_DIR} not found.")


# Global state
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    # Initialize long-term memory DB (for user preferences)
    await init_memory()
    
    # Use InMemorySaver for short-term session memory (reliable, no external deps)
    checkpointer = InMemorySaver()
    
    # Initialize Agent with memory tools
    agent = create_react_agent(
        model=llm,
        tools=[add_to_order, confirm_order, save_preference, get_preference],
        prompt=system_prompt,
        checkpointer=checkpointer,
    )
    logger.info("Agent initialized with InMemorySaver + SQLite long-term memory tools.")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggerMiddleware)


def add_to_order(item: str, quantity: int) -> str:
    """Add an item to the customer's sandwich order."""
    return f"Added {quantity} x {item} to the order."


def confirm_order(order_summary: str) -> str:
    """Confirm the final order with the customer."""
    return f"Order confirmed: {order_summary}. Sending to kitchen."


async def save_preference(preference: str) -> str:
    """Save a user preference (e.g., favorite food, dietary restriction) for future reference."""
    # Using a default user_id for now since we don't have auth
    await update_user_profile("default_user", preference)
    return "Preference saved."


async def get_preference() -> str:
    """Get stored user preferences to personalize recommendations."""
    prefs = await get_user_profile("default_user")
    return f"User preferences: {prefs}" if prefs else "No preferences found."


system_prompt = """
You are a helpful sandwich shop assistant. Your goal is to take the user's order.
Be concise and friendly.

Available toppings: lettuce, tomato, onion, pickles, mayo, mustard.
Available meats: turkey, ham, roast beef.
Available cheeses: swiss, cheddar, provolone.
"""

# Initialize Gemini Agent (commented out due to quota limits)
# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-pro",
#     temperature=0,
#     streaming=True
# )

# Initialize OpenAI-compatible LLM via NEBIUS Router
llm = ChatOpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
    model="Qwen/Qwen3-235B-A22B-Instruct-2507",
    temperature=0,
    streaming=True,
)


async def _stt_stream(
    audio_stream: AsyncIterator[bytes],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Transform stream: Audio (Bytes) -> Voice Events (VoiceAgentEvent)
    
    Uses ElevenLabs real-time STT with VAD for automatic turn detection.
    """
    stt = ElevenLabsSTT(sample_rate=16000, language_code="kan")

    async def send_audio():
        """Background task that sends audio chunks to STT."""
        try:
            async for audio_chunk in audio_stream:
                await stt.send_audio(audio_chunk)
        finally:
            await stt.close()

    send_task = asyncio.create_task(send_audio())

    try:
        async for event in stt.receive_events():
            if event.type == "stt_chunk":
                logger.info(f"[STT] Partial: {event.transcript}")
            elif event.type == "stt_output":
                logger.info(f"[STT] Final: {event.transcript}")
            yield event
    finally:
        with contextlib.suppress(asyncio.CancelledError):
            send_task.cancel()
            await send_task
        await stt.close()


import uvicorn
import httpx
from dotenv import load_dotenv

# ... (imports)

# TRANSLATION_API_URL = "https://akshaymp-1810--ambari-translator-ambarimodel-translate-api-dev.modal.run"
# New URL for vLLM server (Adjust workspace name if needed, assuming same workspace 'akshaymp-1810')
TRANSLATION_API_URL = "https://akshaymp-1810--ambari-translator-vllm-serve.modal.run/v1/completions"

PROMPT_TEMPLATE = """Instruction: translate user query to english
Input: ನನಗೆ ಅಕ್ಕಿ ಬೇಕು.
Output: I want rice.

Instruction: translate user query to english
Input: ನನಗೆ Apple ಫೋನ್ ಬೇಕು.
Output: I want an Apple phone.

Instruction: translate user query to english
Input: ನನಗೆ ಕ್ಯಾಶ್ಯೂ ನಟ್ಸ್ ಬೇಕು.
Output: I want cashew nuts.

Instruction: translate user query to english
Input: ಜಾಗ್ವಾರ್ ಕಾರು ಸೂಪರ್ ಆಗಿದೆ.
Output: The Jaguar car is super.

Instruction: translate user query to english
Input: ಆಫೀಸ್ ಗೆ ಲೇಟ್ ಆಯ್ತು.
Output: I am late for the office.

Instruction: translate LLM response to kanglish
Input: Here is your order.
Output: ಇಲ್ಲಿ ನಿಮ್ಮ ಆರ್ಡರ್ ಇದೆ.

Instruction: translate LLM response to kanglish
Input: Payment is successful.
Output: Payment ಯಶಸ್ವಿಯಾಗಿದೆ.

Instruction: {}
Input: {}
Output:"""

from langsmith import traceable

@traceable(run_type="tool", name="Ambari Translation")
async def translate_text(text: str, direction: str) -> str:
    if not text:
        return ""
    
    instruction = ""
    if direction == "to_english":
        instruction = "translate user query to english"
    elif direction == "to_kanglish":
        instruction = "translate LLM response to kanglish"
    else:
        logger.error(f"[Translation] Invalid direction: {direction}")
        return text

    prompt = PROMPT_TEMPLATE.format(instruction, text)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                TRANSLATION_API_URL,
                json={
                    "model": "ambari-merged",
                    "prompt": prompt,
                    "max_tokens": 256,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "repetition_penalty": 1.2,
                    # "stop": ["###"] # Optional: Stop if it generates headers
                },
                timeout=60.0,
                headers={"Authorization": "Bearer skipped"} # vLLM on Modal usually no auth unless set
            )
            resp.raise_for_status()
            result = resp.json()
            # OpenAI completion format: {"choices": [{"text": "..."}]}
            translated_text = result["choices"][0]["text"].strip()
            return translated_text
        except Exception as e:
            logger.error(f"[Translation] Error: {e}")
            return text

async def _agent_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Transform stream: Voice Events -> Voice Events (with Agent Responses)
    
    Passes through all events and invokes agent on stt_output events.
    Includes bi-directional translation (Kanglish <-> English).
    """
    thread_id = str(uuid4())

    async for event in event_stream:
        yield event

        if event.type == "stt_output":
            logger.info(f"[Agent] Processing (original): {event.transcript}")
            
            # 1. Translate Input (Kanglish -> English)
            english_input = await translate_text(event.transcript, "to_english")
            logger.info(f"[Translation] English Input: {english_input}")

            try:
                stream = agent.astream(
                    {"messages": [HumanMessage(content=english_input)]},
                    {"configurable": {"thread_id": thread_id}},
                    stream_mode="messages",
                )

                full_response_buffer = []

                async for message, metadata in stream:
                    if isinstance(message, AIMessage):
                        if message.content:
                            content = message.content
                            # Handle Gemini's list content format
                            text_chunk = ""
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get('type') == 'text':
                                        text_chunk += item.get('text', '')
                                    elif isinstance(item, str) and item:
                                        text_chunk += item
                            elif isinstance(content, str) and content:
                                text_chunk = content
                            
                            if text_chunk:
                                full_response_buffer.append(text_chunk)
                                # We do NOT yield chunks here, we wait for full translation

                        if message.tool_calls:
                            for tool_call in message.tool_calls:
                                logger.info(f"[Agent] Tool call: {tool_call.get('name')}")
                                yield ToolCallEvent.create(
                                    id=tool_call.get("id", str(uuid4())),
                                    name=tool_call.get("name", "unknown"),
                                    args=tool_call.get("args", {}),
                                )

                    elif isinstance(message, ToolMessage):
                        logger.info(f"[Agent] Tool result received")
                        yield ToolResultEvent.create(
                            tool_call_id=message.tool_call_id,
                            name=message.name if hasattr(message, "name") else "unknown",
                            result=str(message.content) if message.content else "",
                        )

                # 2. Translate Output (English -> Kanglish)
                full_english_response = "".join(full_response_buffer)
                if full_english_response:
                    logger.info(f"[Agent] English Response: {full_english_response}")
                    kanglish_response = await translate_text(full_english_response, "to_kanglish")
                    logger.info(f"[Translation] Kanglish Response: {kanglish_response}")
                    
                    # Yield the translated response as a chunk
                    yield AgentChunkEvent.create(kanglish_response)

                logger.info("[Agent] Response complete")
                yield AgentEndEvent.create()
            except Exception as e:
                logger.error(f"[Agent] Error: {type(e).__name__}: {e}", exc_info=True)



async def _tts_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Transform stream: Voice Events -> Voice Events (with Audio)
    
    Creates a fresh TTS connection per turn to handle ElevenLabs timeout.
    Runs TTS in background task so it doesn't block upstream event processing.
    """
    tts_queue: asyncio.Queue[VoiceAgentEvent] = asyncio.Queue()
    active_tts_tasks: List[asyncio.Task] = []
    
    async def synthesize_and_queue(text: str):
        """Run TTS synthesis and put audio events in queue."""
        tts = ElevenLabsTTS(output_format="pcm_24000")
        try:
            logger.info(f"[TTS] Synthesizing: {text[:50]}...")
            await tts.send_text(text)
            await tts.send_text("")  # Signal end of input
            
            async for tts_event in tts.receive_events():
                logger.info(f"[TTS] Audio chunk")
                await tts_queue.put(tts_event)
            
            logger.info("[TTS] Synthesis complete")
        except Exception as e:
            logger.error(f"[TTS] Error: {type(e).__name__}: {e}")
        finally:
            await tts.close()

    buffer: List[str] = []
    
    async def process_upstream():
        """Process upstream events and start TTS tasks."""
        nonlocal buffer
        async for event in event_stream:
            yield event
            
            if event.type == "agent_chunk":
                buffer.append(event.text)
            
            if event.type == "agent_end":
                text = "".join(buffer)
                buffer = []
                
                if text.strip():
                    # Start TTS in background task (non-blocking)
                    task = asyncio.create_task(synthesize_and_queue(text))
                    active_tts_tasks.append(task)
    
    async def drain_tts_queue():
        """Continuously drain TTS queue and yield events."""
        while True:
            try:
                event = await asyncio.wait_for(tts_queue.get(), timeout=0.05)
                yield event
            except asyncio.TimeoutError:
                # No event available, yield control
                await asyncio.sleep(0)
                continue
    
    # Merge upstream processing with TTS audio events
    try:
        async for event in merge_async_iters(process_upstream(), drain_tts_queue()):
            yield event
    finally:
        # Wait for all active TTS tasks to finish (don't cancel them prematurely)
        # This ensures all audio chunks are sent before cleanup
        for task in active_tts_tasks:
            if not task.done():
                try:
                    await asyncio.wait_for(task, timeout=30.0)  # Wait up to 30s for TTS to finish
                except asyncio.TimeoutError:
                    logger.warning("[TTS] Task timed out, cancelling")
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
                except asyncio.CancelledError:
                    pass
        
        # Drain any remaining audio chunks from the queue
        while not tts_queue.empty():
            try:
                event = tts_queue.get_nowait()
                yield event
            except asyncio.QueueEmpty:
                break


pipeline = (
    RunnableGenerator(_stt_stream)
    | RunnableGenerator(_agent_stream)
    | RunnableGenerator(_tts_stream)
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WS] Connection opened")

    async def websocket_audio_stream() -> AsyncIterator[bytes]:
        """Async generator that yields audio bytes from the websocket."""
        packet_count = 0
        try:
            while True:
                data = await websocket.receive_bytes()
                packet_count += 1
                if packet_count % 100 == 0:
                    logger.debug(f"[WS] Received {packet_count} audio chunks")
                yield data
        except Exception as e:
            logger.info(f"[WS] Audio stream ended: {e}")

    output_stream = pipeline.atransform(websocket_audio_stream())

    try:
        async for event in output_stream:
            await websocket.send_json(event_to_dict(event))
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
    finally:
        logger.info("[WS] Connection closed")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "voice-agent"}


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=False)
