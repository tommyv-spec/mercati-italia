# Dedicated no-cost local Happings crawler and source-quality audit.
# Run only from a cloned, marked checkout under %LOCALAPPDATA%.
param(
  [string]$DataRoot = "$env:LOCALAPPDATA\mercati-italia"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$Marker = Join-Path $Repo ".happings-dedicated-checkout"
$DataRoot = [System.IO.Path]::GetFullPath($DataRoot)
$LogFolder = Join-Path $DataRoot "logs"
New-Item -ItemType Directory -Force -Path $LogFolder | Out-Null
$LogPath = Join-Path $LogFolder ("happings-" + (Get-Date -Format "yyyy-MM-dd") + ".log")
Start-Transcript -Path $LogPath -Append | Out-Null
try {
  if (!(Test-Path $Marker -PathType Leaf)) {
    throw "This script may only update the dedicated Happings checkout"
  }
  if (!(Test-Path (Join-Path $Repo "backend\happings_daily_local.py"))) {
    throw "Missing Happings quality pipeline entrypoint"
  }
  $ExpectedOrigin = "https://github.com/tommyv-spec/mercati-italia.git"
  $CurrentOrigin = (& git -C $Repo remote get-url origin).Trim()
  if ($LASTEXITCODE -ne 0 -or $CurrentOrigin -ne $ExpectedOrigin) {
    throw "Unexpected Happings GitHub remote"
  }
  & git -C $Repo fetch --quiet --depth=1 origin "refs/heads/improve/data-quality-security-performance-2026-10-11"
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to fetch trusted DEV revision: no new HTTP crawler launched"
  }
  & git -C $Repo -c core.autocrlf=false reset --hard FETCH_HEAD
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to select trusted DEV revision"
  }
  $Python = (Get-Command python -ErrorAction Stop).Source
  # Windows can otherwise decode UTF-8 ISTAT cities through CP1252.
  # Explicit Python UTF-8 mode is mandatory for every pipeline stage.
  $env:PYTHONUTF8 = "1"
  $env:PYTHONIOENCODING = "utf-8"
  Write-Output "SOURCE_CODE $(git -C $Repo rev-parse HEAD)"
  Push-Location $Repo
  try {
    # Fail closed if a parser or source guard regressed.
    & $Python -X utf8 -m unittest discover -s "backend/tests" -p "test_happings_*.py"
    if ($LASTEXITCODE -ne 0) {
      throw "Happings guard tests failed; no new HTTP crawler launched"
    }
    & $Python -X utf8 "backend/happings_daily_local.py" --repo $Repo --snapshot (Join-Path $DataRoot "happings-full-crawl") --out (Join-Path $DataRoot "happings-reconciliation") --max-pages 70 --discovery-days 1
    if ($LASTEXITCODE -ne 0) {
      throw "Happings source refresh or source-to-DEV audit failed"
    }
    # The same repeatable daily run now progresses new-market admissions.
    # No push occurs unless each source has a live HTML replay, canonical
    # ISTAT location and exact preserved baseline IDs in the static export.
    & $Python -X utf8 "backend/happings_weekly_dev_admission.py" --repo $Repo --out (Join-Path $DataRoot "happings-reconciliation") --max-pages 8 --max-new 32 --publish-dev
    if ($LASTEXITCODE -ne 0) {
      throw "Happings weekly DEV admission failed its replay or publication gate"
    }
  } finally {
    Pop-Location
  }
  Write-Output "HAPPINGS_DAILY_OK"
} catch {
  Write-Error ("HAPPINGS_DAILY_FAILED: " + $_.Exception.Message)
  exit 1
} finally {
  Stop-Transcript | Out-Null
  Get-ChildItem -Path $LogFolder -Filter "happings-*.log" -File |
    Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-14)} |
    Remove-Item -Force -ErrorAction SilentlyContinue
}
