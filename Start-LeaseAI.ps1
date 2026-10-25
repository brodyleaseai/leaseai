# Launch LeaseAI locally and open the browser.
# Run from the LeaseAI folder:  .\Start-LeaseAI.ps1

Set-Location $PSScriptRoot
Write-Host "Starting LeaseAI..." -ForegroundColor Cyan
Write-Host "If the browser does not open, go to http://127.0.0.1:8501" -ForegroundColor Yellow

Start-Job -Name LeaseAIOpenBrowser -ScriptBlock {
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8501/_stcore/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) {
                Start-Process "http://127.0.0.1:8501"
                return
            }
        } catch {
            continue
        }
    }
} | Out-Null

streamlit run Home.py
