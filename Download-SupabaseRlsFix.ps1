# Download the Supabase RLS fix. Run from your LeaseAI folder, then open
# database_security_enable_rls_all_public.sql and run it in the Supabase SQL Editor.

Write-Host "Downloading Supabase RLS lock-down script..." -ForegroundColor Cyan
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-supabase-rls-2408"
Invoke-WebRequest -Uri "$base/database_security_enable_rls_all_public.sql" -OutFile "database_security_enable_rls_all_public.sql"
Write-Host "Saved database_security_enable_rls_all_public.sql" -ForegroundColor Green
Write-Host "Next: Supabase → SQL Editor → paste that file → Run" -ForegroundColor Yellow
