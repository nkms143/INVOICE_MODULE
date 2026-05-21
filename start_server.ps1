$VenvPath = Join-Path $PSScriptRoot ".venv\Scripts"
if (Test-Path "$VenvPath\python.exe") {
    if (-not (Test-Path "$VenvPath\python3.exe")) {
        Copy-Item "$VenvPath\python.exe" "$VenvPath\python3.exe" -Force
    }
    $env:PATH = "$VenvPath;" + $env:PATH
}
npx vercel dev
