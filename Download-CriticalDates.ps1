# Install critical-dates lease selection and PDF table files.
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/add-critical-dates-lease-select-2408"
Write-Host "Downloading critical dates files..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "pages" -Force | Out-Null
Invoke-WebRequest -Uri "$base/critical_date_extract.py" -OutFile "critical_date_extract.py"
Invoke-WebRequest -Uri "$base/lease_report.py" -OutFile "lease_report.py"
Invoke-WebRequest -Uri "$base/extraction_pipeline.py" -OutFile "extraction_pipeline.py"
$existing = Get-ChildItem -Path "pages" -Filter "*Critical_Dates.py" -ErrorAction SilentlyContinue | Select-Object -First 1
$pageUrl = "$base/pages/6_%F0%9F%93%85_Critical_Dates.py"
if ($existing) {
    Invoke-WebRequest -Uri $pageUrl -OutFile $existing.FullName
} else {
    Invoke-WebRequest -Uri $pageUrl -OutFile "pages/6_Critical_Dates.py"
}
Write-Host "Done." -ForegroundColor Green
Write-Host "Restart: streamlit run Home.py"
Write-Host "Open Critical Dates, select a lease, and confirm commencement / expiration / notice dates. Generate PDF Report to see the Critical Dates table."
