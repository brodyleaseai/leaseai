# Install lease-term recovery files into the current LeaseAI folder.
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-are-lease-extraction-2408"
Write-Host "Downloading lease extraction accuracy files..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "$base/lease_field_recovery.py" -OutFile "lease_field_recovery.py"
Invoke-WebRequest -Uri "$base/extraction_pipeline.py" -OutFile "extraction_pipeline.py"
Invoke-WebRequest -Uri "$base/lease_report.py" -OutFile "lease_report.py"
Write-Host "Done." -ForegroundColor Green
Write-Host "Restart: streamlit run Home.py"
Write-Host "Delete the ARE lease and upload ARE LLC_lease.pdf again so the abstract is rebuilt."
