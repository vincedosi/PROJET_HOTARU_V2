-- HOTARU v2 - Schéma Supabase (PostgreSQL)
-- À exécuter dans le SQL Editor du dashboard Supabase (une seule fois).

-- =============================================================================
-- 1. USERS (auth : email, password_hash, role)
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TEXT DEFAULT '',
  last_login TEXT DEFAULT '',
  role TEXT DEFAULT 'user'
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (LOWER(TRIM(email)));

-- =============================================================================
-- 2. AUDITS (legacy / liste par user)
-- =============================================================================
CREATE TABLE IF NOT EXISTS audits (
  id BIGSERIAL PRIMARY KEY,
  audit_id TEXT NOT NULL,
  user_email TEXT NOT NULL,
  workspace TEXT NOT NULL DEFAULT 'Non classé',
  date TEXT DEFAULT '',
  site_url TEXT DEFAULT '',
  nb_pages INTEGER DEFAULT 0,
  data_compressed TEXT,
  nom_site TEXT DEFAULT 'Site Inconnu',
  master_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_audits_user ON audits (LOWER(TRIM(user_email)));

-- =============================================================================
-- 3. JSONLD (modèles par site / workspace)
-- =============================================================================
CREATE TABLE IF NOT EXISTS jsonld (
  id BIGSERIAL PRIMARY KEY,
  site_url TEXT,
  model_id TEXT,
  model_name TEXT,
  page_count INTEGER DEFAULT 0,
  url_pattern TEXT,
  sample_urls TEXT,
  dom_structure TEXT,
  existing_jsonld TEXT,
  recommended_schema TEXT,
  optimized_jsonld TEXT,
  created_at TEXT,
  workspace TEXT,
  user_email TEXT
);

CREATE INDEX IF NOT EXISTS idx_jsonld_user ON jsonld (LOWER(TRIM(user_email)));
CREATE INDEX IF NOT EXISTS idx_jsonld_site ON jsonld (site_url);

-- =============================================================================
-- 4. UNIFIED_SAVES (sauvegardes complètes — 27 champs comme GSheet)
-- =============================================================================
CREATE TABLE IF NOT EXISTS unified_saves (
  id BIGSERIAL PRIMARY KEY,
  save_id TEXT NOT NULL,
  user_email TEXT NOT NULL,
  workspace TEXT NOT NULL DEFAULT 'Non classé',
  site_url TEXT DEFAULT '',
  nom_site TEXT DEFAULT 'Site',
  created_at TEXT DEFAULT '',
  crawl_pages_count INTEGER DEFAULT 0,
  geo_score TEXT,
  geo_clusters_count INTEGER DEFAULT 0,
  jsonld_models_count INTEGER DEFAULT 0,
  geo_stats_pages_crawled TEXT,
  geo_stats_links_discovered TEXT,
  geo_stats_links_filtered TEXT,
  geo_stats_links_duplicate TEXT,
  geo_stats_errors TEXT,
  geo_infra_1 TEXT,
  geo_infra_2 TEXT,
  geo_infra_3 TEXT,
  geo_infra_4 TEXT,
  crawl_data_1 TEXT,
  crawl_data_2 TEXT,
  geo_data_1 TEXT,
  geo_data_2 TEXT,
  jsonld_data_1 TEXT,
  jsonld_data_2 TEXT,
  master_json_1 TEXT,
  master_json_2 TEXT
);

CREATE INDEX IF NOT EXISTS idx_unified_user ON unified_saves (LOWER(TRIM(user_email)));
CREATE INDEX IF NOT EXISTS idx_unified_save_id ON unified_saves (save_id);

-- Optionnel : RLS (Row Level Security) si tu veux isoler par user côté DB.
-- Ici on utilise la clé service_role côté app donc pas obligatoire.
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE audits ENABLE ROW LEVEL SECURITY;
-- etc.
