"""
Test script for IndicConformer STT API on Modal.

Usage:
    # Test with a WAV file
    python src/test_indicconformer.py --file audio.wav --language kn

    # Record and test (5 seconds)
    python src/test_indicconformer.py --record --language kn

    # Health check only
    python src/test_indicconformer.py --health
"""

import argparse
import base64
import json
import requests
import wave
import io

# Your deployed Modal endpoint
API_BASE_URL = "https://akshaymp-1810--indicconformer-stt-indicconformerstt-web-app.modal.run"


def health_check():
    """Check if the API is healthy."""
    print("🔍 Checking API health...")
    print("   (First request may take 1-2 minutes for cold start...)")
    response = requests.get(f"{API_BASE_URL}/health", timeout=180)  # 3 min for cold start
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {data['status']}")
        print(f"📦 Model: {data['model']}")
        print(f"🌍 Languages: {len(data['supported_languages'])} supported")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        print(response.text)
        return False


def list_languages():
    """Get supported languages."""
    response = requests.get(f"{API_BASE_URL}/languages", timeout=30)
    if response.status_code == 200:
        data = response.json()
        print("\n📋 Supported Languages:")
        for code, name in data["languages"].items():
            print(f"   {code}: {name}")
    return response.json()


def transcribe_audio(audio_bytes: bytes, language: str = "kn", decoding: str = "ctc", output_file: str = None):
    """Send audio to the API for transcription."""
    print(f"\n🎯 Transcribing audio (language={language}, decoding={decoding})...")
    
    # Encode to base64
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    # Send request
    response = requests.post(
        f"{API_BASE_URL}/transcribe",
        json={
            "audio_b64": audio_b64,
            "language": language,
            "decoding": decoding,
        },
        timeout=120,  # Allow time for cold start
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Transcription: {data['transcription']}")
        print(f"   Language: {data['language']}")
        print(f"   Decoding: {data['decoding']}")
        
        # Save to file if output_file specified
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(data['transcription'])
            print(f"📄 Saved to: {output_file}")
        
        return data
    else:
        print(f"❌ Transcription failed: {response.status_code}")
        print(response.text)
        return None


def record_audio(duration: int = 5, sample_rate: int = 16000):
    """Record audio from microphone."""
    try:
        import pyaudio
    except ImportError:
        print("❌ pyaudio not installed. Install with: pip install pyaudio")
        return None
    
    print(f"🎤 Recording for {duration} seconds... Speak now!")
    
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        frames_per_buffer=1024,
    )
    
    frames = []
    for _ in range(0, int(sample_rate / 1024 * duration)):
        data = stream.read(1024)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    print("✅ Recording complete!")
    
    # Convert to WAV bytes
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
    
    return buffer.getvalue()


def load_audio_file(filepath: str) -> bytes:
    """Load audio file as bytes."""
    print(f"📂 Loading audio file: {filepath}")
    with open(filepath, "rb") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(description="Test IndicConformer STT API")
    parser.add_argument("--file", "-f", help="Path to audio file (WAV, FLAC, MP3)")
    parser.add_argument("--record", "-r", action="store_true", help="Record from microphone")
    parser.add_argument("--duration", "-d", type=int, default=5, help="Recording duration (seconds)")
    parser.add_argument("--language", "-l", default="kn", help="Language code (default: kn)")
    parser.add_argument("--decoding", choices=["ctc", "rnnt"], default="ctc", help="Decoding method")
    parser.add_argument("--output", "-o", help="Output file path for transcription (.txt)")
    parser.add_argument("--health", action="store_true", help="Health check only")
    parser.add_argument("--languages", action="store_true", help="List supported languages")
    
    args = parser.parse_args()
    
    # Health check
    if args.health:
        health_check()
        return
    
    # List languages
    if args.languages:
        list_languages()
        return
    
    # Always check health first
    if not health_check():
        print("\n⚠️  API might be starting up (cold start). Try again in 30-60 seconds.")
        return
    
    # Get audio
    audio_bytes = None
    
    if args.file:
        audio_bytes = load_audio_file(args.file)
    elif args.record:
        audio_bytes = record_audio(duration=args.duration)
    else:
        print("\n⚠️  No audio source specified. Use --file or --record")
        print("   Example: python test_indicconformer.py --record --language kn")
        return
    
    if audio_bytes:
        transcribe_audio(audio_bytes, language=args.language, decoding=args.decoding, output_file=args.output)


if __name__ == "__main__":
    main()
