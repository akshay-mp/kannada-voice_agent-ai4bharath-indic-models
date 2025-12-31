"""
Event types for Voice Agent Pipeline.
Based on LangChain voice sandwich architecture.
"""
from dataclasses import dataclass, field
from typing import Any, Literal
import time


@dataclass
class VoiceAgentEvent:
    """Base class for all voice agent events."""
    type: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class UserInputEvent(VoiceAgentEvent):
    """Event emitted when raw audio data is received/start of processing."""
    type: Literal["user_input"] = "user_input"
    audio: bytes = b"" # Not sent to client

    @classmethod
    def create(cls, audio: bytes = b"") -> "UserInputEvent":
        return cls(audio=audio)


@dataclass
class STTChunkEvent(VoiceAgentEvent):
    """Partial STT transcription (streaming)."""
    type: Literal["stt_chunk"] = "stt_chunk"
    text: str = ""

    @classmethod
    def create(cls, text: str) -> "STTChunkEvent":
        return cls(text=text)


@dataclass
class STTOutputEvent(VoiceAgentEvent):
    """Final STT transcription (Kannada text)."""
    type: Literal["stt_output"] = "stt_output"
    transcript: str = ""
    language: str = "kn"

    @classmethod
    def create(cls, transcript: str, language: str = "kn") -> "STTOutputEvent":
        return cls(transcript=transcript, language=language)


@dataclass
class TranslationEvent(VoiceAgentEvent):
    """Translation result."""
    type: Literal["translation"] = "translation"
    text: str = ""
    src_lang: str = ""
    tgt_lang: str = ""
    direction: Literal["indic_to_en", "en_to_indic"] = "indic_to_en"

    @classmethod
    def create(cls, text: str, src_lang: str, tgt_lang: str, direction: str) -> "TranslationEvent":
        return cls(text=text, src_lang=src_lang, tgt_lang=tgt_lang, direction=direction)


@dataclass
class AgentChunkEvent(VoiceAgentEvent):
    """Streaming agent response token."""
    type: Literal["agent_chunk"] = "agent_chunk"
    text: str = ""

    @classmethod
    def create(cls, text: str) -> "AgentChunkEvent":
        return cls(text=text)


@dataclass
class ToolCallEvent(VoiceAgentEvent):
    """Agent tool invocation (e.g., Google Search)."""
    type: Literal["tool_call"] = "tool_call"
    id: str = ""
    name: str = ""
    args: dict = field(default_factory=dict)

    @classmethod
    def create(cls, id: str, name: str, args: dict) -> "ToolCallEvent":
        return cls(id=id, name=name, args=args)


@dataclass
class ToolResultEvent(VoiceAgentEvent):
    """Tool execution result."""
    type: Literal["tool_result"] = "tool_result"
    tool_call_id: str = ""
    name: str = ""
    result: str = ""

    @classmethod
    def create(cls, tool_call_id: str, name: str, result: str) -> "ToolResultEvent":
        return cls(tool_call_id=tool_call_id, name=name, result=result)


@dataclass
class AgentEndEvent(VoiceAgentEvent):
    """Agent finished responding."""
    type: Literal["agent_end"] = "agent_end"
    full_response: str = ""

    @classmethod
    def create(cls, full_response: str = "") -> "AgentEndEvent":
        return cls(full_response=full_response)


@dataclass
class TTSChunkEvent(VoiceAgentEvent):
    """Audio chunk from TTS."""
    type: Literal["tts_chunk"] = "tts_chunk"
    audio: bytes = b""

    @classmethod
    def create(cls, audio: bytes) -> "TTSChunkEvent":
        return cls(audio=audio)


@dataclass
class TTSCompleteEvent(VoiceAgentEvent):
    """Signal that TTS generation is complete for this turn."""
    type: Literal["tts_complete"] = "tts_complete"

    @classmethod
    def create(cls) -> "TTSCompleteEvent":
        return cls()


def event_to_dict(event: VoiceAgentEvent) -> dict:
    """Convert event to dictionary for JSON serialization."""
    data = {
        "type": event.type,
        "ts": int(event.timestamp * 1000),  # Convert to milliseconds for frontend
    }
    
    if isinstance(event, UserInputEvent):
        pass # Audio not sent back
    elif isinstance(event, STTChunkEvent):
        data["transcript"] = event.text  # Frontend expects 'transcript' not 'text'
    elif isinstance(event, STTOutputEvent):
        data["transcript"] = event.transcript
        data["language"] = event.language
    elif isinstance(event, TranslationEvent):
        data["text"] = event.text
        data["src_lang"] = event.src_lang
        data["tgt_lang"] = event.tgt_lang
        data["direction"] = event.direction
    elif isinstance(event, AgentChunkEvent):
        data["text"] = event.text
    elif isinstance(event, ToolCallEvent):
        data["id"] = event.id
        data["name"] = event.name
        data["args"] = event.args
    elif isinstance(event, ToolResultEvent):
        data["tool_call_id"] = event.tool_call_id
        data["name"] = event.name
        data["result"] = event.result
    elif isinstance(event, AgentEndEvent):
        data["full_response"] = event.full_response
    elif isinstance(event, TTSChunkEvent):
        # Audio bytes are sent separately, not in JSON
        data["audio_length"] = len(event.audio)
    elif isinstance(event, TTSCompleteEvent):
        pass
    
    return data
