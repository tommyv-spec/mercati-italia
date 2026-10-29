# Registers the Windows task "MercatiItalia-Vintagery": the daily Vintagery read at 03:30
# (before the 04:30 nightly), only while the owner is logged in (it needs their Chrome).
# Run once, by the owner:
#   powershell -NoProfile -ExecutionPolicy Bypass -File <checkout>\ops\vintagery\install-task.ps1
# It copies refresh-daily.ps1 to %LOCALAPPDATA%\mercati-italia\vintagery\ and runs it from there.
$ErrorActionPreference = 'Stop'
$Root = Join-Path $env:LOCALAPPDATA 'mercati-italia\vintagery'
New-Item -ItemType Directory -Force $Root | Out-Null
$Script = Join-Path $Root 'refresh-daily.ps1'
Copy-Item -Force (Join-Path $PSScriptRoot 'refresh-daily.ps1') $Script

$Action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""
$Trigger = New-ScheduledTaskTrigger -Daily -At '03:30'
# Above the script's own limits (read 60 min + nightly wait 180 min): a task killed by
# Windows leaves no log line and no alarm.
$Settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 5)
$Principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
Register-ScheduledTask -TaskName 'MercatiItalia-Vintagery' -Action $Action -Trigger $Trigger `
    -Settings $Settings -Principal $Principal -Force | Out-Null
Write-Output "Registered MercatiItalia-Vintagery: daily 03:30, runs $Script, logs in $Root\logs"
