"""
Voice Agent Pipeline.
Async generator-based pipeline for voice sandwich architecture:
VAD → STT → Indic→En → Agent → En→Indic → TTS
"""
from typing import AsyncIterator
from .events import (
    VoiceAgentEvent,
    UserInputEvent,
    STTChunkEvent,
    STTOutputEvent,
    TranslationEvent,
    AgentChunkEvent,
    AgentEndEvent,
    TTSChunkEvent,
)
from . import stt_client, translation_client, tts_client
from .agent import run_agent_sync
from .vad import SileroVAD, vad_stream
from .config import LANGUAGE_CODE, LANGUAGE_SCRIPT


async def stt_stream(
    audio_stream: AsyncIterator[bytes],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    STT Stage: Audio → Kannada text
    
    Args:
        audio_stream: Async iterator of WAV audio bytes (complete utterances from VAD)
    
    Yields:
        STTOutputEvent with Kannada transcription
    """
    async for audio_bytes in audio_stream:
        # Signal start of STT/Turn (Audio Received)
        yield UserInputEvent.create(audio=audio_bytes)
        # Signal STT processing started (for latency tracking)
        yield STTChunkEvent.create(text="")
        try:
            transcript = await stt_client.transcribe(audio_bytes, LANGUAGE_CODE)
            if transcript and transcript.strip():
                print(f"📝 STT: {transcript}")
                yield STTOutputEvent.create(transcript=transcript, language=LANGUAGE_CODE)
        except Exception as e:
            print(f"❌ STT Error: {e}")


async def indic_en_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Translation Stage: Kannada → English
    
    Passes through all events, translates STT output to English.
    
    Args:
        event_stream: Async iterator of upstream events
    
    Yields:
        All upstream events plus TranslationEvent with English text
    """
    async for event in event_stream:
        # Pass through all events
        yield event
        
        # Translate STT output
        if isinstance(event, STTOutputEvent):
            try:
                # Signal translation start
                yield TranslationEvent.create(
                    text="",
                    src_lang=LANGUAGE_SCRIPT,
                    tgt_lang="eng_Latn",
                    direction="indic_to_en",
                )
                
                english_text = await translation_client.translate_indic_to_english(
                    event.transcript, LANGUAGE_SCRIPT
                )
                if english_text and english_text.strip():
                    print(f"🔄 Kannada→En: {english_text}")
                    yield TranslationEvent.create(
                        text=english_text,
                        src_lang=LANGUAGE_SCRIPT,
                        tgt_lang="eng_Latn",
                        direction="indic_to_en",
                    )
            except Exception as e:
                print(f"❌ Translation Error: {e}")


async def agent_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Agent Stage: Process English text, generate response.
    
    Uses Gemini with Google Search to answer questions.
    
    Args:
        event_stream: Async iterator of upstream events
    
    Yields:
        All upstream events plus AgentChunkEvent and AgentEndEvent
    """
    async for event in event_stream:
        # Pass through all events
        yield event
        
        # Process English translation through agent
        if isinstance(event, TranslationEvent) and event.direction == "indic_to_en" and event.text:
            try:
                print(f"🤖 Agent processing: {event.text}")
                # Signal agent start (for latency tracking)
                yield AgentChunkEvent.create(text="")
                
                # Run agent (synchronous for now, can be made async)
                response = run_agent_sync(event.text)
                
                if response and response.strip():
                    # Yield the full response
                    yield AgentChunkEvent.create(text=response)
                    yield AgentEndEvent.create(full_response=response)
                    print(f"🤖 Agent response: {response[:100]}...")
            except Exception as e:
                print(f"❌ Agent Error: {e}")
                yield AgentEndEvent.create(full_response="Sorry, I couldn't process that request.")


async def en_indic_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Translation Stage: English → Kannada
    
    Translates agent response back to Kannada.
    
    Args:
        event_stream: Async iterator of upstream events
    
    Yields:
        All upstream events plus TranslationEvent with Kannada text
    """
    async for event in event_stream:
        # Pass through all events
        yield event
        
        # Translate agent response to Kannada
        if isinstance(event, AgentEndEvent) and event.full_response:
            try:
                # Signal translation start
                yield TranslationEvent.create(
                    text="",
                    src_lang="eng_Latn",
                    tgt_lang=LANGUAGE_SCRIPT,
                    direction="en_to_indic",
                )
                
                kannada_text = await translation_client.translate_english_to_indic(
                    event.full_response, LANGUAGE_SCRIPT
                )
                if kannada_text and kannada_text.strip():
                    print(f"🔄 En→Kannada: {kannada_text[:100]}...")
                    yield TranslationEvent.create(
                        text=kannada_text,
                        src_lang="eng_Latn",
                        tgt_lang=LANGUAGE_SCRIPT,
                        direction="en_to_indic",
                    )
            except Exception as e:
                print(f"❌ Translation Error: {e}")


async def tts_stream(
    event_stream: AsyncIterator[VoiceAgentEvent],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    TTS Stage: Kannada text → Audio
    
    Synthesizes speech from Kannada text.
    
    Args:
        event_stream: Async iterator of upstream events
    
    Yields:
        All upstream events plus TTSChunkEvent with audio
    """
    async for event in event_stream:
        # Pass through all events
        yield event
        
        # Synthesize translated text (skip empty start events)
        if isinstance(event, TranslationEvent) and event.direction == "en_to_indic" and event.text:
            try:
                print(f"🔊 TTS: Synthesizing...")
                # Signal TTS start (for latency tracking)
                yield TTSChunkEvent.create(audio=b"")
                audio_bytes = await tts_client.synthesize(event.text)
                if audio_bytes:
                    yield TTSChunkEvent.create(audio=audio_bytes)
                    print(f"🔊 TTS: Generated {len(audio_bytes)} bytes")
            except Exception as e:
                print(f"❌ TTS Error: {e}")


async def full_pipeline(
    raw_audio_stream: AsyncIterator[bytes],
) -> AsyncIterator[VoiceAgentEvent]:
    """
    Full voice agent pipeline.
    
    VAD → STT → Indic→En → Agent → En→Indic → TTS
    
    Args:
        raw_audio_stream: Async iterator of raw PCM audio chunks
    
    Yields:
        VoiceAgentEvent for each stage
    """
    # Create VAD filtered stream
    vad = SileroVAD()
    utterance_stream = vad_stream(raw_audio_stream, vad)
    
    # Chain the pipeline stages
    stt_events = stt_stream(utterance_stream)
    trans1_events = indic_en_stream(stt_events)
    agent_events = agent_stream(trans1_events)
    trans2_events = en_indic_stream(agent_events)
    tts_events = tts_stream(trans2_events)
    
    # Yield all events from the pipeline
    async for event in tts_events:
        yield event
