$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-asc842-autopopulate-2408"

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

Save-RepoFile "asc842_params.py"
Save-RepoFile "asc842_engine.py"
Save-RepoFile "asc842_dashboard.py"
Save-RepoFile "pages/5_%F0%9F%93%88_ASC842_Dashboard.py"

Write-Host "Restart Streamlit. Selecting a lease on ASC 842 now fills that lease's dates and rent."
