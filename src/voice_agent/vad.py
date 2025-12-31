"""
Voice Activity Detection using Silero VAD.
Detects speech start/end and buffers complete utterances.
"""
import torch
import io
import wave
from typing import AsyncIterator
from .config import SAMPLE_RATE, VAD_THRESHOLD, MIN_SILENCE_DURATION_MS, MIN_SPEECH_DURATION_MS


class SileroVAD:
    """Silero VAD wrapper for voice activity detection."""
    
    def __init__(
        self,
        threshold: float = VAD_THRESHOLD,
        sample_rate: int = SAMPLE_RATE,
        min_silence_duration_ms: int = MIN_SILENCE_DURATION_MS,
        min_speech_duration_ms: int = MIN_SPEECH_DURATION_MS,
    ):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.min_silence_duration_ms = min_silence_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        
        # Load Silero VAD model
        self.model, self.utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True,
        )
        self.model.eval()
        
        # State
        self.raw_buffer = bytearray()  # Buffer for incoming raw bytes
        self.reset()
    
    def reset(self):
        """Reset VAD state."""
        self.is_speaking = False
        self.speech_buffer = []  # List of 512-sample chunks
        self.silence_frames = 0
        self.speech_frames = 0
        try:
            self.model.reset_states()
        except:
            pass
    
    def clear_buffers(self):
        """Clear audio buffers without resetting model state (for echo suppression)."""
        self.raw_buffer = bytearray()
        self.speech_buffer = []
        self.is_speaking = False
        self.silence_frames = 0
        self.speech_frames = 0
    
    def process_chunk(self, audio_chunk: bytes) -> bytes | None:
        """
        Process an audio chunk and return complete utterance when speech ends.
        Accumlates audio to ensure correct window size for VAD.
        
        Args:
            audio_chunk: Raw PCM audio bytes (16-bit, mono, 16kHz)
        
        Returns:
            WAV bytes of complete utterance if speech ended, None otherwise
        """
        self.raw_buffer.extend(audio_chunk)
        
        window_size_samples = 512 if self.sample_rate == 16000 else 256
        window_size_bytes = window_size_samples * 2  # 16-bit = 2 bytes per sample
        
        utterance = None
        
        while len(self.raw_buffer) >= window_size_bytes:
            # Extract window
            window_bytes = self.raw_buffer[:window_size_bytes]
            self.raw_buffer = self.raw_buffer[window_size_bytes:]
            
            # Process window
            result = self._process_window(bytes(window_bytes), window_size_samples)
            if result:
                utterance = result
                
        return utterance

    def _process_window(self, audio_bytes: bytes, window_size_samples: int) -> bytes | None:
        """Process a single fixed-size window."""
        # Convert bytes to tensor (copy to avoid warning/error)
        # Note: input must be exactly window_size_samples
        audio_int16 = torch.frombuffer(audio_bytes, dtype=torch.int16).clone()
        audio_float = audio_int16.float() / 32768.0  # Normalize to [-1, 1]
        
        # Run VAD
        # Silero expects (batch, samples) or (samples,)
        # It's stateful, so we feed chunks sequentially
        speech_prob = self.model(audio_float, self.sample_rate).item()
        
        # Calculate frame duration in ms
        frame_duration_ms = (window_size_samples / self.sample_rate) * 1000
        
        if speech_prob >= self.threshold:
            # Speech detected
            self.speech_buffer.append(audio_bytes)
            self.speech_frames += 1
            self.silence_frames = 0
            
            if not self.is_speaking:
                # Check minimum speech duration before considering it "speaking"
                total_speech_ms = self.speech_frames * frame_duration_ms
                if total_speech_ms >= self.min_speech_duration_ms:
                    self.is_speaking = True
                    print("🎤 Speech started")
        else:
            # Silence detected
            if self.is_speaking:
                self.speech_buffer.append(audio_bytes)  # Keep some silence padding
                self.silence_frames += 1
                
                # Check if silence duration exceeds threshold
                silence_ms = self.silence_frames * frame_duration_ms
                if silence_ms >= self.min_silence_duration_ms:
                    # Speech ended - return complete utterance
                    print("🔇 Speech ended")
                    utterance = self._create_wav(self.speech_buffer)
                    self.reset()
                    # If we had leftover raw bytes, we should preserve them? 
                    # reset() clears raw_buffer. We should NOT clear raw_buffer in reset if called here.
                    # But reset() is designed to look like fresh state.
                    # Actually, raw_buffer contains *future* audio not yet processed. we shouldn't clear it.
                    # So reset() should be modified or we handle raw_buffer separately.
                    return utterance
            else:
                # Not speaking, keep a small circular buffer? 
                # For simplicity, we discard silence *before* speech starts, 
                # but maybe keep a few frames for context? Silero example uses a trigger.
                # Here we just start buffer when speech detected + maybe some lookback if we implemented ring buffer.
                # Current logic discards silence until threshold triggered.
                self.speech_frames = 0
                # Clear speech buffer if getting too big while not speaking (e.g. spurious spikes didn't trigger min duration)
                if not self.is_speaking and self.speech_buffer:
                     # Check if we should flush buffer if not confirmed speaking
                     # Ideally we keep last N frames.
                     pass
                if not self.is_speaking:
                    self.speech_buffer = [] # Reset buffer if we fell back to silence without confirming speech
        
        return None
        return None

    def _create_wav(self, audio_chunks: list[bytes]) -> bytes:
        """Create WAV file from audio chunks."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(b"".join(audio_chunks))
        return buffer.getvalue()

    def get_remaining(self) -> bytes | None:
        """Get any remaining speech in buffer."""
        if self.speech_buffer and self.is_speaking:
            utterance = self._create_wav(self.speech_buffer)
            # soft reset
            self.is_speaking = False
            self.speech_buffer = []
            self.silence_frames = 0
            self.speech_frames = 0
            try:
                self.model.reset_states()
            except:
                pass
            return utterance
        return None



async def vad_stream(
    audio_stream: AsyncIterator[bytes],
    vad: SileroVAD = None,
) -> AsyncIterator[bytes]:
    """
    VAD stream: Filter audio and yield complete utterances.
    
    Args:
        audio_stream: Async iterator of raw PCM audio chunks
        vad: Optional SileroVAD instance
    
    Yields:
        WAV bytes of complete utterances
    """
    if vad is None:
        vad = SileroVAD()
    
    async for audio_chunk in audio_stream:
        utterance = vad.process_chunk(audio_chunk)
        if utterance:
            yield utterance
    
    # Handle any remaining audio
    remaining = vad.get_remaining()
    if remaining:
        yield remaining
