"""
Modal deployment for Unified Voice Agent.
Consolidates STT, Translation (In/Out), and TTS into a single GPU container.

Deploy:
    modal deploy src/modal/modal_unified.py

Benefits:
    - 75% cost reduction (4x A10G -> 1x A10G)
    - Zero inter-service network latency
    - Single cold-start penalty
"""

import modal
import sys

app = modal.App("unified-voice-agent")

# Model IDs
STT_MODEL_ID = "ai4bharat/indic-conformer-600m-multilingual"
TRANS_INDIC_EN_MODEL_ID = "ai4bharat/indictrans2-indic-en-1B"
TRANS_EN_INDIC_MODEL_ID = "ai4bharat/indictrans2-en-indic-1B"
TTS_MODEL_ID = "ai4bharat/IndicF5"

# Paths
TRANS_INDIC_EN_DIR = "/models/indictrans2-indic-en"
TRANS_EN_INDIC_DIR = "/models/indictrans2-en-indic"
TTS_MODEL_DIR = "/models/indicf5"
REF_AUDIO_URL = "https://raw.githubusercontent.com/AI4Bharat/IndicF5/main/prompts/KAN_F_HAPPY_00001.wav"
REF_AUDIO_PATH = "/models/indicf5/default_ref.wav"
REF_TEXT_DEFAULT = "ನಮ್‌ ಫ್ರಿಜ್ಜಲ್ಲಿ ಕೂಲಿಂಗ್‌ ಸಮಸ್ಯೆ ಆಗಿ ನಾನ್‌ ಭಾಳ ದಿನದಿಂದ ಒದ್ದಾಡ್ತಿದ್ದೆ, ಆದ್ರೆ ಅದ್ನೀಗ ಮೆಕಾನಿಕ್ ಆಗಿರೋ ನಿಮ್‌ ಸಹಾಯ್ದಿಂದ ಬಗೆಹರಿಸ್ಕೋಬೋದು ಅಂತಾಗಿ ನಿರಾಳ ಆಯ್ತು ನಂಗೆ."


def download_all_models():
    """Download all models during image build."""
    import os
    import requests
    from huggingface_hub import snapshot_download, login

    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        login(token=hf_token)

    # Download IndicTrans2 Indic-En
    print(f"📥 Downloading {TRANS_INDIC_EN_MODEL_ID}...")
    snapshot_download(
        repo_id=TRANS_INDIC_EN_MODEL_ID,
        local_dir=TRANS_INDIC_EN_DIR,
        local_dir_use_symlinks=False,
    )
    print(f"✅ Downloaded to {TRANS_INDIC_EN_DIR}")

    # Download IndicTrans2 En-Indic
    print(f"📥 Downloading {TRANS_EN_INDIC_MODEL_ID}...")
    snapshot_download(
        repo_id=TRANS_EN_INDIC_MODEL_ID,
        local_dir=TRANS_EN_INDIC_DIR,
        local_dir_use_symlinks=False,
    )
    print(f"✅ Downloaded to {TRANS_EN_INDIC_DIR}")

    # Download IndicF5 TTS
    print(f"📥 Downloading {TTS_MODEL_ID}...")
    snapshot_download(
        repo_id=TTS_MODEL_ID,
        local_dir=TTS_MODEL_DIR,
        local_dir_use_symlinks=False,
    )
    print(f"✅ Downloaded to {TTS_MODEL_DIR}")

    # Download default reference audio for TTS
    print(f"📥 Downloading reference audio...")
    try:
        response = requests.get(REF_AUDIO_URL, timeout=30)
        response.raise_for_status()
        os.makedirs(os.path.dirname(REF_AUDIO_PATH), exist_ok=True)
        with open(REF_AUDIO_PATH, "wb") as f:
            f.write(response.content)
        print(f"✅ Reference audio saved to {REF_AUDIO_PATH}")
    except Exception as e:
        print(f"⚠️ Failed to download reference audio: {e}")


# Image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg", "libsndfile1")
    .pip_install(
        # STT
        "transformers==4.49.0",  # Pinned to fix meta tensor issue in F5-TTS
        "torch",
        "torchaudio",
        "torchcodec",
        "soundfile",
        "onnx",
        "onnxruntime-gpu",
        # Translation
        "indictranstoolkit",
        "sentencepiece",
        "protobuf",
        # TTS
        "git+https://github.com/AI4Bharat/IndicF5.git",
        "safetensors",
        "numpy",
        "librosa",
        # Common
        "huggingface_hub",
        "fastapi[standard]",
        "pydantic",
        # Agent
        "langchain",
        "langchain-community",
        "langchain-openai",
        "langchain-tavily",
        "langgraph",
        "tavily-python",
        "python-dotenv",
        "tiktoken",
    )
    .env({"HF_HOME": "/root/.cache/huggingface"})
    .run_function(
        download_all_models,
        secrets=[modal.Secret.from_name("huggingface-secret")],
    )
    .add_local_dir("src/voice_agent", remote_path="/root/src/voice_agent")
)

# Volume for STT model cache
stt_cache = modal.Volume.from_name("indicconformer-cache", create_if_missing=True)

MINUTES = 60


@app.cls(
    image=image,
    gpu="A10G",
    secrets=[
        modal.Secret.from_name("huggingface-secret"),
        modal.Secret.from_name("Nebius"),
        modal.Secret.from_name("Tavily"),
    ],
    volumes={"/stt-cache": stt_cache},
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
)
class UnifiedVoiceAgent:
    """Unified Voice Agent: STT + Translation + TTS in a single container."""

    @modal.enter()
    def load_all_models(self):
        """Load all models into GPU memory."""
        import os
        import torch
        from huggingface_hub import login
        from transformers import AutoModel, AutoModelForSeq2SeqLM, AutoTokenizer
        from IndicTransToolkit.processor import IndicProcessor

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 Loading all models on {self.device}...")

        # --- STT ---
        os.environ["HF_HOME"] = "/stt-cache/huggingface"
        os.makedirs("/stt-cache/huggingface", exist_ok=True)
        login(token=os.environ["HF_TOKEN"])

        print(f"🔄 Loading STT: {STT_MODEL_ID}...")
        self.stt_model = AutoModel.from_pretrained(STT_MODEL_ID, trust_remote_code=True)
        stt_cache.commit()
        print("✅ STT loaded!")

        # --- Translation Indic-En ---
        print(f"🔄 Loading Translation (Indic->En)...")
        self.trans_indic_en_tokenizer = AutoTokenizer.from_pretrained(
            TRANS_INDIC_EN_DIR, trust_remote_code=True
        )
        self.trans_indic_en_model = AutoModelForSeq2SeqLM.from_pretrained(
            TRANS_INDIC_EN_DIR, trust_remote_code=True, torch_dtype=torch.float16
        ).to(self.device)
        print("✅ Translation (Indic->En) loaded!")

        # --- Translation En-Indic ---
        print(f"🔄 Loading Translation (En->Indic)...")
        self.trans_en_indic_tokenizer = AutoTokenizer.from_pretrained(
            TRANS_EN_INDIC_DIR, trust_remote_code=True
        )
        self.trans_en_indic_model = AutoModelForSeq2SeqLM.from_pretrained(
            TRANS_EN_INDIC_DIR, trust_remote_code=True, torch_dtype=torch.float16
        ).to(self.device)
        print("✅ Translation (En->Indic) loaded!")

        # IndicProcessor for both
        self.indic_processor = IndicProcessor(inference=True)

        # --- TTS ---
        print(f"🔄 Loading TTS: {TTS_MODEL_ID}...")
        self.tts_model = AutoModel.from_pretrained(
            TTS_MODEL_ID,
            trust_remote_code=True,
            device_map=None,
            low_cpu_mem_usage=False,
        ).to(self.device)
        self.tts_ref_path = REF_AUDIO_PATH
        self.tts_ref_text = REF_TEXT_DEFAULT
        print("✅ TTS loaded!")

        print("🎉 All models loaded successfully!")

    def _transcribe(self, audio_bytes: bytes, language: str = "kn") -> str:
        """STT: Audio bytes -> Text."""
        import io
        import torch
        import torchaudio

        try:
            # Load audio using torchaudio (handles format correctly)
            wav, sr = torchaudio.load(io.BytesIO(audio_bytes))
        except Exception as e:
            # Fallback for raw PCM (assuming 16kHz, 16-bit mono)
            print(
                f"⚠️ STT: torchaudio.load failed ({e}), assuming raw PCM 16kHz 16-bit mono"
            )
            import numpy as np

            wav_np = (
                np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )
            wav = torch.from_numpy(wav_np).unsqueeze(0)
            sr = 16000

        # Convert to mono if stereo
        if wav.shape[0] > 1:
            wav = torch.mean(wav, dim=0, keepdim=True)

        # Resample to 16kHz if needed
        if sr != 16000:
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
            wav = resampler(wav)

        transcription = self.stt_model(wav, language, "ctc")
        return transcription

    def _translate_indic_to_en(self, text: str, src_lang: str = "kan_Knda") -> str:
        """Translation: Indic -> English."""
        import torch

        batch = self.indic_processor.preprocess_batch(
            [text], src_lang=src_lang, tgt_lang="eng_Latn"
        )
        inputs = self.trans_indic_en_tokenizer(
            batch,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(self.device)

        with torch.no_grad():
            generated = self.trans_indic_en_model.generate(
                **inputs,
                use_cache=True,
                max_length=256,
                num_beams=1,  # Greedy for speed
            )
        decoded = self.trans_indic_en_tokenizer.batch_decode(
            generated, skip_special_tokens=True
        )
        translations = self.indic_processor.postprocess_batch(decoded, lang="eng_Latn")
        return translations[0]

    def _translate_en_to_indic(self, text: str, tgt_lang: str = "kan_Knda") -> str:
        """Translation: English -> Indic."""
        import torch

        batch = self.indic_processor.preprocess_batch(
            [text], src_lang="eng_Latn", tgt_lang=tgt_lang
        )
        inputs = self.trans_en_indic_tokenizer(
            batch,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(self.device)

        with torch.no_grad():
            generated = self.trans_en_indic_model.generate(
                **inputs,
                use_cache=True,
                max_length=256,
                num_beams=1,  # Greedy for speed
            )
        decoded = self.trans_en_indic_tokenizer.batch_decode(
            generated, skip_special_tokens=True
        )
        translations = self.indic_processor.postprocess_batch(decoded, lang=tgt_lang)
        return translations[0]

    def _synthesize(self, text: str) -> bytes:
        """TTS: Text -> Audio bytes."""
        import io
        import os
        import numpy as np
        import soundfile as sf
        import torch

        import inspect

        if not os.path.exists(self.tts_ref_path):
            raise FileNotFoundError("TTS reference audio not found!")

        # Inspect model signature to determine correct arguments
        sig = inspect.signature(self.tts_model.forward)
        print(f"🔎 TTS Model signature: {sig}")

        kwargs = {}
        if "n_steps" in sig.parameters:
            kwargs["n_steps"] = 32
            print("🚀 Using n_steps=32")
        elif "num_inference_steps" in sig.parameters:
            kwargs["num_inference_steps"] = 32
            print("🚀 Using num_inference_steps=32")

        with torch.no_grad():
            audio_out = self.tts_model(
                text,
                ref_audio_path=self.tts_ref_path,
                ref_text=self.tts_ref_text,
                **kwargs,
            )

        if hasattr(audio_out, "cpu"):
            audio_out = audio_out.cpu().numpy()
        if audio_out.dtype == np.int16:
            audio_out = audio_out.astype(np.float32) / 32768.0

        buffer = io.BytesIO()
        sf.write(buffer, audio_out, 24000, format="WAV")
        buffer.seek(0)
        return buffer.read()

    @modal.web_endpoint(method="POST")
    def process(self, item: dict):
        """
        Full pipeline: Audio In -> STT -> Translate -> [Agent] -> Translate -> TTS -> Audio Out.

        Input:
            {"audio_b64": "base64_encoded_audio", "language": "kn"}
        Output:
            {"transcription": "...", "translated_en": "...", "response_indic": "...", "audio_b64": "..."}
        """
        import base64
        import time
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse

        audio_b64 = item.get("audio_b64")
        language = item.get("language", "kn")
        src_lang_flores = item.get("src_lang", "kan_Knda")
        tgt_lang_flores = item.get("tgt_lang", "kan_Knda")

        if not audio_b64:
            raise HTTPException(status_code=400, detail="audio_b64 is required")

        timings = {}

        # 1. STT
        t0 = time.perf_counter()
        audio_bytes = base64.b64decode(audio_b64)
        transcription = self._transcribe(audio_bytes, language)
        print(f"📝 STT: {transcription}")
        timings["stt_ms"] = int((time.perf_counter() - t0) * 1000)

        # 2. Translate Indic -> English
        t0 = time.perf_counter()
        translated_en = self._translate_indic_to_en(transcription, src_lang_flores)
        print(f"🔄 Translate (In): {translated_en}")
        timings["translate_in_ms"] = int((time.perf_counter() - t0) * 1000)

        # 3. Agent
        # Import lazily to ensure secrets are available and avoid local import errors
        try:
            sys.path.append("/root")
            from src.voice_agent.agent import run_agent_sync

            print(f"🤖 Querying Agent with: {translated_en}")
            agent_response_en = run_agent_sync(translated_en)
            print(f"🤖 Agent Response: {agent_response_en}")
        except Exception as e:
            print(f"❌ Agent failed: {e}")
            agent_response_en = "I'm sorry, I'm having trouble thinking right now."

        # 4. Translate English -> Indic
        t0 = time.perf_counter()
        response_indic = self._translate_en_to_indic(agent_response_en, tgt_lang_flores)
        print(f"🔄 Translate (Out): {response_indic}")
        timings["translate_out_ms"] = int((time.perf_counter() - t0) * 1000)

        # 5. TTS
        t0 = time.perf_counter()
        audio_out_bytes = self._synthesize(response_indic)
        audio_out_b64 = base64.b64encode(audio_out_bytes).decode("utf-8")
        timings["tts_ms"] = int((time.perf_counter() - t0) * 1000)

        timings["total_ms"] = sum(timings.values())

        return JSONResponse(
            content={
                "transcription": transcription,
                "translated_en": translated_en,
                "agent_response_en": agent_response_en,
                "response_indic": response_indic,
                "audio_b64": audio_out_b64,
                "timings": timings,
            }
        )

    @modal.web_endpoint(method="GET")
    def health(self):
        """Health check."""
        return {
            "status": "healthy",
            "models": ["stt", "trans_indic_en", "trans_en_indic", "tts"],
        }


@app.local_entrypoint()
def main():
    print("🚀 Unified Voice Agent deployed!")
    print("📍 Endpoints: /health, /process")
