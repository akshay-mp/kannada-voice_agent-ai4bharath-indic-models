---
name: modal-indictrans2-en-indic-translation
description: Deploy IndicTrans2 (En-Indic) translation model on Modal. Use when deploying English to Indian language translation (22 languages) as a web API on serverless GPU infrastructure.
---

# IndicTrans2 En-Indic Translation Deployment on Modal

## Overview

Deploy [ai4bharat/indictrans2-en-indic-1B](https://huggingface.co/ai4bharat/indictrans2-en-indic-1B) as a FastAPI web service on Modal with GPU acceleration. This model translates **English → 22 Indian languages** with 1.1B parameters.

**Model Details:**
- Architecture: Transformer Seq2Seq
- Direction: English → Indic
- Languages: 22 (FLORES-200 codes)

## When to Use This Skill

Use when the user wants to:
- Translate English text to Kannada, Hindi, Tamil, etc. via API.
- Deploy the reverse direction of the `indic-en` model.
- Host the model on serverless GPU (A10G/A100).

## Dependencies (Critical)
Requires specific versions for compatibility with the model's custom code:
- `transformers==4.38.2`: Essential to prevent `NoneType` errors.
- `indictranstoolkit`: Use lowercase package name.

## Deployment Commands

```bash
# Deploy to Modal
modal deploy scripts/modal_indictrans2_en_indic.py

# Test locally with live reload
modal serve scripts/modal_indictrans2_en_indic.py
```

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Health check |
| GET | `/languages` | List supported target languages |
| POST | `/translate` | Translate English text to Indic |

### Translate Request

```json
{
  "text": "Hello, how are you?",
  "tgt_lang": "kan_Knda"
}
```

### Response

```json
{
  "translations": ["ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಾ?"],
  "src_lang": "eng_Latn",
  "tgt_lang": "kan_Knda"
}
```

## Supported Languages (Target)
`kan_Knda` (Kannada), `hin_Deva` (Hindi), `tam_Taml` (Tamil), `tel_Telu` (Telugu), `mal_Mlym` (Malayalam), `ben_Beng` (Bengali), and more.

## Resources
- [Modal Web Endpoints](https://modal.com/docs/guide/webhooks)
- [IndicTrans2 En-Indic Model](https://huggingface.co/ai4bharat/indictrans2-en-indic-1B)
