"""
Modal deployment for Voice Agent WebSocket Server.
Serves the FastAPI WebSocket app + static frontend on Modal.

Deploy:
    modal deploy src/modal/modal_app.py

This connects to the unified voice agent endpoint for processing.
"""

import modal

app = modal.App("voice-agent-app")

# URL of the unified voice agent endpoint
UNIFIED_ENDPOINT = (
    "https://akshaymp-1810--unified-voice-agent-unifiedvoiceagent-process.modal.run"
)


def download_vad():
    """Download Silero VAD model to cache."""
    import torch

    print("📥 Downloading Silero VAD...")
    torch.hub.set_dir("/root/.cache/torch")
    torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=True,
        trust_repo=True,
    )
    print("✅ Silero VAD downloaded")


# Image with dependencies for the WebSocket server
image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "fastapi[standard]",
        "uvicorn",
        "httpx",
        "python-dotenv",
        # VAD dependencies
        "torch",
        "torchaudio",
        "numpy",
        "onnxruntime",
    )
    .run_function(download_vad)
    .add_local_dir("src/voice_agent", remote_path="/root/src/voice_agent")
    .add_local_dir("src/web/dist", remote_path="/root/src/web/dist")
)

MINUTES = 60


@app.cls(
    image=image,
    secrets=[
        modal.Secret.from_name("Nebius"),
        modal.Secret.from_name("Tavily"),
    ],
    timeout=10 * MINUTES,
    scaledown_window=10 * MINUTES,
    allow_concurrent_inputs=100,
)
class VoiceAgentApp:
    """Voice Agent WebSocket Server on Modal."""

    @modal.enter()
    def setup(self):
        """Setup paths for imports."""
        import sys

        sys.path.insert(0, "/root")
        print("🚀 Voice Agent App ready!")

    @modal.asgi_app()
    def web(self):
        """Return the FastAPI app for ASGI hosting."""
        import os

        os.environ["UNIFIED_ENDPOINT"] = UNIFIED_ENDPOINT

        from src.voice_agent.modal_server import app as fastapi_app

        return fastapi_app


@app.local_entrypoint()
def main():
    print("🚀 Voice Agent App deployed!")
    print("📍 Access via the Modal-generated URL")
