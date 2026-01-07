"""
Benchmark script for the Unified Voice Agent pipeline.
Measures latency per component and total round-trip time.

Usage:
    python src/modal/test_unified.py
"""

import base64
import time
import requests
import sys
from pathlib import Path

# Default endpoint - deployed on Modal
UNIFIED_ENDPOINT = (
    "https://akshaymp-1810--unified-voice-agent-unifiedvoiceagent-process.modal.run"
)


def load_test_audio(path: str = None) -> str:
    """Load audio file and encode as base64."""
    if path is None:
        # Try to find a test audio file
        candidates = [
            "test_audio.wav",
            "src/modal/test_audio.wav",
            "tests/test_audio.wav",
        ]
        for c in candidates:
            if Path(c).exists():
                path = c
                break

    if path is None or not Path(path).exists():
        print("⚠️ No test audio file found. Please provide one.")
        print("Usage: python test_unified.py <path_to_audio.wav>")
        sys.exit(1)

    with open(path, "rb") as f:
        audio_bytes = f.read()

    return base64.b64encode(audio_bytes).decode("utf-8")


def benchmark_unified(endpoint: str, audio_b64: str, iterations: int = 5):
    """Run benchmark against the unified endpoint."""
    print(f"\n🚀 Running {iterations} iterations against {endpoint}\n")

    timings = []

    for i in range(iterations):
        payload = {
            "audio_b64": audio_b64,
            "language": "kn",
            "src_lang": "kan_Knda",
            "tgt_lang": "kan_Knda",
        }

        t0 = time.perf_counter()
        try:
            response = requests.post(endpoint, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            print(f"❌ Iteration {i + 1} failed: {e}")
            continue

        total_time = (time.perf_counter() - t0) * 1000  # ms

        print(f"--- Iteration {i + 1} ---")
        print(f"  Transcription: {result.get('transcription', 'N/A')[:50]}...")
        print(f"  Server Timings: {result.get('timings', {})}")
        print(f"  Client Total (incl. network): {total_time:.0f}ms")

        timings.append(
            {
                "client_total_ms": total_time,
                **result.get("timings", {}),
            }
        )

    if timings:
        print("\n📊 Benchmark Summary:")
        print(f"  Iterations: {len(timings)}")

        for key in timings[0].keys():
            values = [t[key] for t in timings if key in t]
            if values:
                avg = sum(values) / len(values)
                print(
                    f"  {key}: avg={avg:.0f}ms, min={min(values):.0f}ms, max={max(values):.0f}ms"
                )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark Unified Voice Agent")
    parser.add_argument(
        "--endpoint", "-e", default=UNIFIED_ENDPOINT, help="Endpoint URL"
    )
    parser.add_argument("--audio", "-a", default=None, help="Path to test audio file")
    parser.add_argument(
        "--iterations", "-n", type=int, default=5, help="Number of iterations"
    )

    args = parser.parse_args()

    audio_b64 = load_test_audio(args.audio)
    print(f"✅ Loaded audio ({len(audio_b64)} base64 chars)")

    benchmark_unified(args.endpoint, audio_b64, args.iterations)


if __name__ == "__main__":
    main()
