---
name: modal-indicconformer-stt
description: Deploy IndicConformer Speech-to-Text model on Modal with GPU. Use when deploying Indian language ASR (22 languages) as a web API on serverless GPU infrastructure.
---

# IndicConformer STT Deployment on Modal

## Overview

Deploy [ai4bharat/indic-conformer-600m-multilingual](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) as a FastAPI web service on Modal with GPU acceleration. This model supports **22 Indian languages** including Kannada, Hindi, Tamil, Telugu, etc.

**Model Details:**
- Architecture: Conformer-based Hybrid CTC + RNNT ASR
- Parameters: 600M
- Languages: 22 (IN-22)
- Decoding: CTC (fast) or RNNT (accurate)

## When to Use This Skill

Use when the user wants to:
- Deploy IndicConformer STT as a REST API
- Run Indian language speech-to-text on serverless GPU
- Create a transcription service for Kannada/Hindi/Tamil/other Indian languages
- Use Modal for ASR model hosting

## Prerequisites

1. **HuggingFace Account**: Must accept model license at https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual
2. **Modal Account**: https://modal.com (with credits)
3. **Secrets**: Create HuggingFace token secret in Modal:
   ```bash
   modal secret create huggingface-secret HF_TOKEN=hf_your_token
   ```

## Key Directives

1. **Use the template**: Copy `scripts/modal_indicconformer.py` as the starting point
2. **GPU Selection**: Default is A10G (24GB). Use T4 for cost savings, A100 for large batch
3. **Volume caching**: Model uses `HF_HOME=/cache/huggingface` on Modal Volume for fast restarts
4. **First cold start**: Takes ~2 minutes to download model, subsequent starts are fast

## Deployment Commands

```bash
# Deploy to Modal
modal deploy scripts/modal_indicconformer.py

# Test locally with live reload
modal serve scripts/modal_indicconformer.py
```

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Health check |
| GET | `/languages` | List supported languages |
| POST | `/transcribe` | Transcribe audio |

### Transcribe Request

```json
{
  "audio_b64": "<base64 encoded audio>",
  "language": "kn",
  "decoding": "ctc"
}
```

### Response

```json
{
  "transcription": "ನಮಸ್ಕಾರ",
  "language": "kn",
  "decoding": "ctc"
}
```

## Supported Languages

| Code | Language | Code | Language |
|------|----------|------|----------|
| `kn` | Kannada | `hi` | Hindi |
| `ta` | Tamil | `te` | Telugu |
| `ml` | Malayalam | `bn` | Bengali |
| `mr` | Marathi | `gu` | Gujarati |
| `pa` | Punjabi | `or` | Odia |
| `as` | Assamese | `ur` | Urdu |

Full list: `as, bn, brx, doi, gu, hi, kn, kok, ks, mai, ml, mni, mr, ne, or, pa, sa, sat, sd, ta, te, ur`

## Configuration Options

Modify `modal_indicconformer.py`:

```python
@app.cls(
    gpu="A10G",              # T4, L4, A10G, A100-40GB, A100-80GB
    timeout=10 * MINUTES,    # Max request time
    scaledown_window=5 * MINUTES,  # Keep warm after request
)
```

## Troubleshooting

### Cold Start Timeout
- First request takes 2+ minutes for model download
- Solution: Increase client timeout to 180+ seconds

### Volume Mount Error
- Error: "cannot mount volume on non-empty path"
- Solution: Mount volume at `/cache` not `/root/.cache/huggingface`

### Model Loading Error
- Error: "HFValidationError: Repo id must be in the form..."
- Solution: Use model ID (`ai4bharat/...`), not local path. Model has custom loading code.

## Scripts

- `scripts/modal_indicconformer.py` - Main deployment script
- `scripts/test_indicconformer.py` - Test client for the API

## Resources

- [Modal Docs - Web Endpoints](https://modal.com/docs/guide/webhooks)
- [Modal Docs - GPU](https://modal.com/docs/guide/gpu)
- [IndicConformer Model Card](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual)
- [AI4Bharat](https://ai4bharat.iitm.ac.in/)
