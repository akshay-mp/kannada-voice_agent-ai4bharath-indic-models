
import httpx
import time
import sys

# Replace with the actual deployed URL after running modal deploy
# Typically: https://your-username--indictrans2-en-indic-indictrans2enindicservice-web-app.modal.run
BASE_URL = "https://akshaymp-1810--indictrans2-en-indic-indictrans2enindicse-9e3146.modal.run"

def test_health():
    print("\n Testing /health endpoint...")
    try:
        # Increased timeout to handle cold start
        response = httpx.get(f"{BASE_URL}/health", timeout=120.0)
        response.raise_for_status()
        data = response.json()
        print(f"   Status: {data['status']}")
        print(f"   Model: {data['model']}")
        print(f"   Languages: {len(data['supported_languages'])} supported")
        return True
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

def test_languages():
    print("\n Testing /languages endpoint...")
    try:
        response = httpx.get(f"{BASE_URL}/languages", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        print(f"   Source: {data['source']}")
        print(f"   Target languages: {len(data['languages'])}")
        # Print first 5
        for code, name in list(data['languages'].items())[:5]:
            print(f"      - {code}: {name}")
        return True
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

def test_translate_single():
    print("\n Testing /translate endpoint (Single)...")
    
    # Test cases: English -> Indic
    test_cases = [
        ("Hello, how are you?", "kan_Knda", ["ಹಲೋ", "ನಮಸ್ಕಾರ", "ಹೇಗಿದ್ದೀರಾ"]), # Kannada
        ("Hello, how are you?", "hin_Deva", ["नमस्ते", "कैसे"]),             # Hindi
        ("Hello, how are you?", "tam_Taml", ["வணக்கம்", "எப்படி"]),           # Tamil
    ]

    all_passed = True
    for idx, (text, tgt, expected_keywords) in enumerate(test_cases, 1):
        print(f"\n   Test {idx}: {tgt} (English -> {tgt})")
        payload = {
            "text": text,
            "tgt_lang": tgt
        }
        try:
            # First request might be slow (cold start)
            timeout = 180.0 if idx == 1 else 30.0
            start = time.time()
            response = httpx.post(f"{BASE_URL}/translate", json=payload, timeout=timeout)
            duration = time.time() - start
            
            if response.status_code != 200:
                print(f"   Status: {response.status_code}")
                print(f"   Error: {response.text}")
                all_passed = False
                continue

            data = response.json()
            translation = data["translations"][0]
            print(f"   Input: {text}")
            print(f"   Output: {translation}")
            print(f"   Time: {duration:.2f}s")

            # Simple verification
            found = False
            for k in expected_keywords:
                if k in translation:
                    found = True
                    break
            
            if found:
                print(f"    Contains expected keyword")
            else:
                print(f"    WARNING: May not contain expected keywords: {expected_keywords}")

        except Exception as e:
            print(f"   FAILED: {e}")
            all_passed = False

    return all_passed

def test_translate_batch():
    print("\n Testing batch translation...")
    payload = {
        "text": [
            "Hello",
            "Thank you",
            "What is your name?"
        ],
        "tgt_lang": "kan_Knda"
    }
    
    try:
        response = httpx.post(f"{BASE_URL}/translate", json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        translations = data["translations"]
        
        print("   Input (3 sentences):")
        for t in payload["text"]:
            print(f"      - {t}")
            
        print("   Output (3 translations):")
        for t in translations:
            print(f"      - {t}")
            
        if len(translations) == 3:
            return True
        else:
            print("   FAILED: Incorrect number of translations")
            return False
            
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("IndicTrans2 En-Indic Modal Service Test")
    print("="*60)
    print(f"Testing: {BASE_URL}")
    
    h_ok = test_health()
    l_ok = test_languages()
    t_ok = test_translate_single()
    b_ok = test_translate_batch()
    
    print("\n" + "="*60)
    print("Summary:")
    print(f"   Health: {'PASS' if h_ok else 'FAIL'}")
    print(f"   Languages: {'PASS' if l_ok else 'FAIL'}")
    print(f"   Translate: {'PASS' if t_ok else 'FAIL'}")
    print(f"   Batch: {'PASS' if b_ok else 'FAIL'}")
    print("="*60)
