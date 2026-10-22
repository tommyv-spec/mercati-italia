# Happings source facts — independently restored GitHub archive

This archive captures **2,313 Happings source pages as parsed factual records**, including SHA-256 provenance, plus **10 related quality/reconciliation reports**. Its 88 JSON source files are indexed in `manifest.json` with exact SHA-256 hashes. They are Git objects on a dedicated archive branch, not data loaded by the public site.

**Independent restore passed on 2026-10-22:** all 88 files downloaded from GitHub, compared against the Git-hosted manifest SHA-256, and reconstituted into **2,313 gzip JSON source records plus 10 reports**. See `github-restore-proof.json` for the pinned Git commit and test result.

## Restore on an empty machine

```bash
git clone --depth 1 --branch happings-source-archive-2026-10-21 --single-branch https://github.com/tommyv-spec/mercati-italia.git mercati-archive
cd mercati-archive
python backend/happings_github_readable_backup.py \
  --out source-archives/happings/2026-10-21 \
  --restore-to /path/to/empty/happings-backup
```

Reconstructed source page files are `happings-full-crawl/pages/*.json.gz`; reports are under `happings-reconciliation/`. The restore refuses to overwrite existing data.

**Scope:** The original complete HTML DOM was never part of the full-scan snapshot. This GitHub backup preserves **structured facts and original HTML hashes**, not byte-identical raw HTML or byte-identical gzip streams. Re-fetch the publisher if new fields outside the saved parser facts are required.

**Costs:** Ordinary Git objects only. No Git LFS, paid storage, new GitHub Actions workflows or production publication. Do not publish any personal computer paths, tokens or logs.
