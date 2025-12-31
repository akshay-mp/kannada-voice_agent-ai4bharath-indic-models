"""
Modal deployment for IndicConformer STT (Speech-to-Text) model.
Model: ai4bharat/indic-conformer-600m-multilingual

Deploy:
    modal deploy scripts/modal_indicconformer.py

Test locally:
    modal serve scripts/modal_indicconformer.py
"""

import modal

app = modal.App("indicconformer-stt")

# Model ID
MODEL_ID = "ai4bharat/indic-conformer-600m-multilingual"

# Volume to cache model weights
model_cache = modal.Volume.from_name("indicconformer-cache", create_if_missing=True)

# Container image
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "transformers",
        "torch",
        "torchaudio",
        "torchcodec",
        "soundfile",
        "onnx",
        "onnxruntime-gpu",
        "huggingface_hub",
        "fastapi[standard]",
        "pydantic",
    )
)


MINUTES = 60  # seconds

@app.cls(
    image=image,
    gpu="A10G",  # Options: T4, L4, A10G, A100-40GB, A100-80GB
    secrets=[modal.Secret.from_name("huggingface-secret")],
    volumes={"/cache": model_cache},
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
)
class IndicConformerSTT:
    """IndicConformer STT service with FastAPI web endpoints."""

    @modal.enter()
    def load_model(self):
        """Load model - uses volume cache for fast restarts."""
        import os
        from huggingface_hub import login
        from transformers import AutoModel

        # Set HuggingFace cache to volume (persists between restarts)
        os.environ["HF_HOME"] = "/cache/huggingface"
        os.makedirs("/cache/huggingface", exist_ok=True)

        # Authenticate with HuggingFace (gated model)
        login(token=os.environ["HF_TOKEN"])

        # Load model (will use cache if already downloaded)
        print(f"🔄 Loading {MODEL_ID}...")
        self.model = AutoModel.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
        )
        
        # Commit volume to persist the cache
        model_cache.commit()
        print("✅ IndicConformer model loaded successfully!")

    @modal.asgi_app()
    def web_app(self):
        """FastAPI web application with multiple endpoints."""
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        import base64
        import io
        import torch
        import torchaudio

        web_app = FastAPI(
            title="IndicConformer STT API",
            description="Speech-to-Text API for 22 Indian languages",
            version="1.0.0",
        )

        class TranscribeRequest(BaseModel):
            audio_b64: str
            language: str = "kn"  # Default: Kannada
            decoding: str = "ctc"  # "ctc" or "rnnt"

        class TranscribeResponse(BaseModel):
            transcription: str
            language: str
            decoding: str

        class HealthResponse(BaseModel):
            status: str
            model: str
            supported_languages: list[str]

        SUPPORTED_LANGUAGES = [
            "as", "bn", "brx", "doi", "gu", "hi", "kn", "kok", "ks",
            "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat",
            "sd", "ta", "te", "ur"
        ]

        @web_app.get("/health", response_model=HealthResponse)
        async def health():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy",
                model=MODEL_ID,
                supported_languages=SUPPORTED_LANGUAGES,
            )

        @web_app.post("/transcribe", response_model=TranscribeResponse)
        async def transcribe(request: TranscribeRequest):
            """Transcribe audio to text."""
            try:
                if request.language not in SUPPORTED_LANGUAGES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported language: {request.language}"
                    )

                if request.decoding not in ["ctc", "rnnt"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid decoding: {request.decoding}. Use 'ctc' or 'rnnt'"
                    )

                # Decode audio from base64
                audio_bytes = base64.b64decode(request.audio_b64)
                wav, sr = torchaudio.load(io.BytesIO(audio_bytes))

                # Convert to mono
                wav = torch.mean(wav, dim=0, keepdim=True)

                # Resample to 16kHz if needed
                if sr != 16000:
                    resampler = torchaudio.transforms.Resample(
                        orig_freq=sr, new_freq=16000
                    )
                    wav = resampler(wav)

                # Transcribe
                transcription = self.model(wav, request.language, request.decoding)

                return TranscribeResponse(
                    transcription=transcription,
                    language=request.language,
                    decoding=request.decoding,
                )

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @web_app.get("/languages")
        async def list_languages():
            """Get list of supported language codes with names."""
            language_names = {
                "as": "Assamese", "bn": "Bengali", "brx": "Bodo",
                "doi": "Dogri", "gu": "Gujarati", "hi": "Hindi",
                "kn": "Kannada", "kok": "Konkani", "ks": "Kashmiri",
                "mai": "Maithili", "ml": "Malayalam", "mni": "Manipuri",
                "mr": "Marathi", "ne": "Nepali", "or": "Odia",
                "pa": "Punjabi", "sa": "Sanskrit", "sat": "Santali",
                "sd": "Sindhi", "ta": "Tamil", "te": "Telugu", "ur": "Urdu"
            }
            return {"languages": language_names}

        return web_app


@app.local_entrypoint()
def main():
    print("🚀 IndicConformer STT deployed!")
    print("📍 Endpoints: /health, /languages, /transcribe")
