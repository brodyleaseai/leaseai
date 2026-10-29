# Install per-lease annual escalation extraction for PDF reports.
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-escalation-per-lease-2408"
Write-Host "Downloading per-lease escalation files..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "$base/lease_field_recovery.py" -OutFile "lease_field_recovery.py"
Invoke-WebRequest -Uri "$base/extraction_pipeline.py" -OutFile "extraction_pipeline.py"
Invoke-WebRequest -Uri "$base/lease_report.py" -OutFile "lease_report.py"
Write-Host "Done." -ForegroundColor Green
Write-Host "Restart: streamlit run Home.py"
Write-Host "Re-process a lease to refresh Annual Escalation Rate or Cap from that lease only."
