
import httpx
import time
import base64
import sys
import os

# Replace with actual URL after deploy
BASE_URL = "https://akshaymp-1810--indicf5-tts-indicf5service-generate.modal.run"

def test_generate_default():
    print("\n Testing /generate (Default Reference)...")
    payload = {
        "text": "ನಮಸ್ಕಾರ! ಇದು ಇಂಡಿಕ್ ಎಫ್5 ಟಿಟಿಎಸ್ ಪರೀಕ್ಷೆಯಾಗಿದೆ."
    }
    
    try:
        start = time.time()
        # Increased timeout for first generation (cold start + diffusion)
        response = httpx.post(f"{BASE_URL}", json=payload, timeout=120.0)
        duration = time.time() - start
        
        if response.status_code == 200:
            print(f"   SUCCESS! Time: {duration:.2f}s")
            print(f"   Size: {len(response.content)} bytes")
            with open("output_default.wav", "wb") as f:
                f.write(response.content)
            print("   Saved to output_default.wav")
            return True
        else:
            print(f"   FAILED: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

def test_generate_custom(ref_audio_path, ref_text):
    print(f"\n Testing /generate (Custom Reference: {ref_audio_path})...")
    
    if not os.path.exists(ref_audio_path):
        print("   Skipping: Reference audio file not found.")
        return False

    with open(ref_audio_path, "rb") as f:
        audio_bytes = f.read()
        b64_audio = base64.b64encode(audio_bytes).decode('utf-8')
    
    payload = {
        "text": "ಈ ಧ್ವನಿಯನ್ನು ಕಸ್ಟಮ್ ರೆಫರೆನ್ಸ್ ಆಡಿಯೋದಿಂದ ಕ್ಲೋನ್ ಮಾಡಲಾಗಿದೆ.",
        "ref_audio": b64_audio,
        "ref_text": ref_text
    }
    
    try:
        start = time.time()
        response = httpx.post(f"{BASE_URL}", json=payload, timeout=60.0)
        duration = time.time() - start
        
        if response.status_code == 200:
            print(f"   SUCCESS! Time: {duration:.2f}s")
            with open("output_custom.wav", "wb") as f:
                f.write(response.content)
            print("   Saved to output_custom.wav")
            return True
        else:
            print(f"   FAILED: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("IndicF5 TTS Service Test")
    print("="*60)
    
    # Check if URL arg provided
    import sys
    if len(sys.argv) > 1:
        # Update global manually if needed or just print
        print("Note: Update BASE_URL in script if not matching.")

    # 1. Test Default
    test_generate_default()
    
    # 2. Test Custom (Optional - using default output as input if it exists, just for synthesized ref test?)
    # Or just skip.
    # We can try using the 'output_default.wav' as reference for the custom test!
    if os.path.exists("output_default.wav"):
        print("\n Using generated output_default.wav as reference for cloning test...")
        test_generate_custom("output_default.wav", "ನಮಸ್ಕಾರ! ಇದು ಇಂಡಿಕ್ ಎಫ್5 ಟಿಟಿಎಸ್ ಪರೀಕ್ಷೆಯಾಗಿದೆ.")
