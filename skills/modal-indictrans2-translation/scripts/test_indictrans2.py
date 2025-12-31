"""
Test script for IndicTrans2 Modal deployment.

Usage:
    # 1. First deploy or serve the Modal app:
    modal serve src/modal_indictrans2.py
    
    # 2. Run this test script:
    python src/test_indictrans2.py
"""

import httpx
import sys

# Modal deployed URL
BASE_URL = "https://akshaymp-1810--indictrans2-indic-en-indictrans2service-web-app.modal.run"

# Test sentences in different languages
TEST_CASES = [
    {
        "text": "ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಾ?",
        "src_lang": "kan_Knda",
        "expected_contains": "hello",
    },
    {
        "text": "नमस्ते, आप कैसे हैं?",
        "src_lang": "hin_Deva",
        "expected_contains": "hello",
    },
    {
        "text": "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?",
        "src_lang": "tam_Taml",
        "expected_contains": "hello",
    },
]


def test_health():
    """Test health endpoint."""
    print("\n Testing /health endpoint...")
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=30.0)
        response.raise_for_status()
        data = response.json()
        print(f"   Status: {data['status']}")
        print(f"   Model: {data['model']}")
        print(f"   Languages: {len(data['supported_languages'])} supported")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_languages():
    """Test languages endpoint."""
    print("\n Testing /languages endpoint...")
    try:
        response = httpx.get(f"{BASE_URL}/languages", timeout=30.0)
        response.raise_for_status()
        data = response.json()
        print(f"   Target: {data['target']}")
        print(f"   Source languages: {len(data['languages'])}")
        for code, name in list(data['languages'].items())[:5]:
            print(f"      - {code}: {name}")
        print("      ...")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_translate():
    """Test translate endpoint."""
    print("\n Testing /translate endpoint...")
    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n   Test {i}: {test['src_lang']}")
        print(f"   Input: {test['text']}")
        
        try:
            response = httpx.post(
                f"{BASE_URL}/translate",
                json={"text": test["text"], "src_lang": test["src_lang"]},
                timeout=120.0,  # Long timeout for cold start
            )
            response.raise_for_status()
            data = response.json()
            translation = data["translations"][0]
            print(f"   Output: {translation}")
            
            if test["expected_contains"].lower() in translation.lower():
                print(f"    Contains expected: '{test['expected_contains']}'")
            else:
                print(f"    May not contain expected: '{test['expected_contains']}'")
                
        except httpx.HTTPStatusError as e:
            print(f"    Error status: {e.response.status_code}")
            print(f"    Error details: {e.response.text}")
            return False
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    return True


def test_batch_translate():
    """Test batch translation."""
    print("\n Testing batch translation...")
    
    sentences = [
        "ನಮಸ್ಕಾರ",
        "ಧನ್ಯವಾದಗಳು",
        "ನಿಮ್ಮ ಹೆಸರೇನು?",
    ]
    
    try:
        response = httpx.post(
            f"{BASE_URL}/translate",
            json={"text": sentences, "src_lang": "kan_Knda"},
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"   Input ({len(sentences)} sentences):")
        for s in sentences:
            print(f"      - {s}")
        print(f"   Output ({len(data['translations'])} translations):")
        for t in data["translations"]:
            print(f"      - {t}")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("IndicTrans2 Modal Service Test")
    print("=" * 60)
    print(f"Testing: {BASE_URL}")
    
    results = []
    results.append(("Health", test_health()))
    results.append(("Languages", test_languages()))
    results.append(("Translate", test_translate()))
    results.append(("Batch", test_batch_translate()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"   {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
