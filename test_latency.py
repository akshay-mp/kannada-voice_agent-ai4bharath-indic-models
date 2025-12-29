import time
import requests
import json
import statistics

# Update this with the actual URL after deployment
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

Instruction: translate LLM response to kanglish
Input: Here is your order.
Output: ಇಲ್ಲಿ ನಿಮ್ಮ ಆರ್ಡರ್ ಇದೆ.

Instruction: translate LLM response to kanglish
Input: Payment is successful.
Output: Payment ಯಶಸ್ವಿಯಾಗಿದೆ.

Instruction: {}
Input: {}
Output:"""

TEST_DATA = [
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Showing formal and casual black shirts.",
    "output": "Formal ಮತ್ತು casual black shirts ತೋರಿಸಲಾಗುತ್ತಿದೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ guitar beginners ಗೆ ಒಳ್ಳೆಯದಾ?",
    "output": "Is this guitar good for beginners?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "No, it comes with leak-proof lids.",
    "output": "ಇಲ್ಲ, ಇದು leak-proof ಮುಚ್ಚಳಗಳೊಂದಿಗೆ ಬರುತ್ತದೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಸೀರೆಗೆ ಬ್ಲೌಸ್ ಪೀಸ್ ಇದೆಯಾ?",
    "output": "Is there a blouse piece for this saree?"
  },
  {
    "instruction": "translate user query to english",
    "input": "ನನಗೆ ಕ್ಯಾಶ್ಯೂ ನಟ್ಸ್ ಬೇಕು.",
    "output": "I want cashew nuts."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಕೀಬೋರ್ಡ್ ಲೈಟ್ ಆಫ್ ಮಾಡಬಹುದಾ?",
    "output": "Can I turn off the light of this keyboard?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Go to the product page and scroll down to 'Ratings & Reviews' to write your review.",
    "output": "Product page ಗೆ ಹೋಗಿ, ಕೆಳಗೆ 'Ratings & Reviews' ಗೆ scroll ಮಾಡಿ ನಿಮ್ಮ review ಬರೆಯಿರಿ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಪ್ಯಾಂಟ್ ಗೆ ಪಾಕೆಟ್ಸ್ ಇದೆಯಾ?",
    "output": "Does this pant have pockets?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Grocery items are non-returnable due to hygiene reasons, unless delivered expired or damaged.",
    "output": "Hygiene reasons ಇರೋದ್ರಿಂದ Grocery items non-returnable, ಆದರೆ expired ಅಥವಾ damaged deliver ಆಗಿದ್ರೆ return ಮಾಡಬಹುದು."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಬೆಡ್ ಶೀಟ್ ಡಬಲ್ ಕಾಟ್ ಗೆ ಆಗುತ್ತಾ?",
    "output": "Will this bedsheet fit a double cot?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Please enter your pincode to verify delivery service.",
    "output": "Delivery service verify ಮಾಡಲು ದಯವಿಟ್ಟು ನಿಮ್ಮ pincode ಹಾಕಿ."
  },
  {
    "instruction": "translate user query to english",
    "input": "Subscription ತಗೊಂಡ್ರೆ delivery free ಸಿಗುತ್ತಾ?",
    "output": "Will I get free delivery if I take the subscription?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "The manufacturing date is printed on the back of the package near the barcode.",
    "output": "Manufacturing date package ನ ಹಿಂಭಾಗದಲ್ಲಿ barcode ಹತ್ತಿರ print ಆಗಿರುತ್ತೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ವಾಚ್ ವಾಟರ್ ಪ್ರೂಫ್ ಹೌದಾ?",
    "output": "Is this watch waterproof?"
  },
  {
    "instruction": "translate user query to english",
    "input": "ನನ್ನ ಅಕೌಂಟ್ ಲಾಕ್ ಆಗಿದೆ.",
    "output": "My account is locked."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಪರ್ಫ್ಯೂಮ್ ಸ್ಮೆಲ್ ಎಷ್ಟು ಹೊತ್ತು ಇರುತ್ತೆ?",
    "output": "How long does the smell of this perfume last?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Showing you slim and regular fit black jeans.",
    "output": "ನಿಮಗೆ slim ಮತ್ತು regular fit black jeans ತೋರಿಸ್ತಿದೀನಿ."
  },
  {
    "instruction": "translate user query to english",
    "input": "Grocery items return ಮಾಡಬಹುದಾ?",
    "output": "Can grocery items be returned?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Here are some durable wireless keyboards.",
    "output": "ಇಲ್ಲಿ ಕೆಲವು ಬಾಳಿಕೆ ಬರುವ wireless keyboards ಇವೆ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Yes, this helmet is ISI certified and meets safety standards.",
    "output": "ಹೌದು, ಈ helmet ISI certified ಆಗಿದೆ ಮತ್ತು safety standards ಪಾಲಿಸುತ್ತೆ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Here is a collection of popular Kannada novels.",
    "output": "ಜನಪ್ರಿಯ ಕನ್ನಡ ಕಾದಂಬರಿಗಳ ಸಂಗ್ರಹ ಇಲ್ಲಿದೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ರಿಮೋಟ್ ಗೆ ಬ್ಯಾಟರಿ ಹಾಕಬೇಕಾ ಅಥವಾ ಚಾರ್ಜ್ ಮಾಡಬೇಕಾ?",
    "output": "Do I need to put batteries in this remote or charge it?"
  },
  {
    "instruction": "translate user query to english",
    "input": "5 star rating ಇರುವ best mixer grinder ಯಾವುದು?",
    "output": "Which is the best mixer grinder with a 5 star rating?"
  },
  {
    "instruction": "translate user query to english",
    "input": "ನನ್ನ ಅಕೌಂಟ್ ಲಾಗಿನ್ ಆಗ್ತಿಲ್ಲ.",
    "output": "My account is not logging in."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ವಾಚ್ ಗೆ ಸ್ಟ್ರಾಪ್ ಚೇಂಜ್ ಮಾಡಬಹುದಾ?",
    "output": "Can I change the strap for this watch?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Here are organic green tea options from top brands.",
    "output": "Top brands ನಿಂದ organic green tea options ಇಲ್ಲಿವೆ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Yes, this is made of cotton lycra blend and is stretchable.",
    "output": "ಹೌದು, ಇದು cotton lycra blend ನಿಂದ ಮಾಡಲ್ಪಟ್ಟಿದೆ ಮತ್ತು stretchable ಆಗಿದೆ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "It has a 4.2-star rating with positive feedback on quality.",
    "output": "Quality ಬಗ್ಗೆ positive feedback ಜೊತೆಗೆ ಇದಕ್ಕೆ 4.2-star rating ಇದೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ earphone ನಲ್ಲಿ noise cancellation ಇದ್ಯಾ?",
    "output": "Does this earphone have noise cancellation?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Yes, you can cast your phone screen to the TV.",
    "output": "ಹೌದು, ನೀವು ನಿಮ್ಮ phone screen ನ TV ಗೆ cast ಮಾಡಬಹುದು."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಫೇಸ್ ವಾಶ್ ಆಯಿಲಿ ಸ್ಕಿನ್ ಗೆ ಆಗುತ್ತಾ?",
    "output": "Is this face wash suitable for oily skin?"
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಪ್ರೊಡಕ್ಟ್ ಗೆ ರಿಟರ್ನ್ ಪಾಲಿಸಿ ಇದೆಯಾ?",
    "output": "Is there a return policy for this product?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Yes, select the 'Gift' option at checkout for Rs 30.",
    "output": "ಹೌದು, checkout ನಲ್ಲಿ Rs 30 ಕೊಟ್ಟು 'Gift' option select ಮಾಡಿ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Please wait for 15 minutes before retrying.",
    "output": "ದಯವಿಟ್ಟು retry ಮಾಡುವ ಮುಂಚೆ 15 ನಿಮಿಷ wait ಮಾಡಿ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಡ್ರೆಸ್ ಮೆಟೀರಿಯಲ್ ಕಾಟನ್ ಆ?",
    "output": "Is this dress material cotton?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "No, this model works via Bluetooth and doesn't support a SIM card.",
    "output": "ಇಲ್ಲ, ಈ model Bluetooth ಮೂಲಕ ಕೆಲಸ ಮಾಡುತ್ತೆ ಮತ್ತು SIM card support ಮಾಡಲ್ಲ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Here are some 100% cotton double bedsheets with pillow covers.",
    "output": "Pillow covers ಜೊತೆಗಿರೋ ಕೆಲವು 100% cotton double bedsheets ಇಲ್ಲಿವೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "iPhone 13 ಮತ್ತು 14 ಮಧ್ಯೆ ಏನು difference ಇದೆ?",
    "output": "What is the difference between iPhone 13 and 14?"
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಸ್ಮಾರ್ಟ್ ವಾಚ್ ಗೆ ಕಾಲಿಂಗ್ ಫೀಚರ್ ಇದೆಯಾ?",
    "output": "Does this smart watch have a calling feature?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Yes, just update the shipping address to theirs.",
    "output": "ಹೌದು, shipping address ಅನ್ನು ಅವರದ್ದಕ್ಕೆ update ಮಾಡಿ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Yes, it comes with a separate jar for juicing.",
    "output": "ಹೌದು, ಇದು juicing ಗೆ ಅಂತಾನೇ separate jar ಜೊತೆ ಬರುತ್ತೆ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Yes, they have dual mics for clear calls.",
    "output": "ಹೌದು, clear calls ಗಾಗಿ ಇವುಗಳಲ್ಲಿ dual mics ಇವೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಟಿವಿ ಸ್ಕ್ರೀನ್ ಮಿರರಿಂಗ್ ಸಪೋರ್ಟ್ ಮಾಡುತ್ತಾ?",
    "output": "Does this TV support screen mirroring?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Orders above Rs. 500 qualify for free delivery.",
    "output": "Rs. 500 ಕ್ಕಿಂತ ಮೇಲಿನ orders ಗೆ free delivery ಸಿಗುತ್ತೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಚೇರ್ ಗೆ ವೀಲ್ಸ್ ಇದೆಯಾ?",
    "output": "Does this chair have wheels?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "It offers up to 10 hours of playback time on a single charge.",
    "output": "ಇದು single charge ನಲ್ಲಿ 10 hours ವರೆಗೆ playback time ನೀಡುತ್ತದೆ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Please refresh the page and try again, or check your internet connection.",
    "output": "ದಯವಿಟ್ಟು page refresh ಮಾಡಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ, ಅಥವಾ ನಿಮ್ಮ internet connection check ಮಾಡಿ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಟಿ ಶರ್ಟ್ ಕಲರ್ ಫೇಡ್ ಆಗುತ್ತಾ?",
    "output": "Does the color of this t-shirt fade?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Click on the 'Size Chart' link next to the size options.",
    "output": "Size options ಪಕ್ಕದಲ್ಲಿರೋ 'Size Chart' link ಮೇಲೆ click ಮಾಡಿ."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "Yes, it features Active Noise Cancellation (ANC) up to 25dB.",
    "output": "ಹೌದು, ಇದರಲ್ಲಿ 25dB ವರೆಗೆ Active Noise Cancellation (ANC) ಇದೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ sunscreen oily skin ಗೆ set ಆಗುತ್ತಾ?",
    "output": "Does this sunscreen suit oily skin?"
  },
  {
    "instruction": "translate user query to english",
    "input": "Warranty claim ಮಾಡೋದು ಹೇಗೆ?",
    "output": "How to claim the warranty?"
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಕುರ್ತಾ ಸೈಜ್ ಚಿಕ್ಕದಾದರೆ ರಿಟರ್ನ್ ಮಾಡಬಹುದಾ?",
    "output": "If the kurta size is small, can I return it?"
  },
  {
    "instruction": "translate user query to english",
    "input": "ನನಗೆ ಮೈಕ್ರೋವೇವ್ ಓವನ್ ಬೇಕು.",
    "output": "I want a microwave oven."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "The 'Big Billion Days' sale ends tonight at 11:59 PM.",
    "output": "'Big Billion Days' sale ಇವತ್ತು ರಾತ್ರಿ 11:59 PM ಗೆ ಮುಗಿಯುತ್ತೆ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಟಾಯ್ ಸೇಫ್ ಆ?",
    "output": "Is this toy safe?"
  },
  {
    "instruction": "translate user query to english",
    "input": "ನನಗೆ 500 ರೂಪಾಯಿ ಒಳಗೆ ಬರುವ best bluetooth mouse ಬೇಕು.",
    "output": "I want the best bluetooth mouse under 500 rupees."
  },
  {
    "instruction": "translate user query to english",
    "input": "ನನಗೆ 10000mAh power bank ಬೇಕು.",
    "output": "I want a 10000mAh power bank."
  },
  {
    "instruction": "translate user query to english",
    "input": "ನನಗೆ 5G ಮೊಬೈಲ್ ಮಾತ್ರ ತೋರಿಸಿ.",
    "output": "Show me only 5G mobiles."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ ಜೀನ್ಸ್ ಸ್ಲಿಮ್ ಫಿಟ್ ಆ?",
    "output": "Is this jeans slim fit?"
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "This is a borosilicate glass bottle.",
    "output": "ಇದು borosilicate glass bottle."
  },
  {
    "instruction": "translate LLM response to kanglish",
    "input": "I apologize for the inconvenience. Please go to 'My Orders' and raise a return request immediately.",
    "output": "ತೊಂದರೆಗೆ ಕ್ಷಮಿಸಿ. ದಯವಿಟ್ಟು 'My Orders' ಗೆ ಹೋಗಿ ಕೂಡಲೇ return request raise ಮಾಡಿ."
  },
  {
    "instruction": "translate user query to english",
    "input": "ಈ memory card ನನ್ನ camera ಗೆ support ಮಾಡುತ್ತಾ?",
    "output": "Does this memory card support my camera?"
  }
]


def test_latency():
    output_file = "evaluation_results.txt"
    latencies = []
    
    with open(output_file, "w", encoding="utf-8") as f:
        def log(msg):
            print(msg)
            f.write(msg + "\n")
            
        log(f"Testing API: {API_URL}")
        log("-" * 50)
        log(f"Total test cases: {len(TEST_DATA)}")
        log("-" * 50)

        # Warm-up
        log("Performing Warm-up Request...")
        try:
            warmup_input = TEST_DATA[0]["input"]
            warmup_prompt = PROMPT_TEMPLATE.format(TEST_DATA[0]["instruction"], warmup_input)
            warmup_payload = {
                "model": "ambari-merged",
                "prompt": warmup_prompt,
                "max_tokens": 256,
                "temperature": 0.1,
                "top_p": 0.95,
                "repetition_penalty": 1.1,
                "stop": ["<|endoftext|>"]
            }
            start_time = time.time()
            requests.post(API_URL, json=warmup_payload, timeout=120)  # Increased timeout for warm-up
            end_time = time.time()
            log(f"Warm-up complete. Latency: {(end_time - start_time) * 1000:.2f} ms")
            log("-" * 50)
        except Exception as e:
            log(f"Warm-up failed: {e}")
            log("-" * 50)

        for i, item in enumerate(TEST_DATA):
            instruction = item["instruction"]
            text = item["input"]
            expected = item["output"]
            
            prompt = PROMPT_TEMPLATE.format(instruction, text)
            payload = {
                "model": "ambari-merged",
                "prompt": prompt,
                "max_tokens": 256,
                "temperature": 0.1,
                "top_p": 0.95,
                "repetition_penalty": 1.1,
                "stop": ["<|endoftext|>"]
            }

            try:
                start_time = time.time()
                response = requests.post(API_URL, json=payload, timeout=60) # Increased timeout
                response.raise_for_status()
                end_time = time.time()
                
                latency = (end_time - start_time) * 1000 # ms
                latencies.append(latency)
                
                result = response.json()
                translated = result["choices"][0]["text"].strip()
                
                log(f"[{i+1}/{len(TEST_DATA)}] Latency: {latency:.2f} ms")
                log(f"    Input:    {text}")
                log(f"    Expected: {expected}")
                log(f"    Actual:   {translated}")
                log("-" * 30)
                
            except Exception as e:
                log(f"[{i+1}/{len(TEST_DATA)}] Error: {e}")

        if latencies:
            avg_latency = statistics.mean(latencies)
            total_time = sum(latencies) / 1000
            log("=" * 50)
            log("PERFORMANCE SUMMARY")
            log("=" * 50)
            log(f"Total Requests: {len(latencies)}")
            log(f"Total Time:     {total_time:.2f} s")
            log(f"Average Latency: {avg_latency:.2f} ms")
            log(f"Min Latency:     {min(latencies):.2f} ms")
            log(f"Max Latency:     {max(latencies):.2f} ms")
            log("=" * 50)
        else:
            log("No successful requests.")
        
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    test_latency()
