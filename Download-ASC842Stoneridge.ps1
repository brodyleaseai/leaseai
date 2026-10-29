# Install Stonebridge / phased-commencement ASC 842 calculator files.
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-asc842-stoneridge-2408"
Write-Host "Downloading ASC 842 Stonebridge fix..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "pages" -Force | Out-Null
Invoke-WebRequest -Uri "$base/asc842_params.py" -OutFile "asc842_params.py"
Invoke-WebRequest -Uri "$base/asc842_engine.py" -OutFile "asc842_engine.py"
$existing = Get-ChildItem -Path "pages" -Filter "*ASC842_Dashboard.py" -ErrorAction SilentlyContinue | Select-Object -First 1
$pageUrl = "$base/pages/5_%F0%9F%93%88_ASC842_Dashboard.py"
if ($existing) {
    Invoke-WebRequest -Uri $pageUrl -OutFile $existing.FullName
} else {
    Invoke-WebRequest -Uri $pageUrl -OutFile "pages/5_ASC842_Dashboard.py"
}
Write-Host "Done." -ForegroundColor Green
Write-Host "Restart: streamlit run Home.py"
Write-Host "Select the Stoneridge / Workday lease. Commencement should be November 1, 2008 (Phase I)."
