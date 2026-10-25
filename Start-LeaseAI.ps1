# Launch LeaseAI and force the safe Streamlit flags.
# Run:  powershell -ExecutionPolicy Bypass -File .\Start-LeaseAI.ps1

Set-Location $PSScriptRoot
Write-Host "Starting LeaseAI at http://localhost:8501" -ForegroundColor Cyan
Start-Process "http://localhost:8501"
streamlit run Home.py --server.enableCORS=true --server.headless=false --server.address=localhost --server.port=8501
