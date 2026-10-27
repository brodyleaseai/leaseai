# Install lease delete files into the current LeaseAI folder.
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/add-lease-delete-2408"
Write-Host "Downloading lease delete files..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "pages" -Force | Out-Null
Invoke-WebRequest -Uri "$base/lease_delete.py" -OutFile "lease_delete.py"
Invoke-WebRequest -Uri "$base/Home.py" -OutFile "Home.py"
Invoke-WebRequest -Uri "$base/pages/16_Delete_Leases.py" -OutFile "pages/16_Delete_Leases.py"
Write-Host "Done." -ForegroundColor Green
Write-Host "Restart: streamlit run Home.py --server.enableCORS=true --server.headless=false --server.address=localhost"
Write-Host "After login, click Delete Leases or open Delete Leases in the sidebar."
