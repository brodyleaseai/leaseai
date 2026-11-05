$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/add-asc842-amendment-remeasure-2408"

function Save-RepoFile([string]$RelPath) {
    $uri = "$base/$RelPath"
    $out = [System.Uri]::UnescapeDataString($RelPath)
    $dir = Split-Path -Parent $out
    if ($dir) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    Invoke-WebRequest -Uri $uri -OutFile $out -UseBasicParsing
    Write-Host "Saved $out"
}

Save-RepoFile "report_sources.py"
Save-RepoFile "lease_report.py"
Save-RepoFile "amendment_report.py"
Save-RepoFile "amendment_clause_links.py"
Save-RepoFile "amendment_processor_v2.py"
Save-RepoFile "extraction_pipeline.py"
Save-RepoFile "client_portal_enhanced.py"
Save-RepoFile "asc842_amendment.py"
Save-RepoFile "asc842_dashboard.py"
Save-RepoFile "pages/2_%F0%9F%93%8B_Lease_Review.py"
Save-RepoFile "pages/3_%F0%9F%94%97_Amendment_Graph.py"
Save-RepoFile "pages/5_%F0%9F%93%88_ASC842_Dashboard.py"

Write-Host "Restart Streamlit. Reports now cite the source document text."
