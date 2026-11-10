$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/add-current-lease-position-2408"

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

Save-RepoFile "current_lease_position.py"
Save-RepoFile "email_delivery.py"
Save-RepoFile "pages/3_%F0%9F%94%97_Amendment_Graph.py"

Write-Host "Restart Streamlit. Amendment Resolution Graph now has a Current Position tab and PDF."
