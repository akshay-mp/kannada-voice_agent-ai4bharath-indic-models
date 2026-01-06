# Component View (Code Structure)

This document outlines the organization of the codebase and the responsibilities of each directory.

## Directory Structure

### `src/voice_agent/` - Local Orchestrator
This directory contains the core logic for the local Python application that orchestrates the voice pipeline.
- **Responsibilities**:
    - WebSocket management for real-time audio streaming.
    - VAD (Voice Activity Detection) processing.
    - Handling connections to Modal microservices (STT, Translation, TTS).
    - Managing the conversation state and agent interaction.
- **Key Files**:
    - `main.py`: Entry point for the FastAPI server and WebSocket endpoint.

### `src/modal/` - Artificial Intelligence Microservices
This directory defines the Modal applications for the AI models. These are deployed as serverless functions.
- **Responsibilities**:
    - Hosting large AI models on GPU infrastructure.
    - Providing endpoints for other components to access these models.
- **Key Files**:
    - `modal_indicconformer.py`: Speech-to-Text service using AI4Bharat's IndicConformer.
    - `modal_indictrans2.py`: Translation service (Indic -> English).
    - `modal_indictrans2_en_indic.py`: Translation service (English -> Indic).
    - `modal_indicf5.py`: Text-to-Speech service using IndicF5.

### `src/web/` - Frontend Application
This directory contains the user interface code.
- **Responsibilities**:
    - Capturing microphone input from the user.
    - Streaming audio to the backend.
    - Playing back audio responses.
    - Displaying conversation status or transcripts.
- **Tech Stack**:
    - Svelte, Vite, TypeScript.
