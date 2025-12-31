# Modal IndicF5 TTS Skill

Deploy `ai4bharat/IndicF5` Text-to-Speech model on Modal for Indian language speech synthesis.

## Model

- **Model ID**: `ai4bharat/IndicF5`
- **Type**: Text-to-Speech (TTS)
- **Languages**: 11 Indian languages (Hindi, Kannada, Tamil, Telugu, Bengali, Gujarati, Marathi, Malayalam, Odia, Punjabi, Assamese)

## Endpoint

**URL**: `https://akshaymp-1810--indicf5-tts-indicf5service-generate.modal.run`

**Method**: `POST`

### Request Format

```json
{
  "text": "Text to synthesize",
  "ref_audio": "base64_encoded_audio (optional)",
  "ref_text": "Transcript of ref audio (required if ref_audio provided)"
}
```

### Response

- **Content-Type**: `audio/wav`
- **Sample Rate**: 24000 Hz

## Key Dependencies

```python
"git+https://github.com/AI4Bharat/IndicF5.git"
"transformers==4.49.0"  # Critical: fixes meta tensor issue
"torchcodec"            # Required for audio loading
"torchaudio"
"soundfile"
```

## Critical Notes

1. **transformers==4.49.0**: Pinned version to fix Vocos vocoder meta tensor issue
2. **Load from HuggingFace ID**: Use `ai4bharat/IndicF5` repo ID, not local path (custom code needs repo ID for internal downloads)
3. **device_map=None, low_cpu_mem_usage=False**: Disable accelerate's auto device mapping
4. **Response format**: Use `Response(content=bytes, media_type="audio/wav")` for binary audio

## Usage Example

```python
import httpx

response = httpx.post(
    "https://akshaymp-1810--indicf5-tts-indicf5service-generate.modal.run",
    json={"text": "नमस्ते, आप कैसे हैं?"},
    timeout=120.0
)

with open("output.wav", "wb") as f:
    f.write(response.content)
```

## Files

- [modal_indicf5.py](scripts/modal_indicf5.py) - Modal deployment script
- [test_indicf5.py](scripts/test_indicf5.py) - Test script
