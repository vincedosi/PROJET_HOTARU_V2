# Backend Supabase — option à la connexion

Sur la **page de connexion**, tu peux choisir : **Google Sheets** (par défaut) ou **Supabase**. Une fois Supabase validé, tu pourras supprimer l’option Google Sheets.

## 1. Créer le projet Supabase

- Va sur [supabase.com](https://supabase.com), crée un projet.
- Dans **Settings → API** : note l’**URL** du projet et la clé **service_role** (secret, pour le backend).

## 2. Créer les tables

Dans le **SQL Editor** Supabase, exécute le fichier :

- `docs/supabase_schema.sql`

(une seule fois par projet)

## 3. Secrets Streamlit (pour l’option Supabase)

Dans **Streamlit Cloud** (Settings → Secrets) ou en local dans `.streamlit/secrets.toml`, ajoute **uniquement si tu utilises l’option Supabase** :

```toml
supabase_url = "https://xxxx.supabase.co"
supabase_service_role_key = "eyJhbGc..."
```

Tu peux aussi utiliser `supabase_key` au lieu de `supabase_service_role_key`.  
Aucun `backend` dans les secrets : le choix se fait sur la page de connexion (radio « Connexion avec : Google Sheets | Supabase »).

## 4. Premier utilisateur

Après avoir exécuté le schéma, la table `users` est vide. Tu peux :

- Soit t’inscrire via l’app si tu as une route d’inscription / un admin qui crée les comptes.
- Soit insérer un utilisateur à la main dans Supabase (Table Editor → `users`) avec un `email` et un `password_hash` (SHA-256 du mot de passe en hex). Exemple en Python :  
  `hashlib.sha256(b"ton_mot_de_passe").hexdigest()`  
  et mettre `role = "admin"` si besoin.

## 5. Comportement

- À la **connexion**, l’utilisateur choisit **Google Sheets** ou **Supabase**. Ce choix est gardé pour toute la session (sauvegardes, chargement, etc.).
- **Google Sheets** : comme avant (secrets `gcp_service_account`, `sheet_url`).
- **Supabase** : auth et base via Supabase (secrets `supabase_url`, `supabase_service_role_key`).

Quand Supabase te convient, tu pourras retirer l’option Google Sheets de la page de connexion et le code associé.
