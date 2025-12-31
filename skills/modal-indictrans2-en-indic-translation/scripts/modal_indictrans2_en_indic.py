"""
Modal deployment for IndicTrans2 Translation model.
Model: ai4bharat/indictrans2-en-indic-1B (English → Indic)

Deploy:
    modal deploy src/modal_indictrans2_en_indic.py

Test locally:
    modal serve src/modal_indictrans2_en_indic.py

Note: Model is downloaded during deploy (image build) for fast cold starts.
"""

import modal

app = modal.App("indictrans2-en-indic")

# Model ID
MODEL_ID = "ai4bharat/indictrans2-en-indic-1B"
MODEL_DIR = "/model"  # Model stored in image

# Model is baked into image at /model - no volume needed


def download_model():
    """Download model during image build for fast cold starts."""
    import os
    from huggingface_hub import snapshot_download, login

    # Login with HF token
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        login(token=hf_token)

    # Download model to /model directory (will be baked into image)
    print(f"📥 Downloading {MODEL_ID}...")
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False,
    )
    print(f"✅ Model downloaded to {MODEL_DIR}")


# Container image with all dependencies
# Model is downloaded during image build
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git")
    .pip_install(
        "torch",
        "transformers==4.38.2",  # Pinned for compatibility with custom model code
        "indictranstoolkit",  # Correct PyPI package name
        "sentencepiece",
        "protobuf",
        "huggingface_hub",
        "fastapi[standard]",
        "pydantic",
    )
    .env({"HF_HOME": "/root/.cache/huggingface"})
    .run_function(
        download_model,
        secrets=[modal.Secret.from_name("huggingface-secret")],
    )
)


MINUTES = 60  # seconds


@app.cls(
    image=image,
    gpu="A10G",  # 24GB VRAM - sufficient for 1B params at FP16
    secrets=[modal.Secret.from_name("huggingface-secret")],
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
)
class IndicTrans2EnIndicService:
    """IndicTrans2 Translation service (English → Indic) with FastAPI web endpoints."""

    @modal.enter()
    def load_model(self):
        """Load model from pre-downloaded location (fast cold start)."""
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        from IndicTransToolkit.processor import IndicProcessor

        # Device setup
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔄 Loading model from {MODEL_DIR} on {self.device}...")

        # Load tokenizer and model from pre-downloaded directory
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_DIR,
            trust_remote_code=True,
        )

        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_DIR,
            trust_remote_code=True,
            torch_dtype=torch.float16,
        ).to(self.device)

        # Initialize IndicProcessor for preprocessing/postprocessing
        self.processor = IndicProcessor(inference=True)

        print("✅ IndicTrans2 model loaded successfully!")

    @modal.asgi_app()
    def web_app(self):
        """FastAPI web application with multiple endpoints."""
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        import torch

        web_app = FastAPI(
            title="IndicTrans2 En-Indic Translation API",
            description="English to Indic Translation API for 22 Indian languages",
            version="1.0.0",
        )

        class TranslateRequest(BaseModel):
            text: str | list[str]  # Single sentence or batch
            tgt_lang: str = "kan_Knda"  # Default: Kannada

        class TranslateResponse(BaseModel):
            translations: list[str]
            src_lang: str
            tgt_lang: str

        class HealthResponse(BaseModel):
            status: str
            model: str
            supported_languages: list[str]

        # FLORES-200 language codes for IndicTrans2
        SUPPORTED_LANGUAGES = {
            "asm_Beng": "Assamese",
            "ben_Beng": "Bengali",
            "brx_Deva": "Bodo",
            "doi_Deva": "Dogri",
            "guj_Gujr": "Gujarati",
            "hin_Deva": "Hindi",
            "kan_Knda": "Kannada",
            "kas_Arab": "Kashmiri (Arabic)",
            "kas_Deva": "Kashmiri (Devanagari)",
            "kok_Deva": "Konkani",
            "mai_Deva": "Maithili",
            "mal_Mlym": "Malayalam",
            "mni_Beng": "Manipuri (Bengali)",
            "mni_Mtei": "Manipuri (Meitei)",
            "mar_Deva": "Marathi",
            "npi_Deva": "Nepali",
            "ory_Orya": "Odia",
            "pan_Guru": "Punjabi",
            "san_Deva": "Sanskrit",
            "sat_Olck": "Santali",
            "snd_Arab": "Sindhi (Arabic)",
            "snd_Deva": "Sindhi (Devanagari)",
            "tam_Taml": "Tamil",
            "tel_Telu": "Telugu",
            "urd_Arab": "Urdu",
        }

        SRC_LANG = "eng_Latn"  # Source is always English

        @web_app.get("/health", response_model=HealthResponse)
        async def health():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy",
                model=MODEL_ID,
                supported_languages=list(SUPPORTED_LANGUAGES.keys()),
            )

        @web_app.post("/translate", response_model=TranslateResponse)
        async def translate(request: TranslateRequest):
            """Translate English text to Indic language."""
            try:
                # Validate target language
                if request.tgt_lang not in SUPPORTED_LANGUAGES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported language: {request.tgt_lang}. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
                    )

                # Handle single string or list
                sentences = [request.text] if isinstance(request.text, str) else request.text

                # Preprocess with IndicProcessor
                # For En-Indic, src_lang is English, tgt_lang is requested language
                batch = self.processor.preprocess_batch(
                    sentences,
                    src_lang=SRC_LANG,
                    tgt_lang=request.tgt_lang,
                )

                # Tokenize
                inputs = self.tokenizer(
                    batch,
                    truncation=True,
                    padding="longest",
                    return_tensors="pt",
                    return_attention_mask=True,
                ).to(self.device)

                # Generate translations
                with torch.no_grad():
                    generated_tokens = self.model.generate(
                        **inputs,
                        use_cache=True,
                        min_length=0,
                        max_length=256,
                        num_beams=5,
                        num_return_sequences=1,
                    )

                # Decode tokens
                decoded = self.tokenizer.batch_decode(
                    generated_tokens,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True,
                )

                # Postprocess translations
                translations = self.processor.postprocess_batch(decoded, lang=request.tgt_lang)

                return TranslateResponse(
                    translations=translations,
                    src_lang=SRC_LANG,
                    tgt_lang=request.tgt_lang,
                )

            except HTTPException:
                raise
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"{e}")

        @web_app.get("/languages")
        async def list_languages():
            """Get list of supported target language codes with names."""
            return {"languages": SUPPORTED_LANGUAGES, "source": "eng_Latn (English)"}

        return web_app


@app.local_entrypoint()
def main():
    print("🚀 IndicTrans2 En-Indic Translation Service deployed!")
    print("📍 Endpoints: /health, /languages, /translate")
