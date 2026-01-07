---
description: How to Create and Deploy the Voice Agent on Modal
---

# Deploying the Voice Agent on Modal

This workflow describes the complete process of creating and deploying the Unified Voice Agent on Modal.

## Prerequisites

1.  **Modal Account**: Sign up at [modal.com](https://modal.com).
2.  **Modal Settings**: Install the client and authenticate.
    ```powershell
    pip install modal
    modal setup
    ```
3.  **Secrets**: Ensure you have created the following secrets in your Modal dashboard:
    *   `huggingface-secret` (Key: `HF_TOKEN`)
    *   `Nebius` (Key: `NEBIUS_API_KEY`)
    *   `Tavily` (Key: `TAVILY_API_KEY`)

## 1. Deploy the Backend (Unified Processor)

The backend handles STT, Translation, Agent Logic, and TTS on a GPU.

**File**: `src/modal/modal_unified.py`

**Deploy Command**:
```powershell
modal deploy src/modal/modal_unified.py
```
*Note the URL of the `process` endpoint from the output (e.g., `https://...-process.modal.run`).*

## 2. Deploy the Frontend (WebSocket Server)

The frontend serves the Web UI and manages the WebSocket connection.

**File**: `src/modal/modal_app.py`

**Deploy Command**:
```powershell
modal deploy src/modal/modal_app.py
```
*Use the output URL labeled `VoiceAgentApp.web` to access the UI.*

## 3. Automated Deployment (Full Stack)

To deploy both services in the correct order, we have provided a script:

```powershell
.\deploy_full_stack.ps1
```

## Troubleshooting

### 500 Internal Server Error
If you see `500` errors when speaking:
1.  Go to the [Modal Dashboard](https://modal.com/apps).
2.  Click on the `unified-voice-agent` app.
3.  Check the **Logs** tab.
4.  Look for Python exceptions (e.g., `ImportError`, `OutOfMemoryError`, or API key issues).

### App Stopped
If you see a "stopped" error:
*   Redeploy the backend service (`step 1` or `deploy_full_stack.ps1`). Modal apps stop if deployed ephemerally (`modal serve`), so always use `modal deploy` for persistence.
