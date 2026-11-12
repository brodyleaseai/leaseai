$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/add-lease-term-facts-2408"

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

Save-RepoFile "lease_term_facts.py"
Save-RepoFile "database_schema_lease_term_facts.sql"
Save-RepoFile "extraction_pipeline.py"
Save-RepoFile "pipeline.py"
Save-RepoFile "app.py"
Save-RepoFile "admin_dashboard.py"
Save-RepoFile "client_portal_enhanced.py"
Save-RepoFile "pages/2_%F0%9F%93%8B_Lease_Review.py"
Save-RepoFile "pages/4_%F0%9F%93%8A_Admin_Dashboard.py"
Save-RepoFile "pages/14_%E2%9A%99%EF%B8%8F_User_Settings.py"
Save-RepoFile "docs/Master_Services_Agreement_MSA.md"
Save-RepoFile "docs/Data_Processing_Agreement_DPA.md"
Save-RepoFile "amendment_processor.py"
Save-RepoFile "amendment_processor_v2.py"

Write-Host "Run database_schema_lease_term_facts.sql in the Supabase SQL Editor, then restart Streamlit."
Write-Host "Processed leases then write de-identified term facts. Opt in under User Settings."
