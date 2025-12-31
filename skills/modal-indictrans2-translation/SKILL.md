---
name: modal-indictrans2-translation
description: Deploy IndicTrans2 translation model on Modal with GPU. Use when deploying Indian language to English translation (22 languages) as a web API on serverless GPU infrastructure.
---

# IndicTrans2 Translation Deployment on Modal

## Overview

Deploy [ai4bharat/indictrans2-indic-en-1B](https://huggingface.co/ai4bharat/indictrans2-indic-en-1B) as a FastAPI web service on Modal with GPU acceleration. This model translates **22 Indian languages → English** with 1.1B parameters.

**Model Details:**
- Architecture: Transformer Seq2Seq
- Parameters: 1.1B
- Direction: Indic → English
- Languages: 22 (FLORES-200 codes)

## When to Use This Skill

Use when the user wants to:
- Deploy IndicTrans2 translation as a REST API
- Run Indian language translation on serverless GPU
- Create a translation service for Kannada/Hindi/Tamil → English
- Use Modal for translation model hosting

## Prerequisites

1. **HuggingFace Account**: Accept model license at https://huggingface.co/ai4bharat/indictrans2-indic-en-1B
2. **Modal Account**: https://modal.com (with credits)
3. **Secrets**: Create HuggingFace token secret in Modal:
   ```bash
   modal secret create huggingface-secret HF_TOKEN=hf_your_token
   ```

## Key Directives

1. **Use the template**: Copy `scripts/modal_indictrans2.py` as starting point
2. **GPU Selection**: Default is A10G (24GB). Use T4 for cost savings, A100 for large batch
3. **Volume caching**: Model uses `HF_HOME=/root/.cache/huggingface` in the image
4. **First cold start**: Takes ~3 minutes to download 1B model (baked into image)
5. **Dependencies**: Requires specific versions for compatibility:
    - `transformers==4.38.2`: Essential to prevent "NoneType has no attribute 'shape'" error with the model's custom code.
    - `indictranstoolkit`: Use lowercase package name for correct pip installation.

## Deployment Commands

```bash
# Deploy to Modal
modal deploy scripts/modal_indictrans2.py

# Test locally with live reload
modal serve scripts/modal_indictrans2.py
```

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Health check |
| GET | `/languages` | List supported languages |
| POST | `/translate` | Translate Indic text to English |

### Translate Request

```json
{
  "text": "ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ?",
  "src_lang": "kan_Knda"
}
```

### Response

```json
{
  "translations": ["Hello, how are you?"],
  "src_lang": "kan_Knda",
  "tgt_lang": "eng_Latn"
}
```

### Batch Translation

```json
{
  "text": ["ನಮಸ್ಕಾರ", "ಧನ್ಯವಾದಗಳು"],
  "src_lang": "kan_Knda"
}
```

## Supported Languages (FLORES-200 Codes)

| Code | Language | Code | Language |
|------|----------|------|----------|
| `kan_Knda` | Kannada | `hin_Deva` | Hindi |
| `tam_Taml` | Tamil | `tel_Telu` | Telugu |
| `mal_Mlym` | Malayalam | `ben_Beng` | Bengali |
| `mar_Deva` | Marathi | `guj_Gujr` | Gujarati |
| `pan_Guru` | Punjabi | `ory_Orya` | Odia |
| `asm_Beng` | Assamese | `urd_Arab` | Urdu |

Full list: `asm_Beng, ben_Beng, brx_Deva, doi_Deva, guj_Gujr, hin_Deva, kan_Knda, kas_Arab, kas_Deva, kok_Deva, mai_Deva, mal_Mlym, mni_Beng, mni_Mtei, mar_Deva, npi_Deva, ory_Orya, pan_Guru, san_Deva, sat_Olck, snd_Arab, snd_Deva, tam_Taml, tel_Telu, urd_Arab`

## Configuration Options

Modify `modal_indictrans2.py`:

```python
@app.cls(
    gpu="A10G",              # T4, L4, A10G, A100-40GB, A100-80GB
    timeout=10 * MINUTES,    # Max request time
    scaledown_window=5 * MINUTES,  # Keep warm after request
)
```

## Troubleshooting

### Cold Start Timeout
- First request takes 3+ minutes for model download
- Solution: Increase client timeout to 180+ seconds

### IndicTransToolkit Import Error
- Error: `ModuleNotFoundError: No module named 'IndicTransToolkit'`
- Solution: Ensure `IndicTransToolkit` is in pip_install list

### Language Code Error
- Error: `Unsupported language: kn`
- Solution: Use FLORES-200 codes (e.g., `kan_Knda` not `kn`)

## Scripts

- `scripts/modal_indictrans2.py` - Main deployment script
- `scripts/test_indictrans2.py` - Test client for the API

## Resources

- [Modal Docs - Web Endpoints](https://modal.com/docs/guide/webhooks)
- [Modal Docs - GPU](https://modal.com/docs/guide/gpu)
- [IndicTrans2 Model Card](https://huggingface.co/ai4bharat/indictrans2-indic-en-1B)
- [IndicTransToolkit GitHub](https://github.com/VarunGumma/IndicTransToolkit)
- [AI4Bharat](https://ai4bharat.iitm.ac.in/)
