-- One remote database, two release pointers, immutable datasets.
CREATE TABLE IF NOT EXISTS catalog_datasets (
  dataset_id TEXT PRIMARY KEY,
  content_signature TEXT NOT NULL UNIQUE,
  manifest_sha256 TEXT NOT NULL,
  source_git_sha TEXT NOT NULL,
  expected_rows INTEGER NOT NULL CHECK(expected_rows BETWEEN 1 AND 100000),
  status TEXT NOT NULL DEFAULT 'loading' CHECK(status IN ('loading','ready','archived')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  ready_at TEXT
);
CREATE TABLE IF NOT EXISTS catalog_markets (
  dataset_id TEXT NOT NULL REFERENCES catalog_datasets(dataset_id),
  slug TEXT NOT NULL,
  nome TEXT NOT NULL,
  citta TEXT NOT NULL,
  provincia TEXT NOT NULL DEFAULT '',
  regione TEXT NOT NULL,
  fonte TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  payload_sha256 TEXT NOT NULL,
  PRIMARY KEY (dataset_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_catalog_city ON catalog_markets(dataset_id,regione,provincia,citta);
CREATE INDEX IF NOT EXISTS idx_catalog_source ON catalog_markets(dataset_id,fonte);
CREATE TABLE IF NOT EXISTS catalog_channels (
  channel TEXT PRIMARY KEY CHECK(channel IN ('dev','prod')),
  dataset_id TEXT REFERENCES catalog_datasets(dataset_id),
  activated_at TEXT
);
INSERT OR IGNORE INTO catalog_channels(channel,dataset_id) VALUES ('dev',NULL);
INSERT OR IGNORE INTO catalog_channels(channel,dataset_id) VALUES ('prod',NULL);
CREATE TABLE IF NOT EXISTS catalog_import_chunks (
  dataset_id TEXT NOT NULL REFERENCES catalog_datasets(dataset_id),
  chunk_no INTEGER NOT NULL,
  chunk_sha256 TEXT NOT NULL,
  num_records INTEGER NOT NULL,
  imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY(dataset_id,chunk_no)
);
CREATE TABLE IF NOT EXISTS happings_source_facts (
  source_url TEXT PRIMARY KEY,
  html_sha256 TEXT NOT NULL,
  facts_sha256 TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK(source_type IN ('detail','weekly','unknown')),
  source_status TEXT NOT NULL CHECK(source_status IN ('parsed','unavailable','unassessed','robots_denied')),
  facts_gzip_base64 TEXT NOT NULL,
  imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS source_import_chunks (
  import_id TEXT NOT NULL,
  chunk_no INTEGER NOT NULL,
  chunk_sha256 TEXT NOT NULL,
  num_records INTEGER NOT NULL,
  imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY(import_id,chunk_no)
);
CREATE TABLE IF NOT EXISTS release_audit (
  event_id TEXT PRIMARY KEY,
  channel TEXT NOT NULL CHECK(channel IN ('dev','prod')),
  old_dataset_id TEXT,
  new_dataset_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
