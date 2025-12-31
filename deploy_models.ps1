Write-Host "🚀 Deploying All Voice Agent Models to Modal..."

Write-Host "1️⃣ Deploying IndicConformer STT..."
modal deploy src/modal/modal_indicconformer.py

Write-Host "2️⃣ Deploying IndicTrans2 (Indic -> English)..."
modal deploy src/modal/modal_indictrans2.py

Write-Host "3️⃣ Deploying IndicTrans2 (English -> Indic)..."
modal deploy src/modal/modal_indictrans2_en_indic.py

Write-Host "4️⃣ Deploying IndicF5 TTS..."
modal deploy src/modal/modal_indicf5.py

Write-Host "✅ All models deployed successfully!"
