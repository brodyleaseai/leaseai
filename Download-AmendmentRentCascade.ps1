$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-amendment-rent-cascade-2408"

Invoke-WebRequest -Uri "$base/amendment_clause_links.py" -OutFile "amendment_clause_links.py"
Invoke-WebRequest -Uri "$base/amendment_report.py" -OutFile "amendment_report.py"
Invoke-WebRequest -Uri "$base/amendment_processor_v2.py" -OutFile "amendment_processor_v2.py"
New-Item -ItemType Directory -Force -Path "pages" | Out-Null
Invoke-WebRequest -Uri "$base/pages/3_%F0%9F%94%97_Amendment_Graph.py" -OutFile "pages/3_🔗_Amendment_Graph.py"

Write-Host "Restart Streamlit, then regenerate the Amendment Resolution Abstract. Re-process the Third Amendment to store Order of Precedence."
