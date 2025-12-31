Write-Host " Cold Starting Models (This may take a few minutes if they are scaling up)..."

Write-Host "1️ Warming up IndicConformer STT..."
uv run python src/test_indicconformer.py

Write-Host "2️ Warming up IndicTrans2 (Indic -> English)..."
uv run python src/test_indictrans2.py

Write-Host "3️ Warming up IndicTrans2 (English -> Indic)..."
uv run python src/test_indictrans2_en_indic.py

Write-Host "4️ Warming up IndicF5 TTS..."
uv run python src/test_indicf5.py

Write-Host " All models checked and warmed up!"
