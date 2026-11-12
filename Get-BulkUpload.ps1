$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-bulk-upload-2408"

function Save-RepoFile([string]$RelPath) {
    $uri = "$base/$RelPath"
    $out = [System.Uri]::UnescapeDataString($RelPath)
    $dir = Split-Path -Parent $out
    if ($dir) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    curl.exe -L $uri -o $out
    if ($LASTEXITCODE -ne 0) {
        throw "Download failed: $uri"
    }
    Write-Host "Saved $out"
}

Save-RepoFile "bulk_upload.py"
Save-RepoFile "extraction_timeout.py"
Save-RepoFile "extraction_pipeline.py"
Save-RepoFile "lease_header.py"
Save-RepoFile "lease_report.py"
Save-RepoFile "report_sources.py"
Save-RepoFile "pages/9_%F0%9F%93%A6_Bulk_Upload.py"
Save-RepoFile "pages/2_%F0%9F%93%8B_Lease_Review.py"
Save-RepoFile "client_portal_enhanced.py"

Write-Host "Restart Streamlit, then bulk upload will process every selected PDF one at a time."
Write-Host "Re-process bulk leases so page 1 shows the legal tenant name and the abstract cites lease excerpts."
