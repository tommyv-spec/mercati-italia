# Daily Vintagery read, unattended (Windows task "MercatiItalia-Vintagery", see install-task.ps1).
#
# vintagery.it blocks scripts (Vercel Security Checkpoint), so the read runs in the owner's
# Chrome through Claude in Chrome (`claude -p --chrome`). Everything else is done here:
#  1. our own DEV checkout (never the nightly runner's), reset to DEV;
#  2. today's plan (cards to re-read) + the collector, as one script for the page;
#  3. Claude in Chrome runs it in a new vintagery.it tab and waits for the download;
#  4. the newest ~/Downloads/vintagery_cards*.json is merged into the snapshot, then archived;
#  5. if the snapshot changed: wait until the nightly runner is idle, fetch DEV, commit ONLY
#     backend/data/vintagery-snapshot.json, push via SSH.
# Chrome or the extension not connected, Vercel blocking, no download: log, exit 1 and open
# the nightly runner's GitHub issue alarm (closed on the next good day). The nightly then
# keeps using the older snapshot (cards stop counting 45 days after their read).
param(
    [int]$PerDay = 120,
    [int]$WaitRunnerMinutes = 180,
    # Read and merge, but commit and push nothing (a test run).
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$Root = Join-Path $env:LOCALAPPDATA 'mercati-italia\vintagery'
$Repo = Join-Path $Root 'repo'
$Archive = Join-Path $Root 'archive'
$Downloads = Join-Path $env:USERPROFILE 'Downloads'
$Dev = 'improve/data-quality-security-performance-2026-10-11'
$Remote = 'git@github.com:tommyv-spec/mercati-italia.git'
$Snapshot = 'backend/data/vintagery-snapshot.json'
New-Item -ItemType Directory -Force (Join-Path $Root 'logs'), $Archive | Out-Null
$Log = Join-Path $Root ('logs\' + (Get-Date -Format 'yyyy-MM-dd') + '.log')
function Write-Log([string]$Message) { "$(Get-Date -Format s) $Message" | Out-File -FilePath $Log -Append -Encoding utf8 }
function Invoke-Checked([string]$What, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit $LASTEXITCODE)" }
}
# Same alarm as the nightly runner (ops/runner.py notify): one GitHub issue while failing.
function Send-Alarm([bool]$Ok) {
    try {
        $Ops = Join-Path $Repo 'ops'
        if (-not (Test-Path (Join-Path $Ops 'runner.py'))) { return }
        $Code = 'import sys, types; sys.path.insert(0, sys.argv[1]); import runner; ' +
                'runner.notify(''vintagery-daily'', sys.argv[2] == ''1'', types.SimpleNamespace(id=sys.argv[3], log_path=sys.argv[4]))'
        & python -c $Code $Ops ([int]$Ok) ('vintagery-' + (Get-Date -Format 'yyyy-MM-dd')) $Log
    } catch { Write-Log ('alarm unavailable: ' + $_) }
}
$env:PYTHONUTF8 = '1'

try {
    Write-Log 'start'
    # 1. Our own DEV checkout.
    if (-not (Test-Path (Join-Path $Repo '.git'))) {
        Invoke-Checked 'clone' { git clone -q -c core.autocrlf=false --branch $Dev $Remote $Repo }
    }
    Invoke-Checked 'fetch DEV' { git -C $Repo fetch -q $Remote $Dev }
    Invoke-Checked 'reset to DEV' { git -C $Repo reset -q --hard FETCH_HEAD }

    # 2. Today's plan (new cards from the last archived listing, then the oldest reads).
    $Day = Get-Date -Format 'yyyy-MM-dd'
    $Plan = Join-Path $Root 'plan.js'
    $Listing = @(Get-ChildItem -Path $Archive -Filter 'vintagery_cards_*.json' | Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 | ForEach-Object { '--listing'; $_.FullName })
    Invoke-Checked 'plan' { python (Join-Path $Repo 'backend\vintagery_source.py') --plan $Plan --per-day $PerDay --today $Day --out (Join-Path $Repo $Snapshot) @Listing }
    $Script = (Get-Content $Plan -Raw -Encoding utf8) + (Get-Content (Join-Path $Repo 'ops\vintagery\collect.js') -Raw -Encoding utf8)

    # 3. Claude in Chrome reads the pages in the owner's Chrome. The prompt goes in on stdin:
    # Windows PowerShell 5.1 breaks a program argument that holds double quotes.
    $Started = Get-Date
    $Prompt = @"
You run the daily Vintagery read in the user's Chrome. Do exactly this, nothing else:
1. Call tabs_context_mcp with createIfEmpty true, then tabs_create_mcp, and navigate the new tab to https://vintagery.it/ .
2. If the tab title stays "Vercel Security Checkpoint" after waiting 20 seconds (computer action wait), reply exactly BLOCKED and stop. Never try to get past it.
3. Run the script between BEGIN SCRIPT and END SCRIPT below once with javascript_tool in that tab, copied exactly and whole (it returns 'collector started').
4. Every 60 seconds (computer action wait, 10 s at a time) run javascript_tool with: JSON.stringify(window.__vgState)
   until "running" is false, at most 40 minutes.
5. If "last" starts with "stopped", reply BLOCKED: <last>. If it is "finished", wait 10 seconds for the download, close the tab with tabs_close_mcp and reply DONE <done>.
If the Chrome extension is not connected or a browser tool fails twice, reply NOT_CONNECTED and stop.

BEGIN SCRIPT
$Script
END SCRIPT
"@
    $Tools = @('mcp__claude-in-chrome__tabs_context_mcp', 'mcp__claude-in-chrome__tabs_create_mcp',
               'mcp__claude-in-chrome__navigate', 'mcp__claude-in-chrome__javascript_tool',
               'mcp__claude-in-chrome__computer', 'mcp__claude-in-chrome__tabs_close_mcp')
    $OutputEncoding = New-Object System.Text.UTF8Encoding $false
    # No 2>&1 on programs: in Windows PowerShell it turns stderr lines into errors.
    $Answer = $Prompt | & claude -p --chrome --allowedTools $Tools | Out-String
    Write-Log ('claude: ' + $Answer.Trim())
    if ($LASTEXITCODE -ne 0 -or $Answer -notmatch '\bDONE\b') { throw "Claude in Chrome read did not finish: $($Answer.Trim())" }

    # 4. Merge the newest download, then archive it.
    $File = Get-ChildItem -Path $Downloads -Filter 'vintagery_cards*.json' |
        Where-Object { $_.LastWriteTime -gt $Started } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $File) { throw 'No vintagery_cards*.json downloaded during this run' }
    $Merge = & python (Join-Path $Repo 'backend\vintagery_source.py') $File.FullName --out (Join-Path $Repo $Snapshot) | Out-String
    if ($LASTEXITCODE -ne 0) { throw "Merge failed: $Merge" }
    Write-Log ('merge: ' + $Merge.Trim())
    Move-Item -Force $File.FullName (Join-Path $Archive $File.Name)

    # 5. Publish the snapshot alone.
    if ($DryRun) { Write-Log 'dry run: nothing committed'; exit 0 }
    if (-not (git -C $Repo status --porcelain -- $Snapshot)) { Write-Log 'snapshot unchanged'; Send-Alarm $true; exit 0 }
    # The nightly runner holds runner.lock while it runs (ops/runner.py lock(), stale after 8 h).
    # Not process names: "autopilot" also matched the unrelated KavenoAutopilotExecutor and
    # lost the 2026-10-29 read.
    $Lock = Join-Path $env:LOCALAPPDATA 'mercati-italia\runner\runner.lock'
    $Deadline = (Get-Date).AddMinutes($WaitRunnerMinutes)
    while ((Test-Path $Lock) -and (Get-Item $Lock).LastWriteTime -gt (Get-Date).AddHours(-8)) {
        if ((Get-Date) -gt $Deadline) { throw 'Nightly runner still busy: snapshot not pushed today' }
        Start-Sleep -Seconds 60
    }
    Invoke-Checked 'stage snapshot' { git -C $Repo add -- $Snapshot }
    Invoke-Checked 'commit snapshot' { git -C $Repo commit -q -m "Vintagery snapshot: daily read $Day" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" }
    Invoke-Checked 'fetch DEV before push' { git -C $Repo fetch -q $Remote $Dev }
    Invoke-Checked 'merge DEV' { git -C $Repo merge -q --no-edit FETCH_HEAD }
    $Changed = git -C $Repo diff --name-only FETCH_HEAD HEAD
    if (($Changed | Where-Object { $_ -ne $Snapshot })) { throw "Refusing to push files other than the snapshot: $Changed" }
    Invoke-Checked 'push' { git -C $Repo push -q $Remote "HEAD:refs/heads/$Dev" }
    Write-Log 'pushed'
    Send-Alarm $true
    exit 0
} catch {
    Write-Log ('FAILED: ' + $_)
    Send-Alarm $false
    exit 1
}
