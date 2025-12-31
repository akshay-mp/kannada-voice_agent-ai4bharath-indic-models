"""
Test script to verify individual voice agent pipeline stages.
"""
import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.voice_agent import stt_client, translation_client, tts_client, agent

async def test_stt():
    print("\n🎤 Testing STT Client...")
    try:
        # Use sample audio if available, otherwise skip
        audio_path = "sample_audio.wav"
        if os.path.exists(audio_path):
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            text = await stt_client.transcribe(audio_bytes)
            print(f"✅ STT Result: {text}")
        else:
            print(f"⚠️ {audio_path} not found, skipping STT test")
    except Exception as e:
        print(f"❌ STT Failed: {e}")

async def test_translation():
    print("\n🔄 Testing Translation Client...")
    try:
        # Indic to English
        kannada_text = "ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ?"  # Hello, how are you?
        en_text = await translation_client.translate_indic_to_english(kannada_text)
        print(f"✅ Indic->En: '{kannada_text}' -> '{en_text}'")
        
        # English to Indic
        english_text = "I am fine, thank you."
        kn_text = await translation_client.translate_english_to_indic(english_text)
        print(f"✅ En->Indic: '{english_text}' -> '{kn_text}'")
    except Exception as e:
        print(f"❌ Translation Failed: {e}")

async def test_agent():
    print("\n🤖 Testing Gemini Agent...")
    try:
        query = "What is the capital of Karnataka?"
        response = await agent.run_agent(query)
        print(f"✅ Agent Response: {response[:100]}...")
    except Exception as e:
        print(f"❌ Agent Failed: {e}")

async def test_tts():
    print("\n🔊 Testing TTS Client...")
    try:
        text = "ನಮಸ್ಕಾರ, ಇದು ಧ್ವನಿ ಪರೀಕ್ಷೆ." # Hello, this is a voice test.
        audio_bytes = await tts_client.synthesize(text)
        print(f"✅ TTS Generated {len(audio_bytes)} bytes")
        # Save to file
        with open("test_output.wav", "wb") as f:
            f.write(audio_bytes)
        print("✅ Saved to test_output.wav")
    except Exception as e:
        print(f"❌ TTS Failed: {e}")

async def test_full_pipeline():
    print("\n🔗 Testing Full End-to-End Pipeline (STT -> Trans -> Agent -> Trans -> TTS)...")
    try:
        # 1. STT
        audio_path = "sample_audio.wav"
        if not os.path.exists(audio_path):
            print(f"⚠️ {audio_path} not found, using fallback text for pipeline test")
            stt_text = "ಬೆಂಗಳೂರಿನ ಹವಾಮಾನ ಹೇಗಿದೆ?" # How is weather in Bangalore?
        else:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            print("1️⃣ Transcribing audio...")
            stt_text = await stt_client.transcribe(audio_bytes)
        
        print(f"   STT Output: {stt_text}")

        # 2. Indic -> En
        print("2️⃣ Translating to English...")
        en_text = await translation_client.translate_indic_to_english(stt_text)
        print(f"   English Query: {en_text}")

        # 3. Agent
        print("3️⃣ Querying Agent...")
        agent_resp = await agent.run_agent(en_text)
        print(f"   Agent Response: {agent_resp[:100]}...")

        # 4. En -> Indic
        print("4️⃣ Translating to Kannada...")
        kn_resp = await translation_client.translate_english_to_indic(agent_resp)
        print(f"   Kannada Response: {kn_resp[:100]}...")

        # 5. TTS
        print("5️⃣ Synthesizing Speech...")
        audio = await tts_client.synthesize(kn_resp)
        print(f"✅ Full Pipeline Success! Output audio: {len(audio)} bytes")
        
        with open("full_pipeline_output.wav", "wb") as f:
            f.write(audio)
            
    except Exception as e:
        print(f"❌ Full Pipeline Failed: {e}")
        raise e

async def main():
    print("🚀 Starting Pipeline Tests...")
    # Individual integrity checks
    await test_stt()
    await test_translation()
    await test_agent()
    await test_tts()
    
    # Full integration check
    await test_full_pipeline()
    
    print("\n✨ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
