"""
Test client for IndicConformer STT API on Modal.

Usage:
    # Test with a WAV file
    python test_indicconformer.py --file audio.wav --language kn

    # Health check only
    python test_indicconformer.py --health

    # List supported languages
    python test_indicconformer.py --languages
"""

import argparse
import base64
import requests

# Update this with your deployed Modal endpoint
API_BASE_URL = "https://YOUR-WORKSPACE--indicconformer-stt-indicconformerstt-web-app.modal.run"


def health_check():
    """Check if the API is healthy."""
    print("🔍 Checking API health...")
    print("   (First request may take 1-2 minutes for cold start...)")
    response = requests.get(f"{API_BASE_URL}/health", timeout=180)
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


def transcribe_audio(audio_bytes: bytes, language: str = "kn", decoding: str = "ctc"):
    """Send audio to the API for transcription."""
    print(f"\n🎯 Transcribing audio (language={language}, decoding={decoding})...")
    
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    response = requests.post(
        f"{API_BASE_URL}/transcribe",
        json={
            "audio_b64": audio_b64,
            "language": language,
            "decoding": decoding,
        },
        timeout=120,
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Transcription: {data['transcription']}")
        print(f"   Language: {data['language']}")
        print(f"   Decoding: {data['decoding']}")
        return data
    else:
        print(f"❌ Transcription failed: {response.status_code}")
        print(response.text)
        return None


def load_audio_file(filepath: str) -> bytes:
    """Load audio file as bytes."""
    print(f"📂 Loading audio file: {filepath}")
    with open(filepath, "rb") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(description="Test IndicConformer STT API")
    parser.add_argument("--file", "-f", help="Path to audio file (WAV, FLAC, MP3)")
    parser.add_argument("--language", "-l", default="kn", help="Language code (default: kn)")
    parser.add_argument("--decoding", choices=["ctc", "rnnt"], default="ctc")
    parser.add_argument("--health", action="store_true", help="Health check only")
    parser.add_argument("--languages", action="store_true", help="List supported languages")
    
    args = parser.parse_args()
    
    if args.health:
        health_check()
        return
    
    if args.languages:
        list_languages()
        return
    
    if not health_check():
        print("\n⚠️  API might be starting up. Try again in 30-60 seconds.")
        return
    
    if args.file:
        audio_bytes = load_audio_file(args.file)
        transcribe_audio(audio_bytes, language=args.language, decoding=args.decoding)
    else:
        print("\n⚠️  No audio file specified. Use --file <path>")


if __name__ == "__main__":
    main()
