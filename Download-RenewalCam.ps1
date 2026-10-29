# Install renewal-option dates in the PDF critical-dates table and CAM key fallback.
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-renewal-cam-secrets-2408"
Write-Host "Downloading renewal dates and CAM secret-fallback files..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "pages" -Force | Out-Null
Invoke-WebRequest -Uri "$base/critical_date_extract.py" -OutFile "critical_date_extract.py"
Invoke-WebRequest -Uri "$base/lease_report.py" -OutFile "lease_report.py"
Invoke-WebRequest -Uri "$base/openai_key.py" -OutFile "openai_key.py"
Invoke-WebRequest -Uri "$base/cam_gpt_extractor.py" -OutFile "cam_gpt_extractor.py"
$cam = Get-ChildItem -Path "pages" -Filter "*CAM_Reconciliation.py" -ErrorAction SilentlyContinue | Select-Object -First 1
$camUrl = "$base/pages/10_%F0%9F%92%B5_CAM_Reconciliation.py"
if ($cam) {
    Invoke-WebRequest -Uri $camUrl -OutFile $cam.FullName
} else {
    Invoke-WebRequest -Uri $camUrl -OutFile "pages/10_CAM_Reconciliation.py"
}
$health = Get-ChildItem -Path "pages" -Filter "*Portfolio_Health.py" -ErrorAction SilentlyContinue | Select-Object -First 1
$healthUrl = "$base/pages/11_%F0%9F%8F%A5_Portfolio_Health.py"
if ($health) {
    Invoke-WebRequest -Uri $healthUrl -OutFile $health.FullName
} else {
    Invoke-WebRequest -Uri $healthUrl -OutFile "pages/11_Portfolio_Health.py"
}
Write-Host "Done." -ForegroundColor Green
Write-Host "Restart: streamlit run Home.py"
Write-Host "Regenerate the Workday PDF to see renewal notice dates. CAM Extract now uses the same OPENAI_API_KEY as lease upload."
