$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/add-asc842-amendment-remeasure-2408"

Invoke-WebRequest -Uri "$base/report_sources.py" -OutFile "report_sources.py"
Invoke-WebRequest -Uri "$base/lease_report.py" -OutFile "lease_report.py"
Invoke-WebRequest -Uri "$base/amendment_report.py" -OutFile "amendment_report.py"
Invoke-WebRequest -Uri "$base/amendment_clause_links.py" -OutFile "amendment_clause_links.py"
Invoke-WebRequest -Uri "$base/amendment_processor_v2.py" -OutFile "amendment_processor_v2.py"
Invoke-WebRequest -Uri "$base/extraction_pipeline.py" -OutFile "extraction_pipeline.py"
Invoke-WebRequest -Uri "$base/client_portal_enhanced.py" -OutFile "client_portal_enhanced.py"
Invoke-WebRequest -Uri "$base/asc842_amendment.py" -OutFile "asc842_amendment.py"
Invoke-WebRequest -Uri "$base/asc842_dashboard.py" -OutFile "asc842_dashboard.py"
New-Item -ItemType Directory -Force -Path "pages" | Out-Null
Invoke-WebRequest -Uri "$base/pages/2_%F0%9F%93%8B_Lease_Review.py" -OutFile "pages/2_📋_Lease_Review.py"
Invoke-WebRequest -Uri "$base/pages/3_%F0%9F%94%97_Amendment_Graph.py" -OutFile "pages/3_🔗_Amendment_Graph.py"
Invoke-WebRequest -Uri "$base/pages/5_%F0%9F%93%88_ASC842_Dashboard.py" -OutFile "pages/5_📈_ASC842_Dashboard.py"

Write-Host "Restart Streamlit. Lease abstracts, Amendment Resolution Abstracts, and ASC 842 as-amended previews now cite the source document text."
