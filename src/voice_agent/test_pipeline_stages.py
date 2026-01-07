"""
Test script to verify the unified voice agent pipeline.
Tests the consolidated Modal endpoint: unified-voice-agent
"""
import asyncio
import base64
import os
import time

import httpx

# Unified endpoint
UNIFIED_ENDPOINT = "https://akshaymp-1810--unified-voice-agent-unifiedvoiceagent-process.modal.run"
HEALTH_ENDPOINT = "https://akshaymp-1810--unified-voice-agent-unifiedvoiceagent-health.modal.run"


async def test_health():
    """Test health endpoint."""
    print("\n💚 Testing Health Endpoint...")
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.get(HEALTH_ENDPOINT)
            resp.raise_for_status()
            print(f"✅ Health: {resp.json()}")
        except Exception as e:
            print(f"❌ Health Failed: {e}")


async def test_unified_pipeline():
    """Test the full unified pipeline: Audio -> STT -> Trans -> Agent -> Trans -> TTS -> Audio"""
    print("\n🔗 Testing Full Unified Pipeline...")
    
    audio_path = "sample_audio.wav"
    if not os.path.exists(audio_path):
        print(f"❌ {audio_path} not found!")
        return
    
    # Load and encode audio
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    print(f"📂 Loaded audio: {len(audio_bytes)} bytes")
    
    payload = {
        "audio_b64": audio_b64,
        "language": "kn",
        "src_lang": "kan_Knda",
        "tgt_lang": "kan_Knda",
    }
    
    async with httpx.AsyncClient(timeout=180) as client:
        try:
            print("⏳ Sending to unified endpoint (may take ~90s on cold start)...")
            t0 = time.perf_counter()
            resp = await client.post(UNIFIED_ENDPOINT, json=payload)
            total_time = time.perf_counter() - t0
            resp.raise_for_status()
            result = resp.json()
            
            print(f"\n✅ Pipeline Success! (Total: {total_time:.1f}s)")
            print(f"   📝 Transcription: {result.get('transcription', 'N/A')}")
            print(f"   🔄 Translated (En): {result.get('translated_en', 'N/A')}")
            print(f"   🤖 Agent Response: {result.get('agent_response_en', 'N/A')[:50]}...")
            print(f"   🔄 Response (Indic): {result.get('response_indic', 'N/A')[:50]}...")
            print(f"   ⏱️ Timings: {result.get('timings', {})}")
            
            # Save output audio
            audio_out_b64 = result.get("audio_b64")
            if audio_out_b64:
                audio_out = base64.b64decode(audio_out_b64)
                with open("unified_output.wav", "wb") as f:
                    f.write(audio_out)
                print(f"   🔊 Saved output audio: unified_output.wav ({len(audio_out)} bytes)")
                
        except httpx.TimeoutException:
            print("❌ Request timed out (>180s). Service may be cold starting.")
        except Exception as e:
            print(f"❌ Pipeline Failed: {e}")


async def benchmark_unified(iterations: int = 3):
    """Benchmark the unified pipeline."""
    print(f"\n� Benchmarking ({iterations} iterations)...")
    
    audio_path = "sample_audio.wav"
    if not os.path.exists(audio_path):
        print(f"❌ {audio_path} not found!")
        return
    
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    payload = {
        "audio_b64": audio_b64,
        "language": "kn",
        "src_lang": "kan_Knda",
        "tgt_lang": "kan_Knda",
    }
    
    timings_list = []
    
    async with httpx.AsyncClient(timeout=180) as client:
        for i in range(iterations):
            try:
                t0 = time.perf_counter()
                resp = await client.post(UNIFIED_ENDPOINT, json=payload)
                client_time = (time.perf_counter() - t0) * 1000
                resp.raise_for_status()
                result = resp.json()
                
                server_timings = result.get("timings", {})
                timings_list.append({
                    "client_total_ms": client_time,
                    **server_timings,
                })
                print(f"   Iteration {i+1}: {server_timings}")
            except Exception as e:
                print(f"   ❌ Iteration {i+1} failed: {e}")
    
    if timings_list:
        print("\n📈 Summary:")
        for key in timings_list[0].keys():
            values = [t[key] for t in timings_list if key in t]
            if values:
                avg = sum(values) / len(values)
                print(f"   {key}: avg={avg:.0f}ms, min={min(values):.0f}ms, max={max(values):.0f}ms")


async def main():
    print("🚀 Unified Voice Agent Pipeline Tests")
    print("=" * 50)
    
    await test_health()
    await test_unified_pipeline()
    await benchmark_unified(iterations=3)
    
    print("\n✨ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
