"""
Configuration for Voice Agent Pipeline.
Contains Modal endpoint URLs and language settings.
"""

import os

# Modal Service URLs (deployed endpoints)
MODAL_STT_URL = (
    "https://akshaymp-1810--indicconformer-stt-indicconformerstt-web-app.modal.run"
)
MODAL_TRANS_INDIC_EN_URL = (
    "https://akshaymp-1810--indictrans2-indic-en-indictrans2service-web-app.modal.run"
)
MODAL_TRANS_EN_INDIC_URL = (
    "https://akshaymp-1810--indictrans2-en-indic-indictrans2enindicse-9e3146.modal.run"
)
MODAL_TTS_URL = "https://akshaymp-1810--indicf5-tts-indicf5service-generate.modal.run"

# Language Configuration
LANGUAGE_CODE = "kn"  # Kannada for STT
LANGUAGE_SCRIPT = "kan_Knda"  # For IndicTrans2

# Audio Configuration
SAMPLE_RATE = 16000  # 16kHz for STT
CHUNK_SIZE = 512  # Samples per chunk for VAD (32ms at 16kHz)

# VAD Configuration
VAD_THRESHOLD = 0.5
MIN_SILENCE_DURATION_MS = 1000  # Increased from 500ms to allow natural pauses
MIN_SPEECH_DURATION_MS = 250

# API Timeouts (seconds)
STT_TIMEOUT = 120
TRANSLATION_TIMEOUT = 60
TTS_TIMEOUT = 120

# Google Gemini Configuration
GEMINI_MODEL = "gemini-3-flash-preview"  # Using experimental flash model
