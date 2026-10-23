-- Cloudflare D1: additive, repeatable migration. Never rewrite a legacy snapshot.
-- The original active DEV catalog_markets rows remain the immutable base.
CREATE TABLE IF NOT EXISTS catalog_dataset_parents (
  dataset_id TEXT PRIMARY KEY REFERENCES catalog_datasets(dataset_id),
  parent_dataset_id TEXT NOT NULL REFERENCES catalog_datasets(dataset_id),
  CHECK (dataset_id <> parent_dataset_id)
);
CREATE INDEX IF NOT EXISTS idx_catalog_dataset_parent
  ON catalog_dataset_parents(parent_dataset_id);

-- Only modified and newly admitted market rows are stored for each new version.
CREATE TABLE IF NOT EXISTS catalog_market_changes (
  dataset_id TEXT NOT NULL REFERENCES catalog_datasets(dataset_id),
  slug TEXT NOT NULL,
  nome TEXT NOT NULL,
  citta TEXT NOT NULL,
  provincia TEXT NOT NULL DEFAULT '',
  regione TEXT NOT NULL,
  fonte TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
  payload_sha256 TEXT NOT NULL,
  PRIMARY KEY (dataset_id,slug)
);
CREATE INDEX IF NOT EXISTS idx_catalog_changes_city
  ON catalog_market_changes(dataset_id,regione,provincia,citta);

-- Independent resumable checkpoints, kept separate from the legacy snapshot importer.
CREATE TABLE IF NOT EXISTS catalog_delta_import_chunks (
  dataset_id TEXT NOT NULL REFERENCES catalog_datasets(dataset_id),
  chunk_no INTEGER NOT NULL,
  chunk_sha256 TEXT NOT NULL,
  num_records INTEGER NOT NULL,
  imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY (dataset_id,chunk_no)
);
