# Modal IndicConformer STT Skill

Deploy [ai4bharat/indic-conformer-600m-multilingual](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) on Modal with GPU.

## Quick Start

```bash
# 1. Create secret
modal secret create huggingface-secret HF_TOKEN=hf_your_token

# 2. Deploy
cd skills/modal-indicconformer-stt
modal deploy scripts/modal_indicconformer.py

# 3. Test
python scripts/test_indicconformer.py --file audio.wav --language kn
```

## Supported Languages

`as, bn, brx, doi, gu, hi, kn, kok, ks, mai, ml, mni, mr, ne, or, pa, sa, sat, sd, ta, te, ur`

## Files

- `SKILL.md` - Agent instructions
- `scripts/modal_indicconformer.py` - Modal deployment
- `scripts/test_indicconformer.py` - Test client
