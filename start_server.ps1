$Python312Path = Join-Path $env:USERPROFILE "AppData\Local\Programs\Python\Python312"
if (Test-Path "$Python312Path\python.exe") {
    if (-not (Test-Path "$Python312Path\python3.exe")) {
        Copy-Item "$Python312Path\python.exe" "$Python312Path\python3.exe" -Force
    }
    $env:PATH = "$Python312Path;" + $env:PATH
}
npx vercel dev

