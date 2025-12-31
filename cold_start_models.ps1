Write-Host " Cold Starting Models (This may take a few minutes if they are scaling up)..."

$models = @(
    @{ Name = "IndicConformer STT"; Path = "src/modal/test_indicconformer.py" },
    @{ Name = "IndicTrans2 (Indic -> English)"; Path = "src/modal/test_indictrans2.py" },
    @{ Name = "IndicTrans2 (English -> Indic)"; Path = "src/modal/test_indictrans2_en_indic.py" },
    @{ Name = "IndicF5 TTS"; Path = "src/modal/test_indicf5.py" }
)

$jobs = @()

$models | ForEach-Object {
    $model = $_
    Write-Host "🚀 Starting warmup for $($model.Name)..."
    $jobs += Start-Job -ScriptBlock {
        param($name, $path)
        Write-Output "⏳ Warming up $name..."
        uv run python $path
        Write-Output "✅ $name warmed up!"
    } -ArgumentList $model.Name, $model.Path
}

Write-Host "Waiting for all models to warm up..."
$jobs | Wait-Job | Receive-Job


Write-Host " All models checked and warmed up!"
