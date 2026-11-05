$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-amendment-rent-cascade-2408"

Invoke-WebRequest -Uri "$base/amendment_clause_links.py" -OutFile "amendment_clause_links.py"
Invoke-WebRequest -Uri "$base/amendment_report.py" -OutFile "amendment_report.py"
Invoke-WebRequest -Uri "$base/amendment_processor_v2.py" -OutFile "amendment_processor_v2.py"

Write-Host "Restart Streamlit, then regenerate the Amendment Resolution Abstract. Re-processing the Second Amendment is optional."
