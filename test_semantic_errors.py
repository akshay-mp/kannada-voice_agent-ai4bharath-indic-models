import time
import requests
import json
import statistics

API_URL = "https://akshaymp-1810--ambari-translator-vllm-serve.modal.run/v1/completions"

PROMPT_TEMPLATE = """Instruction: translate user query to english
Input: ನನಗೆ ಅಕ್ಕಿ ಬೇಕು.
Output: I want rice.

Instruction: translate user query to english
Input: ನನಗೆ Apple ಫೋನ್ ಬೇಕು.
Output: I want an Apple phone.

Instruction: translate user query to english
Input: ನನಗೆ ಕ್ಯಾಶ್ಯೂ ನಟ್ಸ್ ಬೇಕು.
Output: I want cashew nuts.

Instruction: translate user query to english
Input: ನನಗೆ ಒಂದು ಕ್ಯಾಶ್ಯೂ ಪ್ಯಾಕೆಟ್ ಬೇಕು.
Output: I want a cashew packet.

Instruction: translate user query to english
Input: ಜಾಗ್ವಾರ್ ಕಾರು ಸೂಪರ್ ಆಗಿದೆ.
Output: The Jaguar car is super.

Instruction: translate user query to english
Input: ಆಫೀಸ್ ಗೆ ಲೇಟ್ ಆಯ್ತು.
Output: I am late for the office.

Instruction: translate LLM response to kanglish
Input: Here is your order.
Output: ಇಲ್ಲಿ ನಿಮ್ಮ ಆರ್ಡರ್ ಇದೆ.

Instruction: translate LLM response to kanglish
Input: Payment is successful.
Output: Payment ಯಶಸ್ವಿಯಾಗಿದೆ.

Instruction: {}
Input: {}
Output:"""

SEMANTIC_TEST_CASES = [
    # 1. Phonetic Ambiguity
    {
        "category": "Phonetic Ambiguity",
        "instruction": "translate user query to english",
        "input": "ನನಗೆ ಒಂದು ಕ್ಯಾಶ್ಯೂ ಪ್ಯಾಕೆಟ್ ಬೇಕು.",
        "expected_keywords": ["cashew", "packet"],
        "unexpected_keywords": ["cash", "back", "cashback"]
    },
    {
        "category": "Phonetic Ambiguity",
        "instruction": "translate user query to english",
        "input": "ಕರೆಂಟ್ ಬಿಲ್ ಪೇ ಮಾಡಬೇಕು.",
        "expected_keywords": ["bill", "pay"],
        "unexpected_keywords": ["bell", "beel"]
    },

    # 2. Brand vs Object
    {
        "category": "Brand vs Object",
        "instruction": "translate user query to english",
        "input": "ನಾನು ಹೊಸ ಆಪಲ್ ವಾಚ್ ತಗೊಂಡೆ.",
        "expected_keywords": ["apple", "watch"],
        "unexpected_keywords": ["fruit", "eat"]
    },
    {
        "category": "Brand vs Object",
        "instruction": "translate user query to english",
        "input": "ಊಟಕ್ಕೆ ಆಪಲ್ ಕಟ್ ಮಾಡು.",
        "expected_keywords": ["apple", "cut"],
        "unexpected_keywords": ["phone", "watch", "mac"]
    },
    {
        "category": "Brand vs Object",
        "instruction": "translate user query to english",
        "input": "ಜಾಗ್ವಾರ್ ಕಾರು ತುಂಬಾ ವೇಗವಾಗಿ ಹೋಗುತ್ತೆ.",
        "expected_keywords": ["jaguar", "car"],
        "unexpected_keywords": ["animal", "tiger"]
    },

     # 3. Contextual Ambiguity
    {
        "category": "Contextual Ambiguity",
        "instruction": "translate user query to english",
        "input": "ಸೀಲಿಂಗ್ ಫ್ಯಾನ್ ಆನ್ ಮಾಡು.",
        "expected_keywords": ["fan", "on"],
        "unexpected_keywords": ["follower", "movie"]
    },
    {
        "category": "Contextual Ambiguity",
        "instruction": "translate user query to english",
        "input": "ನಾನು ದರ್ಶನ್ ಅವರ ದೊಡ್ಡ ಫ್ಯಾನ್.",
        "expected_keywords": ["fan", "big", "darshan"],
        "unexpected_keywords": ["air", "wind", "ceiling"]
    },
    {
        "category": "Contextual Ambiguity",
        "instruction": "translate user query to english",
        "input": "ಟೇಬಲ್ ಮೇಲೆ ಮೌಸ್ ಇದೆ.",
        "expected_keywords": ["mouse", "table"], 
        "unexpected_keywords": []
    },

    # 4. Loan Words & Code Switching
    {
        "category": "Code Switching",
        "instruction": "translate user query to english",
        "input": "ಆಫೀಸ್ ಗೆ ಲೇಟ್ ಆಯ್ತು.",
        "expected_keywords": ["office", "late"],
        "unexpected_keywords": ["light"] # Removed 'off'
    },
     {
        "category": "Code Switching",
        "instruction": "translate user query to english",
        "input": "ಬಸ್ ಸ್ಟಾಪ್ ಎಲ್ಲಿದೆ?",
        "expected_keywords": ["bus", "stop"],
        "unexpected_keywords": ["boss", "step"]
    }
]

import re

def test_semantic_errors():
    output_file = "semantic_evaluation_results.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")
            
        log(f"Testing Semantic Errors on: {API_URL}")
        log("-" * 60)
        
        passed_count = 0
        
        for i, item in enumerate(SEMANTIC_TEST_CASES):
            category = item["category"]
            instruction = item["instruction"]
            text = item["input"]
            expected = item["expected_keywords"]
            unexpected = item["unexpected_keywords"]
            
            prompt = PROMPT_TEMPLATE.format(instruction, text)
            payload = {
                "model": "ambari-merged",
                "prompt": prompt,
                "max_tokens": 128,
                "temperature": 0.1,  # Strict
                "repetition_penalty": 1.1,
                "stop": ["<|endoftext|>"]
            }

            try:
                response = requests.post(API_URL, json=payload, timeout=60)
                response.raise_for_status()
                translated = response.json()["choices"][0]["text"].strip().lower()
                
                # Input Validation (Must match exact words)
                def check_keywords(text, keywords):
                    found = []
                    for kw in keywords:
                        if re.search(r'\b' + re.escape(kw) + r'\b', text):
                            found.append(kw)
                    return found

                found_expected = check_keywords(translated, expected)
                found_unexpected = check_keywords(translated, unexpected)

                # Criteria: ALL expected must be present, NO unexpected must be present
                input_passed = len(found_expected) == len(expected)
                negative_passed = len(found_unexpected) == 0
                
                is_pass = input_passed and negative_passed
                status = "PASS" if is_pass else "FAIL"
                if is_pass: passed_count += 1
                
                log(f"[{i+1}] {category} -> {status}")
                log(f"    Input:    {text}")
                log(f"    Actual:   {translated}")
                if not is_pass:
                    if not input_passed:
                        log(f"    Missing:  {[kw for kw in expected if kw not in found_expected]}")
                    if not negative_passed:
                        log(f"    Found Unexpected: {found_unexpected}")
                log("-" * 30)

            except Exception as e:
                log(f"[{i+1}] Error: {e}")

        log("=" * 60)
        log(f"Semantic Check Summary: {passed_count}/{len(SEMANTIC_TEST_CASES)} Passed")
        log("=" * 60)
    
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    test_semantic_errors()
