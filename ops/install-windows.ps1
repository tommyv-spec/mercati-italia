# Install the daily automation on this Windows PC (no GitHub Actions).
# Re-runnable: replaces the task with the same name. Run from any folder:
#   powershell -NoProfile -ExecutionPolicy Bypass -File ops\install-windows.ps1
$ErrorActionPreference = 'Stop'
$home_ = Join-Path $env:LOCALAPPDATA 'mercati-italia\runner'
New-Item -ItemType Directory -Force (Join-Path $home_ 'logs') | Out-Null

# The scheduled entry point: refresh the runner's own copy of DEV, then run
# everything due today. New code on DEV is picked up on the next run.
@'
# Judge commands by exit code: in Windows PowerShell any stderr line of a
# native program would otherwise abort the whole night run.
$ErrorActionPreference = 'Continue'
$home_ = Join-Path $env:LOCALAPPDATA 'mercati-italia\runner'
$code = Join-Path $home_ 'code'
$dev = 'improve/data-quality-security-performance-2026-10-11'
$log = Join-Path $home_ ('logs\daily-' + (Get-Date -Format 'yyyyMMdd') + '.log')
if (-not (Test-Path (Join-Path $code '.git'))) {
  git clone -q -c core.autocrlf=false -b $dev https://github.com/tommyv-spec/mercati-italia.git $code
}
git -C $code fetch -q origin $dev
if ($LASTEXITCODE -eq 0) { git -C $code reset -q --hard FETCH_HEAD }
$env:PYTHONUTF8 = '1'
cmd /c "python `"$code\ops\runner.py`" daily >> `"$log`" 2>&1"
exit $LASTEXITCODE
'@ | Set-Content -Encoding utf8 (Join-Path $home_ 'run-daily.ps1')

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $home_ 'run-daily.ps1') + '"')
$trigger = New-ScheduledTaskTrigger -Daily -At '04:30'
# Wake the PC, run a missed day as soon as it is back on, retry twice.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 6) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 30)
# Interactive logon keeps access to the SSH key and the saved gh login.
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName 'MercatiItalia-Automazione' -Action $action -Trigger $trigger `
  -Settings $settings -Principal $principal -Force | Out-Null

# The old 9:30 Happings crawl only checked; the weekly workflow replaces it.
if (Get-ScheduledTask -TaskName 'MercatiItalia-HappingsDaily' -ErrorAction SilentlyContinue) {
  Disable-ScheduledTask -TaskName 'MercatiItalia-HappingsDaily' | Out-Null
}
Get-ScheduledTask -TaskName 'MercatiItalia-Automazione' | Get-ScheduledTaskInfo |
  Select-Object TaskName, NextRunTime | Format-List
