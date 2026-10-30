# Install Dixie / PSF monthly-rent calculator fix.
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-dixie-monthly-rent-2408"
Write-Host "Downloading Dixie monthly rent fix..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "$base/lease_field_recovery.py" -OutFile "lease_field_recovery.py"
Invoke-WebRequest -Uri "$base/extraction_pipeline.py" -OutFile "extraction_pipeline.py"
Invoke-WebRequest -Uri "$base/lease_report.py" -OutFile "lease_report.py"
Write-Host "Done." -ForegroundColor Green
Write-Host "Restart: streamlit run Home.py"
Write-Host "Re-process the Dixie Development lease. Base Rent Year 1 should be `$8,550.08."
