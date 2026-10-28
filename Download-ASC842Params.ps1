# Install ASC 842 lease-parameter files into the current LeaseAI folder.
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-asc842-lease-params-2408"
Write-Host "Downloading ASC 842 lease parameter files..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "pages" -Force | Out-Null
Invoke-WebRequest -Uri "$base/asc842_params.py" -OutFile "asc842_params.py"
$dashboardUrl = "$base/pages/5_%F0%9F%93%88_ASC842_Dashboard.py"
$existing = Get-ChildItem -Path "pages" -Filter "*ASC842_Dashboard.py" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existing) {
    Invoke-WebRequest -Uri $dashboardUrl -OutFile $existing.FullName
} else {
    Invoke-WebRequest -Uri $dashboardUrl -OutFile "pages/5_ASC842_Dashboard.py"
}
Write-Host "Done." -ForegroundColor Green
Write-Host "Restart: streamlit run Home.py"
Write-Host "Open ASC 842, pick a lease, and confirm commencement, end date, and monthly rent match that lease before calculating."
