# Happings – verified source data snapshot, 22 October 2026

This archive captures **2,349 Happings page fact records** and **10 QA/reconciliation reports**.
The deterministic `manifest.json` indexes **89 JSON files** with SHA-256 checksums.
Eighty JSON blobs are reused byte-for-byte from the 21 October snapshot; only nine new Git blobs were required.
This preserves previous archive versions without Git LFS, extra runners, or any paid storage.

**Restore (once the independent restore proof has been added):**

```bash
git clone --depth 1 --single-branch --branch happings-source-archive-2026-10-22 https://github.com/tommyv-spec/mercati-italia.git mercati-archive
cd mercati-archive
python backend/happings_github_readable_backup.py \
  --out source-archives/happings/2026-10-22 \
  --restore-to /path/to/empty/happings-source-backup
```

This archive contains **extracted structured source facts and original HTML hashes**, not the full original HTML DOM.
The original crawler checkpoint gzip bytes may differ after restore because their JSON facts are re-encoded.
The public website and production dataset are not modified by this archive branch.
