-- ============================================================
-- Mercati d'Italia — Database Schema
-- PostgreSQL / Supabase
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- fuzzy text matching
CREATE EXTENSION IF NOT EXISTS "postgis";       -- geography/geometry

-- ─── Enums ──────────────────────────────────────────────────

CREATE TYPE market_category AS ENUM (
  'alimentare',
  'antiquariato',
  'vintage_abbigliamento',
  'usato',
  'artigianato',
  'misto'
);

CREATE TYPE market_status AS ENUM (
  'attivo',       -- confirmed active
  'non_confermato', -- scraped but not verified recently
  'annullato',    -- canceled
  'archiviato'    -- no longer running
);

CREATE TYPE source_type AS ENUM (
  'scraper',      -- automated scraping
  'manuale',      -- manual data entry
  'comunita',     -- user-submitted
  'api'           -- from a partner API
);

CREATE TYPE recurrence_type AS ENUM (
  'giornaliero',           -- every day
  'settimanale',           -- every week (specific day)
  'bisettimanale',         -- every two weeks
  'mensile_giorno_fisso',  -- e.g. every 1st Sunday
  'mensile_data_fissa',    -- e.g. every 15th
  'annuale',               -- yearly event
  'irregolare',            -- irregular / one-off dates
  'sconosciuto'
);

-- ─── Regions & Cities (lookup tables) ───────────────────────

CREATE TABLE regioni (
  id          SMALLSERIAL PRIMARY KEY,
  nome        TEXT NOT NULL UNIQUE,
  codice_istat TEXT UNIQUE       -- e.g. '09' for Toscana
);

CREATE TABLE province (
  id          SMALLSERIAL PRIMARY KEY,
  nome        TEXT NOT NULL,
  sigla       CHAR(2) NOT NULL UNIQUE,  -- e.g. 'FI', 'RM'
  regione_id  SMALLINT REFERENCES regioni(id)
);

CREATE TABLE comuni (
  id          SERIAL PRIMARY KEY,
  nome        TEXT NOT NULL,
  provincia_id SMALLINT REFERENCES province(id),
  location    GEOGRAPHY(POINT, 4326),   -- PostGIS point
  popolazione INTEGER,
  UNIQUE(nome, provincia_id)
);

CREATE INDEX idx_comuni_location ON comuni USING GIST(location);
CREATE INDEX idx_comuni_nome_trgm ON comuni USING GIN(nome gin_trgm_ops);

-- ─── Markets (core table) ───────────────────────────────────

CREATE TABLE mercati (
  id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  nome            TEXT NOT NULL,
  slug            TEXT NOT NULL UNIQUE,     -- URL-friendly name

  -- Location
  comune_id       INTEGER REFERENCES comuni(id),
  indirizzo       TEXT,
  location        GEOGRAPHY(POINT, 4326),   -- lat/lng
  luogo_nome      TEXT,                      -- e.g. "Piazza Grande"

  -- Classification
  categoria       market_category NOT NULL DEFAULT 'misto',
  tags            TEXT[] DEFAULT '{}',       -- e.g. {'al chiuso','produttori locali'}
  status          market_status NOT NULL DEFAULT 'non_confermato',

  -- Schedule
  ricorrenza      recurrence_type DEFAULT 'sconosciuto',
  ricorrenza_testo TEXT,                     -- human-readable: "Ogni prima domenica del mese"
  orario_apertura TIME,
  orario_chiusura TIME,
  orario_testo    TEXT,                      -- fallback: "7:00–14:00" when not parsed

  -- Content
  descrizione     TEXT,
  immagine_url    TEXT,
  sito_web        TEXT,
  telefono        TEXT,

  -- Data quality
  confidence      SMALLINT DEFAULT 50 CHECK (confidence BETWEEN 0 AND 100),
  n_fonti         SMALLINT DEFAULT 0,       -- how many sources confirm this
  verificato_il   TIMESTAMPTZ,              -- last human verification
  
  -- Timestamps
  creato_il       TIMESTAMPTZ DEFAULT NOW(),
  aggiornato_il   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mercati_location ON mercati USING GIST(location);
CREATE INDEX idx_mercati_categoria ON mercati(categoria);
CREATE INDEX idx_mercati_status ON mercati(status);
CREATE INDEX idx_mercati_comune ON mercati(comune_id);
CREATE INDEX idx_mercati_confidence ON mercati(confidence DESC);
CREATE INDEX idx_mercati_nome_trgm ON mercati USING GIN(nome gin_trgm_ops);
CREATE INDEX idx_mercati_tags ON mercati USING GIN(tags);

-- ─── Market Dates (individual occurrences) ──────────────────

CREATE TABLE date_mercato (
  id          BIGSERIAL PRIMARY KEY,
  mercato_id  UUID REFERENCES mercati(id) ON DELETE CASCADE,
  data        DATE NOT NULL,
  confermata  BOOLEAN DEFAULT FALSE,
  annullata   BOOLEAN DEFAULT FALSE,
  note        TEXT,

  UNIQUE(mercato_id, data)
);

CREATE INDEX idx_date_mercato_data ON date_mercato(data);
CREATE INDEX idx_date_mercato_mercato ON date_mercato(mercato_id);
CREATE INDEX idx_date_mercato_prossime ON date_mercato(data) WHERE NOT annullata;

-- ─── Sources (provenance tracking) ─────────────────────────

CREATE TABLE fonti (
  id          SERIAL PRIMARY KEY,
  nome        TEXT NOT NULL UNIQUE,       -- e.g. 'eventiesagre.it'
  url_base    TEXT,
  tipo        source_type DEFAULT 'scraper',
  affidabilita SMALLINT DEFAULT 50 CHECK (affidabilita BETWEEN 0 AND 100),
  attiva      BOOLEAN DEFAULT TRUE,
  note        TEXT,
  creato_il   TIMESTAMPTZ DEFAULT NOW()
);

-- Seed known sources
INSERT INTO fonti (nome, url_base, tipo, affidabilita) VALUES
  ('eventiesagre.it', 'https://www.eventiesagre.it', 'scraper', 80),
  ('ilturista.info', 'https://www.ilturista.info', 'scraper', 75),
  ('mercatini-ditalia.it', 'https://www.mercatini-ditalia.it', 'scraper', 70),
  ('cosedicasa.com', 'https://www.cosedicasa.com/mercatini', 'scraper', 78),
  ('comune', NULL, 'manuale', 90),
  ('utente', NULL, 'comunita', 40);

-- ─── Source ↔ Market link (many-to-many) ────────────────────

CREATE TABLE mercato_fonti (
  id              SERIAL PRIMARY KEY,
  mercato_id      UUID REFERENCES mercati(id) ON DELETE CASCADE,
  fonte_id        INTEGER REFERENCES fonti(id),
  url_originale   TEXT,                    -- exact page URL scraped
  dati_grezzi     JSONB,                   -- raw scraped payload
  hash_contenuto  TEXT,                    -- to detect changes
  primo_visto     TIMESTAMPTZ DEFAULT NOW(),
  ultimo_visto    TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(mercato_id, fonte_id, url_originale)
);

CREATE INDEX idx_mercato_fonti_mercato ON mercato_fonti(mercato_id);

-- ─── Scrape Jobs (tracking scraper runs) ────────────────────

CREATE TABLE scrape_jobs (
  id              SERIAL PRIMARY KEY,
  fonte_id        INTEGER REFERENCES fonti(id),
  iniziato_il     TIMESTAMPTZ DEFAULT NOW(),
  completato_il   TIMESTAMPTZ,
  status          TEXT DEFAULT 'in_corso', -- in_corso, completato, errore
  regione         TEXT,                    -- which region was scraped
  pagine_lette    INTEGER DEFAULT 0,
  mercati_trovati INTEGER DEFAULT 0,
  mercati_nuovi   INTEGER DEFAULT 0,
  mercati_aggiornati INTEGER DEFAULT 0,
  errori          JSONB DEFAULT '[]',
  note            TEXT
);

-- ─── User Favorites ─────────────────────────────────────────

CREATE TABLE preferiti (
  id          BIGSERIAL PRIMARY KEY,
  user_id     UUID NOT NULL,              -- Supabase auth user
  mercato_id  UUID REFERENCES mercati(id) ON DELETE CASCADE,
  creato_il   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, mercato_id)
);

CREATE INDEX idx_preferiti_user ON preferiti(user_id);

-- ─── User Reports (community verification) ─────────────────

CREATE TABLE segnalazioni (
  id          BIGSERIAL PRIMARY KEY,
  user_id     UUID,
  mercato_id  UUID REFERENCES mercati(id) ON DELETE CASCADE,
  tipo        TEXT NOT NULL,              -- 'confermato', 'annullato', 'orari_sbagliati', 'nuovo_mercato'
  messaggio   TEXT,
  dati        JSONB,                      -- e.g. {"orario_corretto": "8:00-15:00"}
  risolta     BOOLEAN DEFAULT FALSE,
  creato_il   TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Views ──────────────────────────────────────────────────

-- Upcoming markets with full location info
CREATE OR REPLACE VIEW v_prossimi_mercati AS
SELECT
  m.id,
  m.nome,
  m.slug,
  m.categoria,
  m.tags,
  m.status,
  m.orario_testo,
  m.ricorrenza_testo,
  m.descrizione,
  m.confidence,
  m.location,
  ST_Y(m.location::geometry) as lat,
  ST_X(m.location::geometry) as lng,
  m.indirizzo,
  m.luogo_nome,
  c.nome as citta,
  p.sigla as provincia,
  p.nome as provincia_nome,
  r.nome as regione,
  dm.data as prossima_data,
  m.aggiornato_il
FROM mercati m
JOIN date_mercato dm ON dm.mercato_id = m.id
LEFT JOIN comuni c ON m.comune_id = c.id
LEFT JOIN province p ON c.provincia_id = p.id
LEFT JOIN regioni r ON p.regione_id = r.id
WHERE dm.data >= CURRENT_DATE
  AND NOT dm.annullata
  AND m.status IN ('attivo', 'non_confermato')
ORDER BY dm.data ASC;

-- Market search function with distance
CREATE OR REPLACE FUNCTION cerca_mercati(
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  raggio_km INTEGER DEFAULT 50,
  categoria_filtro market_category DEFAULT NULL,
  limite INTEGER DEFAULT 50
)
RETURNS TABLE (
  id UUID,
  nome TEXT,
  categoria market_category,
  citta TEXT,
  regione TEXT,
  prossima_data DATE,
  orario TEXT,
  distanza_km DOUBLE PRECISION,
  confidence SMALLINT,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION
)
LANGUAGE SQL STABLE
AS $$
  SELECT DISTINCT ON (m.id)
    m.id,
    m.nome,
    m.categoria,
    c.nome,
    r.nome,
    dm.data,
    m.orario_testo,
    ST_Distance(m.location, ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography) / 1000 as distanza_km,
    m.confidence,
    ST_Y(m.location::geometry),
    ST_X(m.location::geometry)
  FROM mercati m
  JOIN date_mercato dm ON dm.mercato_id = m.id
  LEFT JOIN comuni c ON m.comune_id = c.id
  LEFT JOIN province p ON c.provincia_id = p.id
  LEFT JOIN regioni r ON p.regione_id = r.id
  WHERE dm.data >= CURRENT_DATE
    AND NOT dm.annullata
    AND m.status IN ('attivo', 'non_confermato')
    AND ST_DWithin(m.location, ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography, raggio_km * 1000)
    AND (categoria_filtro IS NULL OR m.categoria = categoria_filtro)
  ORDER BY m.id, dm.data ASC
  LIMIT limite;
$$;

-- ─── Triggers ───────────────────────────────────────────────

-- Auto-update aggiornato_il
CREATE OR REPLACE FUNCTION aggiorna_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.aggiornato_il = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_mercati_aggiornato
  BEFORE UPDATE ON mercati
  FOR EACH ROW EXECUTE FUNCTION aggiorna_timestamp();

-- Auto-update confidence when sources change
CREATE OR REPLACE FUNCTION aggiorna_confidence()
RETURNS TRIGGER AS $$
DECLARE
  n INTEGER;
  avg_aff NUMERIC;
BEGIN
  SELECT COUNT(*), COALESCE(AVG(f.affidabilita), 0)
  INTO n, avg_aff
  FROM mercato_fonti mf
  JOIN fonti f ON f.id = mf.fonte_id
  WHERE mf.mercato_id = COALESCE(NEW.mercato_id, OLD.mercato_id);

  UPDATE mercati SET
    n_fonti = n,
    confidence = LEAST(100, (avg_aff * 0.6 + n * 15)::SMALLINT)
  WHERE id = COALESCE(NEW.mercato_id, OLD.mercato_id);

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_fonti_confidence
  AFTER INSERT OR UPDATE OR DELETE ON mercato_fonti
  FOR EACH ROW EXECUTE FUNCTION aggiorna_confidence();

-- ─── Row Level Security (Supabase) ─────────────────────────

ALTER TABLE mercati ENABLE ROW LEVEL SECURITY;
ALTER TABLE date_mercato ENABLE ROW LEVEL SECURITY;
ALTER TABLE preferiti ENABLE ROW LEVEL SECURITY;
ALTER TABLE segnalazioni ENABLE ROW LEVEL SECURITY;

-- Public read access to markets
CREATE POLICY "Mercati leggibili da tutti" ON mercati
  FOR SELECT USING (true);

CREATE POLICY "Date leggibili da tutti" ON date_mercato
  FOR SELECT USING (true);

-- Users manage their own favorites
CREATE POLICY "Preferiti propri" ON preferiti
  FOR ALL USING (auth.uid() = user_id);

-- Users can submit reports
CREATE POLICY "Segnalazioni proprie" ON segnalazioni
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Segnalazioni leggibili" ON segnalazioni
  FOR SELECT USING (auth.uid() = user_id);
