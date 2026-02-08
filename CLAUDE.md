# HOTARU — Architecture SaaS & Guide de développement

**Version doc :** 3.0.1 — 2026-02-08

---

## 1. Vision produit

HOTARU est une application **SaaS** d’audit et d’optimisation pour le web « lisible par l’IA » : crawl, scoring GEO, Authority Index, Master Data (JSON-LD entité), LEAF (JSON-LD par page). L’app est conçue pour évoluer en multi-utilisateurs et multi-tenant (isolation stricte des données par utilisateur).

**Design :** Noir + rouge `rgb(168, 27, 35)`, fond blanc. Titres de section harmonisés (format `XX / TITRE`, rouge, souligné). Deux couleurs principales sur tout le dashboard.

---

## 2. Logique SaaS (obligatoire)

### 2.1 Authentification

- **Entrée :** `core.auth.AuthManager` — login par email + mot de passe, stockage du hash (SHA-256) dans Google Sheets (onglet `users`).
- **Session :** Après login, `st.session_state` contient :
  - `authenticated` (bool)
  - `user_email` (str) — **identifiant utilisateur** pour toute l’isolation
  - `user_role` (`admin` | `user`) — pour stats globales / admin plus tard
- **Clés centralisées :** `core.session_keys` (`SESSION_AUTHENTICATED`, `SESSION_USER_EMAIL`, `SESSION_USER_ROLE`) pour cohérence du code.

### 2.2 Isolation des données (Data Isolation)

- **Règle :** Un utilisateur ne voit et ne modifie **que ses propres données**.
- **Audits :** `core.database.AuditDatabase.load_user_audits(user_email)` filtre **strictement** sur `user_email` (colonne 2 du sheet `audits`). Aucune ligne d’un autre utilisateur ne doit être retournée.
- **Sauvegarde :** `save_audit(..., user_email, ...)` enregistre toujours l’`user_email` de la session.
- **Futur :** Toute nouvelle table (workspaces, exports, etc.) devra avoir une colonne `user_email` (ou `user_id`) et toutes les requêtes devront filtrer dessus.

### 2.3 Rôles

- **user :** Accès à ses propres audits, projets, données.
- **admin :** Idem + (à implémenter) statistiques globales, gestion des utilisateurs, paramètres plateforme. Vérifier `session_keys.is_admin()` avant d’afficher ou d’exécuter des actions admin.

---

## 3. Structure du projet

```
PROJET_HOTARU_V2/
├── app.py                      # Point d’entrée : auth, header, tabs principaux, footer
├── assets/
│   ├── logo.png
│   └── style.css               # Design system (noir, rouge, section-title, step-badge, etc.)
├── core/
│   ├── auth.py                 # AuthManager (Google Sheets users, login/register/change_password)
│   ├── database.py             # AuditDatabase (audits : load_user_audits, save_audit) — filtré par user_email
│   ├── session_keys.py         # Constantes de session SaaS (SESSION_USER_EMAIL, etc.)
│   ├── scraping.py             # SmartScraper (crawl, patterns)
│   └── ai_clustering.py        # Renommage de clusters (Mistral)
├── engine/
│   ├── master_handler.py       # MasterDataHandler, Wikidata + Mistral
│   ├── dynamic_handler.py      # Prédictions Mistral (LEAF)
│   └── template_builder.py     # Génération JSON-LD
├── modules/
│   ├── home.py                 # Page d’accueil + note de version
│   ├── audit_geo.py            # Audit GEO (workspace en haut, onglets Audit Site | Méthodologie)
│   ├── authority_score.py      # Authority Score (onglets Analyse | Méthodologie)
│   ├── master.py               # Master Data (onglets Données | Méthodologie)
│   ├── leaf.py                 # LEAF Builder (onglets Builder | Méthodologie)
│   ├── methodologie_blocks.py  # Contenu Méthodologie réutilisable (authority, master, leaf)
│   └── geo_scoring.py          # Scoring GEO (sous-module)
├── requirements.txt
├── README.md
└── CLAUDE.md                   # Ce fichier
```

---

## 4. Navigation et onglets

### 4.1 Tabs principaux (app.py)

- **Home** — Présentation, modules, note de version.
- **Audit** — Crawl, graphe, rapports, archives (workspace en haut de page).
- **Authority Score** — AI Authority Index (5 piliers).
- **Master** — Données d’entité, JSON-LD Organization.
- **Leaf** — JSON-LD par page, prédictions IA.

### 4.2 Sous-onglets « Méthodologie » (par module)

Chaque module métier expose **deux sous-onglets** pour garder une structure homogène et documenter la méthode :

| Module        | Onglet 1      | Onglet 2      |
|---------------|---------------|---------------|
| Audit         | Audit Site    | Méthodologie  |
| Authority     | Analyse       | Méthodologie  |
| Master        | Données       | Méthodologie  |
| Leaf          | Builder       | Méthodologie  |

- **Audit (Méthodologie) :** Contenu dédié dans `audit_geo.render_methodologie()` (framework 2026, critères, scoring, directives).
- **Authority / Master / Leaf (Méthodologie) :** Contenu commun par module dans `modules.methodologie_blocks.render_methodologie_for_module(module_key)` avec `module_key` ∈ `["authority", "master", "leaf"]`.

---

## 5. Base de données (Google Sheets)

- **Onglet `users` :** email, password_hash, created_at, last_login, role. (Pas de `api_vault` pour l’instant ; clés API via `st.secrets`.)
- **Onglet `audits` :** audit_id, user_email, workspace, date, site_url, nb_pages, data_compressed, nom_site. **Filtrage obligatoire par `user_email`** dans `load_user_audits`.

---

## 6. Sécurité et évolution SaaS

- **Secrets Streamlit :** `gcp_service_account`, `sheet_url`, `mistral.api_key`. Ne jamais commiter de secrets.
- **Vault (futur) :** Onglet Paramètres, stockage des clés API chiffrées par utilisateur (ex. colonne `api_vault` dans `users`), déchiffrement au login.
- **HTTPS / cookies :** En production, forcer HTTPS et sécuriser les cookies de session (configuration déploiement).

---

## 7. Conventions de code

- **Session :** Utiliser `core.session_keys` pour les clés (`SESSION_USER_EMAIL`, etc.) et `get_current_user_email()` / `is_authenticated()` / `is_admin()` si besoin.
- **Audits :** Toujours passer `user_email` depuis la session aux fonctions qui chargent ou sauvent des audits.
- **Titres de section :** Classe CSS `.section-title` (rouge, souligné). Format texte `XX / TITRE` pour cohérence (ex. `01 / ANALYSE`, `02 / DÉTAIL PAR PILIER`).
- **Version :** Mise à jour dans `app.py` (VERSION, BUILD_DATE) et note sur la Home à chaque livraison significative.

---

## 8. Roadmap SaaS

- **Court terme**
  - [x] Isolation stricte des audits par `user_email`.
  - [x] Centralisation des clés de session (`session_keys`) et usage de `get_current_user_email()` dans les modules.
  - [ ] Onglet **Paramètres** : profil utilisateur, changement de mot de passe (déjà en auth), préférences.
  - [ ] Vault : formulaire de saisie des clés API (Mistral, OpenAI), chiffrement et stockage en base (ex. colonne `api_vault` dans `users`), chargement au login.

- **Moyen terme**
  - [ ] Table **workspaces** (ou renforcement du champ workspace) : CRUD par utilisateur, partage optionnel (futur).
  - [ ] Rôle **admin** : dashboard stats globales (agrégats anonymisés), gestion des comptes (liste users, reset mot de passe, désactivation).
  - [ ] Limites d’usage par utilisateur / plan (ex. nombre d’audits par mois, pages crawlées max) avec stockage des quotas.

- **Long terme**
  - [ ] Multi-tenant avancé : organisations / équipes, facturation par espace.
  - [ ] API REST ou webhooks pour intégrations (export automatique, CI/CD).
  - [ ] Logs d’audit (qui a fait quoi, quand) pour conformité et support.

---

## 9. Résumé des actions récentes (audit externe)

- **Isolation SaaS :** `load_user_audits(user_email)` filtre désormais strictement sur `user_email` (correction critique).
- **Onglets Méthodologie :** Ajoutés dans Audit (déjà présent), Authority Score, Master et Leaf via sous-tabs et `methodologie_blocks`.
- **Session :** Centralisation des clés dans `core.session_keys` et utilisation dans `app.py`.
- **Design :** Titres harmonisés (noir + rouge), deux couleurs sur tout le dashboard.
- **Session :** Utilisation de `get_current_user_email()` dans le module Audit (alignement avec `session_keys`).

Ce document sert de référence pour toute évolution future en SaaS (multi-tenant, rôles, nouvelles tables, Vault, roadmap ci-dessus, etc.).
