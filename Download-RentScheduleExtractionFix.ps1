$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-rent-schedule-extraction-2408"

Invoke-WebRequest -Uri "$base/extraction_enrichment.py" -OutFile "extraction_enrichment.py"
Invoke-WebRequest -Uri "$base/extraction_pipeline.py" -OutFile "extraction_pipeline.py"
Invoke-WebRequest -Uri "$base/lease_report.py" -OutFile "lease_report.py"
New-Item -ItemType Directory -Force -Path "pages" | Out-Null
Invoke-WebRequest -Uri "$base/pages/2_%F0%9F%93%8B_Lease_Review.py" -OutFile "pages/2_📋_Lease_Review.py"

Write-Host "Restart Streamlit. Open the Northshore lease, click Generate PDF Report. Re-extract is optional."
