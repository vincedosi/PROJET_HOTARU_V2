-- HOTARU - Module Sitemap Dynamique
-- À exécuter dans le SQL Editor du dashboard Supabase.

-- =============================================================================
-- 1. SITEMAP_PROJECTS (projets sitemap par workspace)
-- =============================================================================
CREATE TABLE IF NOT EXISTS sitemap_projects (
    id BIGSERIAL PRIMARY KEY,
    workspace TEXT NOT NULL DEFAULT 'Non classé',
    user_email TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    domain VARCHAR(255) NOT NULL,

    max_urls_geo INTEGER DEFAULT 500,
    exclude_content_types TEXT DEFAULT '[]',
    min_content_quality DECIMAL(3,2) DEFAULT 0.50,
    min_jsonld_quality DECIMAL(3,2) DEFAULT 0.50,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_project_name_per_workspace UNIQUE(workspace, name)
);

CREATE INDEX IF NOT EXISTS idx_sitemap_projects_workspace ON sitemap_projects(workspace);
CREATE INDEX IF NOT EXISTS idx_sitemap_projects_user ON sitemap_projects(LOWER(TRIM(user_email)));

-- =============================================================================
-- 2. SITEMAP_PAGES (pages crawlées par projet)
-- =============================================================================
CREATE TABLE IF NOT EXISTS sitemap_pages (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES sitemap_projects(id) ON DELETE CASCADE,

    url TEXT NOT NULL,
    content_type VARCHAR(100) DEFAULT 'page',

    has_jsonld BOOLEAN DEFAULT FALSE,
    jsonld_quality DECIMAL(3,2) DEFAULT 0,
    content_quality DECIMAL(3,2) DEFAULT 0,
    monthly_traffic INTEGER DEFAULT 0,
    backlinks INTEGER DEFAULT 0,

    last_modified TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'active',

    seo_priority DECIMAL(3,2) DEFAULT 0.50,
    geo_priority DECIMAL(3,2) DEFAULT 0.50,
    is_citable BOOLEAN DEFAULT FALSE,

    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_url_per_project UNIQUE(project_id, url)
);

CREATE INDEX IF NOT EXISTS idx_sitemap_pages_project ON sitemap_pages(project_id);
CREATE INDEX IF NOT EXISTS idx_sitemap_pages_citable ON sitemap_pages(project_id, is_citable);
CREATE INDEX IF NOT EXISTS idx_sitemap_pages_seo ON sitemap_pages(project_id, seo_priority DESC);
CREATE INDEX IF NOT EXISTS idx_sitemap_pages_geo ON sitemap_pages(project_id, geo_priority DESC);

-- =============================================================================
-- 3. SITEMAP_GENERATIONS (historique des générations)
-- =============================================================================
CREATE TABLE IF NOT EXISTS sitemap_generations (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES sitemap_projects(id) ON DELETE CASCADE,

    type VARCHAR(10) NOT NULL,
    urls_count INTEGER NOT NULL DEFAULT 0,

    xml_content TEXT,
    file_url TEXT,

    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    generated_by TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_sitemap_gen_project ON sitemap_generations(project_id, generated_at DESC);

-- =============================================================================
-- 4. TRIGGER updated_at
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_sitemap_projects_updated_at
    BEFORE UPDATE ON sitemap_projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sitemap_pages_updated_at
    BEFORE UPDATE ON sitemap_pages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 5. RAFRAICHIR LE CACHE POSTGREST
-- =============================================================================
NOTIFY pgrst, 'reload schema';
