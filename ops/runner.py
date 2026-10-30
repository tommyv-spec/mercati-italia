#!/usr/bin/env python3
"""Run the project's scheduled workflows on this machine, without GitHub Actions.

The job definitions are the same YAML files GitHub Actions used, kept in
ops/workflows/. Each job runs in a fresh clone of the repository: bash steps,
checkout, artifacts handed between jobs. Pushes use this machine's SSH key.
A failed workflow opens (or comments on) one GitHub issue; success closes it.

    python ops/runner.py daily            # everything due today (scheduler entry)
    python ops/runner.py run <workflow>   # one workflow now, e.g. market-autopilot
    python ops/runner.py plan             # what "daily" would run, and why
    python ops/runner.py rehearse --code <checkout>   # today's market-autopilot run
                                          # replayed with that checkout's new commits; nothing published

Supported subset (all the project uses): checkout, setup-python/-node (the
machine's own Python 3.13 and Node 22), upload/download-artifact, github-script
(skipped; the runner notifies), job/step `if`, `env`, `shell: bash`,
`continue-on-error`, `timeout-minutes`, ${{ env/github/needs/inputs }}.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from types import SimpleNamespace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO = "tommyv-spec/mercati-italia"
REPO_SSH = f"git@github.com:{REPO}.git"
REPO_HTTPS = f"https://github.com/{REPO}.git"


def set_origin(repo_dir, push=REPO_SSH):
    # Same origin as actions/checkout (scripts verify it); push over SSH.
    git("remote", "set-url", "origin", REPO_HTTPS, cwd=repo_dir)
    git("remote", "set-url", "--push", "origin", push, cwd=repo_dir)
DEV = "improve/data-quality-security-performance-2026-10-11"
WORKFLOWS = Path(__file__).resolve().parent / "workflows"
HOME = Path(os.environ.get("MERCATI_RUNNER_HOME")
            or Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "mercati-italia" / "runner")
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")
BASH = os.environ.get("MERCATI_BASH") or (str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash"))
KEEP_RUNS = 10  # one night is ~7 workflows: a failed run's files survive until the next night
EXPR = re.compile(r"\$\{\{\s*(.*?)\s*\}\}", re.S)


class Ctx(dict):
    """Attribute access like GitHub expressions; unknown names are ''."""
    def __getattr__(self, name):
        return self.get(name, "")


def evaluate(expr, ctx):
    py = expr.replace("&&", " and ").replace("||", " or ")
    py = re.sub(r"!(?!=)", " not ", py)
    return eval(py, {"__builtins__": {}}, ctx)  # noqa: S307 - own repo's workflow files only


def expand(text, ctx):
    return EXPR.sub(lambda m: str(evaluate(m.group(1), ctx)), str(text))


def condition(raw, ctx, default):
    if raw is None:
        return default
    return bool(evaluate(EXPR.sub(lambda m: m.group(1), str(raw)), ctx))


def git(*args, cwd=None):
    subprocess.run(["git", *map(str, args)], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def rmtree(path):
    def writable(func, target, _):
        os.chmod(target, stat.S_IWRITE)
        func(target)
    shutil.rmtree(path, onerror=writable) if Path(path).exists() else None


def kill_leftovers(job_dir):
    """Background servers (vite preview) die with a GitHub VM; here we stop them."""
    if os.name == "nt":
        pattern = str(job_dir).replace("'", "''")
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*{pattern}*' }}"
                        " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(["pkill", "-f", str(job_dir)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def bash_tmp():
    out = subprocess.run([BASH, "-c", "cygpath -m /tmp 2>/dev/null || echo /tmp"],
                         capture_output=True, text=True).stdout.strip()
    return Path(out or "/tmp")


class Run:
    def __init__(self, name, event):
        self.name, self.event = name, event
        self.id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + name
        self.dir = HOME / "runs" / self.id
        self.artifacts = self.dir / "artifacts"
        self.log_path = HOME / "logs" / (self.id + ".log")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.log = open(self.log_path, "a", encoding="utf-8", errors="replace")
        self.rehearsal, self.inputs = None, Ctx()

    def say(self, text):
        line = f"[{datetime.now():%H:%M:%S}] {text}"
        print(line, flush=True)
        self.log.write(line + "\n")
        self.log.flush()


def update_mirror():
    mirror = HOME / "mirror.git"
    if not mirror.exists():
        git("clone", "-q", "--mirror", REPO_SSH, mirror)
    git("-C", mirror, "fetch", "-q", "--prune", "origin")
    return mirror


def copy_into(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dest)


def upload(run, job_dir, spec, ctx):
    """As actions/upload-artifact: the root is the least common ancestor of
    the search paths (a single directory: the directory itself)."""
    target = run.artifacts / expand(spec["name"], ctx)
    patterns = [p.strip() for p in expand(spec.get("path", ""), ctx).splitlines() if p.strip()]
    bases = [bash_tmp() / p[len("/tmp/"):] if p.startswith("/tmp/") else job_dir / p for p in patterns]
    searches = [Path(*[part for part in iter_until_glob(b.parts)]) for b in bases]
    if len(searches) == 1:
        root = searches[0] if searches[0].is_dir() else searches[0].parent
    else:
        root = Path(os.path.commonpath([str(s) for s in searches]))
    found = 0
    for base in bases:
        for match in map(Path, glob.glob(str(base))):
            copy_into(match, target / match.relative_to(root) if match != root else target)
            found += 1
    if not found and spec.get("if-no-files-found") == "error":
        raise RuntimeError("No files for artifact " + target.name)


def iter_until_glob(parts):
    for part in parts:
        if any(ch in part for ch in "*?["):
            return
        yield part


def download(run, job_dir, spec, ctx):
    source = run.artifacts / expand(spec["name"], ctx)
    if not source.exists():
        raise RuntimeError("Artifact not found: " + source.name)
    copy_into(source, job_dir / expand(spec.get("path") or ".", ctx))


def run_job(run, wf, job_name, job, needs_results, mirror, env_base):
    job_dir = run.dir / job_name
    tmp = run.dir / (job_name + "-tmp")
    tmp.mkdir(parents=True, exist_ok=True)
    # GitHub limits were sized for billed minutes on fast runners; locally a
    # job may take longer (polite pauses), but a hung one must still stop.
    timeout = 60 * max(int(job.get("timeout-minutes") or 360), 60)
    started, failed = time.monotonic(), False
    summary = run.dir / (job_name + "-summary.md")
    for index, step in enumerate(job.get("steps") or []):
        ctx = Ctx(env=Ctx(env_base), needs=needs_results, inputs=run.inputs, secrets=Ctx(),
                  github=Ctx(run_id=run.id, run_number=run.id, event_name=run.event, repository=REPO),
                  always=lambda: True, success=lambda: not failed, failure=lambda: failed,
                  cancelled=lambda: False)
        label = step.get("name") or step.get("uses") or f"step {index + 1}"
        if not condition(step.get("if"), ctx, default=not failed):
            run.say(f"  - skip: {label}")
            continue
        run.say(f"  - {label}")
        try:
            uses = str(step.get("uses") or "").split("@")[0]
            spec = step.get("with") or {}
            if uses == "actions/checkout":
                git("clone", "-q", "-c", "core.autocrlf=false", mirror, job_dir)
                git("checkout", "-q", expand(spec.get("ref") or "main", ctx), cwd=job_dir)
                set_origin(job_dir, push=run.rehearsal.origin if run.rehearsal else REPO_SSH)
                if run.rehearsal and job_name == "candidate":
                    # The replayed night's saved reads, for --resume; not its finished catalog.
                    saved = run.rehearsal.saved
                    shutil.copytree(saved, job_dir / "autopilot-output",
                                    ignore=lambda d, names: ["candidate"] if Path(d) == saved else [])
            elif uses in ("actions/setup-python", "actions/setup-node", "actions/github-script"):
                pass  # the machine's own interpreters; notifications are the runner's job
            elif uses == "actions/upload-artifact":
                upload(run, job_dir, spec, ctx)
            elif uses == "actions/download-artifact":
                download(run, job_dir, spec, ctx)
            elif uses:
                raise RuntimeError("Unsupported action " + uses)
            else:
                script = tmp / f"step-{index + 1}.sh"
                script.write_text(expand(step["run"], ctx), encoding="utf-8", newline="\n")
                # GitHub runners live in UTC and the pipeline compares
                # date.today() with UTC timestamps: give every job that clock.
                env = {**os.environ, **env_base, "CI": "true", "PYTHONUTF8": "1", "TZ": "UTC0",
                       "GITHUB_ACTIONS": "", "GITHUB_RUN_ID": run.id, "GITHUB_EVENT_NAME": run.event,
                       "GITHUB_REPOSITORY": REPO, "GITHUB_WORKSPACE": job_dir.as_posix(),
                       "RUNNER_TEMP": tmp.as_posix(), "GITHUB_STEP_SUMMARY": summary.as_posix(),
                       "GITHUB_OUTPUT": (tmp / "output").as_posix(), "GITHUB_ENV": (tmp / "env").as_posix(),
                       **{k: expand(v, ctx) for k, v in (step.get("env") or {}).items()}}
                remaining = timeout - (time.monotonic() - started)
                result = subprocess.run([BASH, "--noprofile", "--norc", "-eo", "pipefail", str(script)],
                                        cwd=job_dir if job_dir.exists() else run.dir, env=env,
                                        stdout=run.log, stderr=subprocess.STDOUT, timeout=max(remaining, 1))
                if result.returncode:
                    raise RuntimeError(f"exit code {result.returncode}")
        except Exception as error:  # one failed step fails the job unless allowed
            run.say(f"    FAILED: {error}")
            if not step.get("continue-on-error"):
                failed = True
    kill_leftovers(job_dir)
    return "failure" if failed else "success"


def seconds_until_safe_start(now):
    """The pipeline stamps every read with its UTC day, so a job must not cross UTC
    midnight. Jobs take under an hour: never start one in the last UTC hour."""
    if now.hour != 23:
        return 0
    return (now.replace(hour=0, minute=5, second=0, microsecond=0) + timedelta(days=1) - now).total_seconds()


def run_workflow(name, event="schedule", rehearsal=None):
    wait = seconds_until_safe_start(datetime.now(timezone.utc))
    if wait:
        print(f"waiting {round(wait / 60)} min: no job starts in the last hour before UTC midnight", flush=True)
        time.sleep(wait)
    wf = yaml.safe_load((WORKFLOWS / f"{name}.yml").read_text("utf-8"))
    run = Run(name + ("-rehearsal" if rehearsal else ""), event)
    run.say(f"workflow {name} ({event}) → {run.dir}")
    if rehearsal:
        run.rehearsal, run.inputs = rehearsal, Ctx(offline="true", resume="true")
    mirror = rehearsal.origin if rehearsal else update_mirror()
    results = Ctx()
    github = Ctx(run_id=run.id, run_number=run.id, event_name=event, repository=REPO)
    env_base = {k: expand(v, Ctx(github=github, env=Ctx())) for k, v in (wf.get("env") or {}).items()}
    for job_name, job in wf["jobs"].items():
        needs = job.get("needs") or []
        needs = [needs] if isinstance(needs, str) else needs
        steps = job.get("steps") or []
        if steps and all(str(s.get("uses", "")).startswith("actions/github-script") for s in steps):
            # GitHub-only housekeeping/notification: done by the runner itself.
            results[job_name] = Ctx(result="success")
            continue
        ctx = Ctx(needs=results, env=Ctx(env_base), github=Ctx(event_name=event),
                  always=lambda: True, cancelled=lambda: False,
                  success=lambda: all(results[n].result == "success" for n in needs),
                  failure=lambda: any(results[n].result == "failure" for n in needs))
        if not condition(job.get("if"), ctx, default=all(results[n].result == "success" for n in needs)):
            results[job_name] = Ctx(result="skipped")
            run.say(f"job {job_name}: skipped")
            continue
        if rehearsal and (job.get("permissions") or {}).get("contents") == "write":
            results[job_name] = Ctx(result="skipped")
            run.say(f"job {job_name}: skipped (rehearsal: it writes to the repository)")
            continue
        run.say(f"job {job_name}")
        results[job_name] = Ctx(result=run_job(run, wf, job_name, job, results, mirror, env_base))
        run.say(f"job {job_name}: {results[job_name].result}")
    ok = all(r.result in ("success", "skipped") for r in results.values()) and any(
        r.result == "success" for r in results.values())
    run.say(f"workflow {name}: {'OK' if ok else 'FAILED'}")
    if rehearsal:
        return ok, run  # invisible to the schedule and the alarms
    run.log.close()
    record(name, ok, run)
    notify(name, ok, run)
    prune_runs()
    return ok, run


def record(name, ok, run):
    path = HOME / "state.json"
    state = json.loads(path.read_text("utf-8")) if path.exists() else {}
    entry = state.get(name, {})
    entry.update(status="ok" if ok else "failed", at=datetime.now(timezone.utc).isoformat(timespec="minutes"),
                 log=str(run.log_path))
    if ok:
        entry["last_success"] = date.today().isoformat()
    state[name] = entry
    path.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def notify(name, ok, run, intro=None):
    """One open issue per failing workflow; closed again when it recovers."""
    title = f"[Automazione locale] {name} — verifica richiesta"
    try:
        found = json.loads(subprocess.run(
            ["gh", "issue", "list", "-R", REPO, "--state", "open", "--search", f'"{title}" in:title',
             "--json", "number,title"], capture_output=True, text=True, check=True).stdout)
        issue = next((i["number"] for i in found if i["title"] == title), None)
        tail = "".join(open(run.log_path, encoding="utf-8", errors="replace").readlines()[-40:])
        intro = intro or (f"Esecuzione `{run.id}` sul computer dell'automazione non riuscita. "
                          "Nessun dato parziale viene pubblicato.")
        body = f"{intro}\n\nUltime righe del log (`{run.log_path}`):\n\n```\n{tail[-6000:]}\n```"
        if ok and issue:
            subprocess.run(["gh", "issue", "close", str(issue), "-R", REPO, "-c", f"Ripristinato: `{run.id}`"],
                           check=True, capture_output=True)
        elif not ok and issue:
            subprocess.run(["gh", "issue", "comment", str(issue), "-R", REPO, "-b", body], check=True,
                           capture_output=True)
        elif not ok:
            subprocess.run(["gh", "issue", "create", "-R", REPO, "-t", title, "-b", body], check=True,
                           capture_output=True)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print("notification unavailable:", error, file=sys.stderr)


def prune_runs():
    # Each run holds full clones (+ node_modules): keep only the latest few.
    for old in sorted((HOME / "runs").glob("*"))[:-KEEP_RUNS]:
        rmtree(old)


def schedule_of(name):
    wf = yaml.safe_load((WORKFLOWS / f"{name}.yml").read_text("utf-8"))
    on = wf.get(True) or wf.get("on") or {}
    crons = [s["cron"] for s in (on.get("schedule") or [])] if isinstance(on, dict) else []
    return crons[0].split() if crons else None


def due(name, state, today):
    """Daily: not yet succeeded today. Weekly: its weekday, or 7 days since success."""
    cron = schedule_of(name)
    if not cron:
        return False, "no schedule"
    last = state.get(name, {}).get("last_success")
    weekdays = cron[4]
    if weekdays == "*":
        return last != today.isoformat(), f"daily; last success {last or 'never'}"
    cron_day = (today.weekday() + 1) % 7
    days = {int(d) % 7 for d in weekdays.split(",")}
    stale = not last or (today - date.fromisoformat(last)).days >= 7
    return (cron_day in days and last != today.isoformat()) or stale, f"weekly; last success {last or 'never'}"


def scorecard():
    """Publish the one-page quality report with the latest job states."""
    mirror = update_mirror()
    work = HOME / "scorecard"
    rmtree(work)
    git("clone", "-q", "-c", "core.autocrlf=false", mirror, work)
    git("checkout", "-q", DEV, cwd=work)
    set_origin(work)
    state = HOME / "state.json"
    env = {**os.environ, "PYTHONUTF8": "1"}
    out = subprocess.run([sys.executable, "backend/quality_scorecard.py", "--jobs", str(state)],
                         cwd=work, env=env, check=True, stdout=subprocess.PIPE, text=True).stdout
    # Its red flags (a source no longer re-read, a figure that dropped, a failed job) open the
    # same issue alarm as a failed job, and close it when the report is clean again.
    flags = json.loads(out.strip().splitlines()[-1])["red_flags"]
    notify("qualita-dati", flags == 0,
           SimpleNamespace(id=f"qualita-{date.today()}", log_path=work / "reports/QUALITA.md"),
           intro="Il controllo qualità dei dati segnala problemi (sezione «Semaforo»).")
    git("add", "reports/QUALITA.md", "reports/quality-history.json", cwd=work)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=work).returncode:
        git("-c", "user.name=mercati-runner", "-c", "user.email=runner@mercati.local",
            "commit", "-q", "-m", "report: weekly data quality scorecard (DEV only)", cwd=work)
        git("push", "-q", "origin", f"HEAD:{DEV}", cwd=work)


CATALOG = "candidate/public/data/v1/manifest.json"
CATALOG_DIFF = """
import json, sys
sys.path.insert(0, "backend")
from collections import Counter
from pathlib import Path
from merge_catalog import load_existing
old, new = ({r["slug"]: r for r in load_existing(Path(p))} for p in sys.argv[1:3])
diff = {s: {k: [old[s].get(k), new[s].get(k)] for k in sorted(set(old[s]) | set(new[s]))
            if old[s].get(k) != new[s].get(k)} for s in sorted(old.keys() & new.keys())}
diff = {s: d for s, d in diff.items() if d}
report = {"added": sorted(new.keys() - old.keys()), "removed": sorted(old.keys() - new.keys()),
          "changed": len(diff), "fields": dict(Counter(k for d in diff.values() for k in d).most_common())}
open(sys.argv[3], "w", encoding="utf-8").write(json.dumps({**report, "records": diff}, ensure_ascii=False, indent=1))
print(json.dumps({**report, "added": len(report["added"]), "removed": len(report["removed"])}))
"""


def replay_source(run_id=None):
    """The saved reads of today's latest market-autopilot run: --resume only accepts the same day."""
    today = datetime.now(timezone.utc).date().isoformat()
    for run_dir in sorted((HOME / "runs").glob(run_id or "*-market-autopilot"), reverse=True):
        saved = run_dir / "artifacts" / f"mercati-checkpoints-{run_dir.name}"
        baseline = saved / "checkpoints" / "baseline.json"
        if ((saved / CATALOG).is_file() and baseline.is_file()
                and json.loads(baseline.read_text("utf-8"))["result"]["today"] == today):
            return saved
    raise SystemExit(f"no market-autopilot run of {today} (UTC) with a finished catalog to replay")


def rehearse(code=None, replay=None):
    """Replay today's nightly run with new commits: that night's code and catalog plus the
    commits of `code` that DEV lacks, fed the source reads it saved (offline + resume).
    Runs the jobs that only read the repository, then the publish job's Happings admission
    without publishing, and writes how the catalog differs from that night's. Every job
    clones a throwaway copy and pushes only into it; state.json and the alarms are untouched."""
    saved = replay_source(replay)
    for old in (HOME / "runs").glob("*-rehearsal"):
        rmtree(old)  # one at a time, so rehearsals never prune the night they replay
    work = HOME / "rehearsal"
    rmtree(work)
    origin, tree = work / "origin.git", work / "tree"
    git("clone", "-q", "--bare", update_mirror(), origin)
    git("clone", "-q", "-c", "core.autocrlf=false", origin, tree)
    git("checkout", "-q", "-B", DEV, (saved / "dev-source-sha.txt").read_text().strip(), cwd=tree)
    tested = []
    if code:
        git("fetch", "-q", Path(code).resolve(), "HEAD", cwd=tree)
        tested = subprocess.run(["git", "rev-list", "--reverse", "--no-merges", f"origin/{DEV}..FETCH_HEAD"],
                                cwd=tree, check=True, capture_output=True, text=True).stdout.split()
        picked = subprocess.run(["git", "-c", "user.name=mercati-runner", "-c", "user.email=runner@mercati.local",
                                 "cherry-pick", *tested], cwd=tree, capture_output=True, text=True) if tested else None
        if picked and picked.returncode:
            raise SystemExit("the tested commits do not apply to that night's code:\n" + picked.stderr[-2000:])
    git("push", "-q", "-f", "origin", f"HEAD:refs/heads/{DEV}", cwd=tree)
    ok, run = run_workflow("market-autopilot", "workflow_dispatch", Ctx(origin=origin, saved=saved))
    run.say(f"rehearsal of {saved.parent.parent.name} with {len(tested)} tested commit(s): {' '.join(tested) or '-'}")
    env = {**os.environ, "PYTHONUTF8": "1", "TZ": "UTC0"}
    if ok:
        mine = run.artifacts / f"mercati-checkpoints-{run.id}"
        summary = subprocess.run([sys.executable, "-c", CATALOG_DIFF, saved / CATALOG, mine / CATALOG,
                                  run.dir / "catalog-diff.json"], cwd=tree, env=env, check=True,
                                 capture_output=True, text=True).stdout.strip()
        run.say(f"catalog vs that night ({run.dir / 'catalog-diff.json'}): {summary}")
        # The publish job copies the catalog into DEV, then runs this admission with --publish-dev.
        rmtree(tree / "public/data/v1")
        shutil.copytree(mine / "candidate/public/data/v1", tree / "public/data/v1")
        set_origin(tree, push=origin)
        (tree / ".happings-dedicated-checkout").write_text("rehearsal, never published\n", encoding="utf-8")
        # ponytail: page/new limits copied from the publish step; keep them in step with it.
        admitted = subprocess.run([sys.executable, "-X", "utf8", "backend/happings_weekly_dev_admission.py",
                                   "--repo", ".", "--from-autopilot-output", mine, "--out", run.dir / "admission",
                                   "--max-pages", "16", "--max-new", "32"],
                                  cwd=tree, env=env, stdout=run.log, stderr=subprocess.STDOUT)
        report = run.dir / "admission" / "happings-weekly-admission.json"
        status = json.loads(report.read_text("utf-8"))["status"] if report.is_file() else "no report"
        ok = admitted.returncode == 0 and status in (
            "qa_approved", "no_eligible_source_pages", "no_new_admissible_markets")
        run.say(f"Happings admission without publishing: {status}")
    run.say(f"rehearsal {'PASSED' if ok else 'FAILED'}; log {run.log_path}")
    run.log.close()
    return ok


def lock():
    HOME.mkdir(parents=True, exist_ok=True)
    path = HOME / "runner.lock"
    if path.exists() and time.time() - path.stat().st_mtime > 8 * 3600:
        path.unlink()  # a crashed run must not block the schedule forever
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return path


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("daily")
    sub.add_parser("plan")
    one = sub.add_parser("run")
    one.add_argument("workflow")
    rh = sub.add_parser("rehearse")
    rh.add_argument("--code", help="a local checkout: its commits that DEV lacks are tested")
    rh.add_argument("--replay", help="run id to replay (default: today's latest market-autopilot)")
    args = p.parse_args()
    names = sorted((p.stem for p in WORKFLOWS.glob("*.yml") if schedule_of(p.stem)),
                   key=lambda n: (schedule_of(n)[1].zfill(2), schedule_of(n)[0].zfill(2)))
    state_path = HOME / "state.json"
    state = json.loads(state_path.read_text("utf-8")) if state_path.exists() else {}
    if args.cmd == "plan":
        for name in names:
            go, why = due(name, state, date.today())
            print(f"{'RUN ' if go else 'skip'} {name}: {why}")
        return
    held = lock()
    try:
        if args.cmd == "run":
            sys.exit(0 if run_workflow(args.workflow, event="workflow_dispatch")[0] else 1)
        if args.cmd == "rehearse":
            sys.exit(0 if rehearse(args.code, args.replay) else 1)
        failures = [n for n in names if due(n, state, date.today())[0] and not run_workflow(n)[0]]
        scorecard()
        sys.exit(1 if failures else 0)
    finally:
        held.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
