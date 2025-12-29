import os
import modal

# Define the image with vLLM and merging dependencies
image = (
    modal.Image.from_registry("nvidia/cuda:12.1.1-devel-ubuntu22.04", add_python="3.10")
    .pip_install(
        "vllm==0.11.2",
        "huggingface_hub",
        "hf_transfer",
        "transformers",
        "peft",
        "accelerate",
        "bitsandbytes"
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App("ambari-translator-vllm")

# Volume to store the merged model and generic cache
model_vol = modal.Volume.from_name("ambari-vllm-model-cache", create_if_missing=True)

# Path in the volume where the merged model will be stored
MERGED_MODEL_DIR = "/model/ambari-merged"

@app.function(
    image=image,
    gpu="A100",
    volumes={"/model": model_vol},
    timeout=1800, # 30 mins for download/merge
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
def download_and_merge():
    """
    Downloads the base model and LoRA adapter, merges them, and saves to the volume.
    Run this manually once before serving: `modal run src/ambari_modal.py::download_and_merge`
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    if os.path.exists(MERGED_MODEL_DIR) and os.listdir(MERGED_MODEL_DIR):
        print(f"Merged model already exists at {MERGED_MODEL_DIR}. Skipping merge.")
        return

    BASE_MODEL = "Cognitive-Lab/Ambari-7B-Instruct-v0.2"
    ADAPTER_MODEL = "Akshaymp/ambari-7b-lora-dora-v2"

    print(f"Loading base model: {BASE_MODEL}")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    print(f"Loading adapter: {ADAPTER_MODEL}")
    model = PeftModel.from_pretrained(base_model, ADAPTER_MODEL)

    print("Merging adapter into base model...")
    model = model.merge_and_unload()

    print(f"Saving merged model to {MERGED_MODEL_DIR}...")
    model.save_pretrained(MERGED_MODEL_DIR, safe_serialization=True)
    tokenizer.save_pretrained(MERGED_MODEL_DIR)
    
    # Commit volume changes
    model_vol.commit()
    print("Merge complete and saved to volume.")


@app.function(
    image=image,
    gpu="A100",
    volumes={"/model": model_vol},
    scaledown_window=300,
    timeout=600,
)
@modal.concurrent(max_inputs=10)
@modal.web_server(port=8000, startup_timeout=600)
def serve():
    """
    Serves the merged model using vLLM in an OpenAI-compatible server.
    """
    import subprocess
    import sys

    # Check if merged model exists
    if not os.path.exists(MERGED_MODEL_DIR) or not os.listdir(MERGED_MODEL_DIR):
        print(f"ERROR: Merged model not found at {MERGED_MODEL_DIR}. Please run 'modal run src/ambari_modal.py::download_and_merge' first.")
        sys.exit(1)

    cmd = [
        "vllm", "serve", MERGED_MODEL_DIR,
        "--host", "0.0.0.0",
        "--port", "8000",
        "--served-model-name", "ambari-merged",
        "--dtype", "bfloat16",
        "--tensor-parallel-size", "1", # A100 is enough
        "--max-model-len", "4096", # Adjust based on needs
        "--gpu-memory-utilization", "0.90",
        # "--enforce-eager", # Uncomment if CUDA graph capturing fails
    ]

    print("Starting vLLM server:", " ".join(cmd))
    subprocess.Popen(cmd)
