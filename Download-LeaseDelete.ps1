# Install lease delete files into the current LeaseAI folder.
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/add-lease-delete-2408"
Write-Host "Downloading lease delete files..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "$base/lease_delete.py" -OutFile "lease_delete.py"
Invoke-WebRequest -Uri "$base/Home.py" -OutFile "Home.py"
python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/add-lease-delete-2408/pages/2_%F0%9F%93%8B_Lease_Review.py', r'pages/2_\U0001f4cb_Lease_Review.py')"
Write-Host "Done. Restart with: streamlit run Home.py --server.enableCORS=true --server.headless=false --server.address=localhost" -ForegroundColor Green
Write-Host "Then open Lease Review. Delete leases is at the top of the dashboard." -ForegroundColor Yellow
