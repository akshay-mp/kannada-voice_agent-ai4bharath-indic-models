# IndicTrans2 Modal Deployment

Deploy IndicTrans2 (Indic → English) translation model on Modal with GPU.

## Quick Start

```bash
# Deploy
modal deploy scripts/modal_indictrans2.py

# Test locally
modal serve scripts/modal_indictrans2.py
```

## Prerequisites

1. Accept model license: https://huggingface.co/ai4bharat/indictrans2-indic-en-1B
2. Create Modal secret:
   ```bash
   modal secret create huggingface-secret HF_TOKEN=hf_your_token
   ```

## Usage

```python
import httpx

response = httpx.post(
    "https://<modal-url>/translate",
    json={"text": "ನಮಸ್ಕಾರ", "src_lang": "kan_Knda"}
)
print(response.json())
# {"translations": ["Hello"], "src_lang": "kan_Knda", "tgt_lang": "eng_Latn"}
```

See [SKILL.md](./SKILL.md) for full documentation.
