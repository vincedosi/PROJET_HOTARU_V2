-- Migration : ajouter la table user_workspace_access (backoffice droits).
-- À exécuter si vous aviez déjà créé le schéma avant l’onglet Backoffice.

CREATE TABLE IF NOT EXISTS user_workspace_access (
  id BIGSERIAL PRIMARY KEY,
  user_email TEXT NOT NULL,
  workspace_name TEXT NOT NULL,
  UNIQUE(user_email, workspace_name)
);

CREATE INDEX IF NOT EXISTS idx_user_workspace_user ON user_workspace_access (LOWER(TRIM(user_email)));
