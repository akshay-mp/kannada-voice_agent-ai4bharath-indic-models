Write-Host "🚀 Deploying Unified Voice Agent (Backend)..."
modal deploy src/modal/modal_unified.py

Write-Host "`n🚀 Deploying Voice Agent App (Frontend)..."
modal deploy src/modal/modal_app.py

Write-Host "`n✅ Full stack deployment complete!"
Write-Host "Please use the URL from the 'Voice Agent App' deployment to access the UI."
