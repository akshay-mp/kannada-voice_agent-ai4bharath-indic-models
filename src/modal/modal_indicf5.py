"""
Modal deployment for IndicF5 (Polyglot TTS) model.
Model: ai4bharat/IndicF5 (Text-to-Speech)
Repo: https://github.com/AI4Bharat/IndicF5

Deploy:
    modal deploy src/modal_indicf5.py
"""

import modal

app = modal.App("indicf5-tts")

# Model configuration
MODEL_ID = "ai4bharat/IndicF5"
MODEL_DIR = "/model"
REF_AUDIO_URL = "https://raw.githubusercontent.com/AI4Bharat/IndicF5/main/prompts/KAN_F_HAPPY_00001.wav"
REF_AUDIO_PATH = "/model/default_ref.wav"
# Transcript for the default reference audio (Kannada)
REF_TEXT_DEFAULT = "ನಮ್‌ ಫ್ರಿಜ್ಜಲ್ಲಿ ಕೂಲಿಂಗ್‌ ಸಮಸ್ಯೆ ಆಗಿ ನಾನ್‌ ಭಾಳ ದಿನದಿಂದ ಒದ್ದಾಡ್ತಿದ್ದೆ, ಆದ್ರೆ ಅದ್ನೀಗ ಮೆಕಾನಿಕ್ ಆಗಿರೋ ನಿಮ್‌ ಸಹಾಯ್ದಿಂದ ಬಗೆಹರಿಸ್ಕೋಬೋದು ಅಂತಾಗಿ ನಿರಾಳ ಆಯ್ತು ನಂಗೆ."

def download_setup():
    """Download model and default reference audio."""
    import os
    import requests
    from huggingface_hub import snapshot_download, login

    # Login
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        login(token=hf_token)

    # Download Model
    print(f"📥 Downloading {MODEL_ID}...")
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False,
    )
    print(f"✅ Model downloaded to {MODEL_DIR}")

    # Download Default Reference Audio
    print(f"📥 Downloading reference audio from {REF_AUDIO_URL}...")
    try:
        response = requests.get(REF_AUDIO_URL, timeout=30)
        response.raise_for_status()
        with open(REF_AUDIO_PATH, "wb") as f:
            f.write(response.content)
        print(f"✅ Reference audio saved to {REF_AUDIO_PATH}")
    except Exception as e:
        print(f"❌ Failed to download reference audio: {e}")
        # Create a dummy file or fail? Better to fail or warn.
        # We will try to proceed, but load_model might fail if it relies on it.
        pass


# Image definition
image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg", "libsndfile1")  # FFmpeg is crucial for audio
    .pip_install(
        "git+https://github.com/AI4Bharat/IndicF5.git",
        "transformers==4.49.0",  # Pinned to fix meta tensor issue with Vocos
        "soundfile",
        "numpy",
        "librosa",
        "torch",
        "torchaudio",
        "torchcodec",  # Required for audio loading
        "huggingface_hub",
        "fastapi[standard]",
        "pydantic",
        "safetensors",  # Required for model loading
    )
    .env({"HF_HOME": "/root/.cache/huggingface"})
    .run_function(
        download_setup,
        secrets=[modal.Secret.from_name("huggingface-secret")],
    )
)

MINUTES = 60

@app.cls(
    image=image,
    gpu="A10G",
    secrets=[modal.Secret.from_name("huggingface-secret")],
    timeout=10 * MINUTES,
    scaledown_window=5 * MINUTES,
)
class IndicF5Service:
    """IndicF5 Text-to-Speech Service."""

    @modal.enter()
    def load_model(self):
        """Load model for inference."""
        import os
        import torch
        from transformers import AutoModel
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔄 Loading IndicF5 from {MODEL_DIR} on {self.device}...")

        # Load model using AutoModel (custom code)
        # NOTE: Must use HuggingFace repo ID, not local path, because custom code
        # calls hf_hub_download with config.name_or_path
        self.model = AutoModel.from_pretrained(
            MODEL_ID,  # Use repo ID, not local path
            trust_remote_code=True,
            # Force full loading to RAM by disabling Accelerate's auto-device logic
            device_map=None,
            low_cpu_mem_usage=False,
        ).to(self.device)
        
        # Pre-load default reference audio logic if needed, 
        # but model takes path as input usually.
        self.default_ref_path = REF_AUDIO_PATH
        self.default_ref_text = REF_TEXT_DEFAULT
        
        if not os.path.exists(self.default_ref_path):
            print("⚠️ Default reference audio not found!")

        print("✅ IndicF5 loaded!")

    @modal.web_endpoint(method="POST")
    def generate(self, item: dict):
        """
        Generate speech.
        Input: {
            "text": "Text to speak",
            "ref_audio": "base64_string" (Optional),
            "ref_text": "Transcript of ref audio" (Optional)
        }
        Output: WAV audio bytes
        """
        import base64
        import tempfile
        import soundfile as sf
        import numpy as np
        import io
        import os
        import torch

        text = item.get("text")
        if not text:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Text is required")

        ref_audio_b64 = item.get("ref_audio")
        ref_text = item.get("ref_text")

        # Determine reference inputs
        temp_ref_file = None
        
        if ref_audio_b64:
            # User provided custom reference
            if not ref_text:
                 from fastapi import HTTPException
                 raise HTTPException(status_code=400, detail="ref_text is required when providing ref_audio")
            
            try:
                audio_bytes = base64.b64decode(ref_audio_b64)
                # Create temp file
                fd, temp_ref_path = tempfile.mkstemp(suffix=".wav")
                os.write(fd, audio_bytes)
                os.close(fd)
                
                res_ref_path = temp_ref_path
                res_ref_text = ref_text
                temp_ref_file = temp_ref_path  # Mark for cleanup
            except Exception as e:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=f"Invalid ref_audio: {e}")
        else:
            # Use default
            res_ref_path = self.default_ref_path
            res_ref_text = self.default_ref_text
            if not os.path.exists(res_ref_path):
                 from fastapi import HTTPException
                 raise HTTPException(status_code=500, detail="Default reference audio missing on server")

        print(f"🗣 Generating TTS for: '{text}' using ref: {res_ref_path}")

        try:
            # Generate speech
            # Model signature: (text, ref_audio_path, ref_text)
            # Note: The model forward might return raw audio array.
            
            # Since custom code, assuming it adheres to README usage:
            # audio = model(text, ref_audio_path=..., ref_text=...)
            
            import inspect
            sig = inspect.signature(self.model.forward)
            print(f"🔎 Model signature: {sig}")
            
            # Try to use n_steps if available in signature
            kwargs = {}
            if "n_steps" in sig.parameters:
                kwargs["n_steps"] = item.get("n_steps", 16) # Default to 16 for speed?
                print(f"🚀 Using n_steps={kwargs['n_steps']}")
            elif "num_inference_steps" in sig.parameters:
                kwargs["num_inference_steps"] = item.get("n_steps", 16)
                print(f"🚀 Using num_inference_steps={kwargs['num_inference_steps']}")
                
            with torch.no_grad():
                audio_out = self.model(
                    text,
                    ref_audio_path=res_ref_path,
                    ref_text=res_ref_text,
                    **kwargs
                )

            # Convert to numpy and save to bytes
            # README says: if audio.dtype == np.int16 ... conversion logic
            
            if hasattr(audio_out, "cpu"):
                audio_out = audio_out.cpu().numpy()
            
            if isinstance(audio_out, tuple):
                 # Some models return (sample_rate, audio) or similar using Pipeline?
                 # Custom AutoModel usually returns the output of forward().
                 # Based on README: audio = model(...) returns the array directly.
                 pass

            # Conversion logic from README
            if audio_out.dtype == np.int16:
                audio_out = audio_out.astype(np.float32) / 32768.0
            
            # Write to BytesIO
            buffer = io.BytesIO()
            sf.write(buffer, audio_out, 24000, format='WAV')
            buffer.seek(0)
            wav_bytes = buffer.read()

            # Return as proper binary response
            from fastapi.responses import Response
            return Response(content=wav_bytes, media_type="audio/wav")

        except Exception as e:
            import traceback
            traceback.print_exc()
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Cleanup temp file
            if temp_ref_file and os.path.exists(temp_ref_file):
                os.remove(temp_ref_file)


@app.local_entrypoint()
def main():
    print("🚀 IndicF5 TTS Service deployed!")
