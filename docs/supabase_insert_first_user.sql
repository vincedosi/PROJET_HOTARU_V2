-- Premier utilisateur HOTARU (à exécuter dans le SQL Editor Supabase après le schéma)
-- Remplace 'MotDePasse123' par ton mot de passe, puis Run.
-- Si l'utilisateur existe déjà, son mot de passe sera mis à jour.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO users (email, password_hash, created_at, last_login, role)
VALUES (
  'admin@hotaru.app',
  encode(digest('MotDePasse123', 'sha256'), 'hex'),
  to_char(now(), 'YYYY-MM-DD'),
  '',
  'admin'
)
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role = 'admin';
