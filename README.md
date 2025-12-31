# Kannada Voice Agent (Generic)

A "Voice Sandwich" architecture for a Kannada Generic Voice Agent. This pipeline integrates Voice Activity Detection (VAD), Speech-to-Text (STT), Translation (Indic↔English), LLM Agent (Qwen), and Text-to-Speech (TTS).

## 💡 Motivation: Why this was created

I tested several models and chat apps for Kannada and was not satisfied with either the pronunciation or translation quality. This led to the creation of an agent using **Indic Models**, which are specifically curated for the 22 languages of India.

> **Note**: This pipeline is designed to be easily adaptable for all 22 official Indian languages with minor configuration changes. I encourage you to try adapting it for your own language!

## 🏗️ Architecture

The pipeline follows a **Voice Sandwich** pattern:

1.  **VAD (Silero)**: Detects voice activity in the audio stream.
2.  **STT (IndicConformer)**: Transcribes Kannada audio to Kannada text.
3.  **Translation (IndicTrans2)**: Translates Kannada text to English.
4.  **Agent (QWEN + Tavily)**: Processes the English query using QWEN Model from NEBIUS, augmented with **Tavily Search** for real-time information, and generates an English response.
5.  **Translation (IndicTrans2)**: Translates the English response back to Kannada.
6.  **TTS (IndicF5)**: Synthesizes Kannada audio from the translated text.

### Microservices (Modal)
The heavy lifting (AI Models) is hosted on [Modal](https://modal.com/) as serverless microservices:
- **STT**: `src/modal/modal_indicconformer.py` (AI4Bharat IndicConformer)
- **Translation**:
    - `src/modal/modal_indictrans2.py` (Indic → English)
    - `src/modal/modal_indictrans2_en_indic.py` (English → Indic)
- **TTS**: `src/modal/modal_indicf5.py` (IndicF5)

## �️ Modal Skills (Pre-configured)
This repository includes a `skills/` directory containing **standalone, reusable skills** for deploying each model to Modal. These can be used as references or starting points for isolated deployments:
- `skills/modal-indicconformer-stt/`
- `skills/modal-indictrans2-translation/`
- `skills/modal-indictrans2-en-indic-translation/`
- `skills/modal-indicf5-tts/`

## �🚀 Deployment

### Prerequisites
- [Modal](https://modal.com/) account and CLI installed (`pip install modal`).
- [uv](https://github.com/astral-sh/uv) (recommended) or Python 3.10+.
- `.env` file with:
    - `NEBIUS_API_KEY` (for Qwen)
    - `TAVILY_API_KEY` (for Search capabilities)

### Deploy Models to Modal
Run the deployment script to deploy all microservices:
```powershell
./deploy_models.ps1
```
Or deploy individually:
```bash
modal deploy src/modal/modal_indicconformer.py
modal deploy src/modal/modal_indicf5.py
modal deploy src/modal/modal_indictrans2.py
modal deploy src/modal/modal_indictrans2_en_indic.py
```

### Cold Start (Warmup)
To ensure low latency, warm up the serverless containers before use:
```powershell
./cold_start_models.ps1
```

## 🏃 Running the Voice Agent

### 1. Install Dependencies
```bash
uv pip install -r requirements.txt
```

### 2. Start the Server
Run the local voice agent server (FastAPI + WebSocket):
```bash
uv run python -m src.voice_agent.main
```
The server will start at `http://localhost:8000` (or similar).

### 3. Client Interaction
The agent exposes a WebSocket endpoint (typically `/ws`) for real-time audio streaming.
- **Frontend**: A Svelte/Vite frontend (in `src/web`) connects to this WebSocket to capture microphone input and play back response audio.

## 📂 Project Structure
- `src/voice_agent/`: Core logic for the local agent (Pipeline, VAD, Client logic).
- `src/modal/`: Modal microservice definitions for the AI models.
- `src/web/`: Frontend application.
