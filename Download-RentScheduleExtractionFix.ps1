$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-rent-schedule-extraction-2408"

Invoke-WebRequest -Uri "$base/extraction_enrichment.py" -OutFile "extraction_enrichment.py"
Invoke-WebRequest -Uri "$base/extraction_pipeline.py" -OutFile "extraction_pipeline.py"

Write-Host "Restart Streamlit, then re-process the original 3-page Northshore lease."
