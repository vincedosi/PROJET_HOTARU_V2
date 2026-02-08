# 🏮 PROJECT HOTARU V3 - MASTER INSTRUCTIONS (SaaS & Smart Architecture)

---

## 1. VISION & DESIGN SYSTEM ("ZEN JAPONAIS" / BRUTALIST)

**Philosophie :** Minimalisme radical. Tout ce qui n'est pas essentiel disparaît.

**Palette :** Fond 100% Blanc (#FFFFFF), Textes et Lignes Noir Pur (#000000).

**Composants :**
- **Boutons :** Fond blanc, bordure noire fine (1px), texte noir. Inversion noir/blanc au survol. (Implémenté en **carré** dans `assets/style.css` : `border-radius: 0`.)
- **Inputs :** Contours fins (1px solid var(--border-light)), style underline / focus noir.
- **Sidebar :** Fond blanc, bordure droite noire (CSS présent ; sidebar Streamlit est collapsed par défaut dans `app.py`).
- **Layout :** Navigation par **onglets (Tabs)** en zone principale : Home, Audit, Authority Score, Master, Leaf.

**Fichiers :** `app.py` (router), `assets/style.css` (design system), `assets/logo.png` (logo).

---

## 2. NAVIGATION & SÉCURITÉ (SaaS)

### A. Structure actuelle (implémentée)

- **Authentification :** Page login (email + mot de passe), puis session. Déconnexion via bouton LOGOUT en haut à droite.
- **Pas de sidebar menu.** Zone principale :
  - **Header** : Logo 蛍 + HOTARU, version (V 3.0.0), bouton LOGOUT.
  - **Tabs :** Home | Audit | Authority Score | Master | Leaf.
- **Pied de page :** HOTARU ENTITY FORGE V2, version, build.

**Cible spec (non implémentée telle quelle) :** Sidebar avec menu 🔍 AUDIT GEO, 🛠️ TRANSFORMATION, ⚙️ PARAMÈTRES, et pied de page sidebar avec avatar + Déconnexion.

### B. Gestion des données (Data Isolation)

- **Auth :** `core/auth.py` — Google Sheets onglet `users` (email, password_hash, created_at, last_login, role). Filtrage par email en session (`st.session_state.user_email`).
- **Audits :** `core/database.py` — Onglet `audits`. `load_user_audits(user_email)` et `save_audit(...)` filtrent / enregistrent par `user_email`. Pas de colonne `user_id` (on utilise l’email).
- **Admin :** Le rôle `role` est stocké en session (`st.session_state.user_role`) ; logique "admin voit stats globales" à brancher si besoin.

### C. Le "Vault" (Clés API) — **NON IMPLÉMENTÉ**

- **Actuel :** Clés API (Mistral, etc.) lues uniquement via **Streamlit secrets** : `st.secrets["mistral"]["api_key"]`. Aucun onglet Paramètres, pas de colonne `api_vault` dans la table `users`.
- **Spec :** Onglet Paramètres avec formulaire (Mistral, OpenAI) → chiffrement → stockage dans colonne `api_vault` (Google Sheets) → déchiffrement au login et chargement en session.

---

## 3. CŒUR DU SYSTÈME : AUDIT GEO & SMART ARCHITECT

### État implémenté

- **Crawl / Scraper :** `core/scraping.py` — `SmartScraper` :
  - Multi-URLs de départ, même domaine.
  - Crawl par liens internes (pas de "Sitemap First" dans ce module ; `modules/authority_score.py` utilise sitemap pour son propre flux).
  - Détection SPA/React → bascule Selenium si besoin.
  - `analyze_patterns(pages)` : regroupement par **premier segment de chemin** (ex. `/blog`, `/produit`), avec comptage et échantillons.
- **Renommage IA :** `core/ai_clustering.py` — `get_naming_prompt()`, `analyze_clusters_with_mistral(cluster_data)` : envoi des groupes à Mistral, parsing ligne par ligne (ID: Nom). **Non branché** dans `modules/audit_geo.py` (audit_geo utilise `_call_mistral` pour robots.txt, analyses texte, etc., mais pas pour le renommage des clusters du graphe).
- **Audit GEO :** `modules/audit_geo.py` — Crawl (SmartScraper), vérifs (robots, meta, sitemap mention, etc.), graphe (pyvis/networkx), sauvegarde / chargement d’audits via `core/database.py`. Pas de "Smart Architect" unifié (sitemap first + clustering regex + Mistral renaming) dans ce module.

### Spec Phase 1 "Smart Architect" (objectif)

- **A. Découverte :** Sitemap First, sinon crawl liens. Pattern matching (regex) sur URLs → clusters virtuels. Smart sampling : si cluster > 5 pages, garder 3 spécimens pour l’IA.
- **B. Renommage :** Mistral pour un nom de catégorie par groupe (ex. "Fiches Produits", "Blog"). Nœud du graphe = "📦 Fiches Produits (540 pages)".
- **C. UX :** Graphe interactif (fond blanc, nœuds rectangulaires), clic → panneau avec URLs échantillons ; expander "Journal d’activité" avec logs type [INFO] / [IA].

---

## 4. DATABASE & VERSIONING (Google Sheets)

### Schéma actuel

- **Table `users` (auth) :** email, password_hash, created_at, last_login, role. (Pas de colonne api_vault.)
- **Table `audits` :** audit_id, user_email, workspace, date, site_url, nb_pages, data_compressed, nom_site. (`data_compressed` = JSON des résultats compressé en base64/zlib.)

**Save/Load :** Bouton "Sauvegarder l’architecture" dans l’audit ; tableau des audits passés avec "Charger" (dashboard dans l’onglet Audit). Implémenté dans `audit_geo.py` + `database.py`.

**Spec :** Colonnes audit_id, user_id, site_url, timestamp, graph_data_json (compressé), status (Structure Only / Scored). En pratique : user_email au lieu de user_id, pas de colonne status.

---

## 5. STRUCTURE DU PROJET (scan du code)

```
PROJET_HOTARU_V2/
├── app.py                 # Point d’entrée : auth, header, tabs, injection CSS
├── assets/
│   ├── logo.png
│   └── style.css          # Design system Brutalist (monochrome, Inter, bordures 1px)
├── core/
│   ├── auth.py            # AuthManager (Google Sheets users, login/register/change_password)
│   ├── database.py        # AuditDatabase (audits : save/load par user_email)
│   ├── scraping.py       # SmartScraper (crawl, analyze_patterns par path)
│   └── ai_clustering.py   # Renommage clusters via Mistral (non branché dans audit_geo)
├── engine/
│   ├── master_handler.py  # MasterDataHandler, enrichissement Wikidata + Mistral
│   ├── dynamic_handler.py # DynamicDataHandler (prédictions Mistral pour LEAF)
│   └── template_builder.py
├── modules/
│   ├── home.py            # Landing / dashboard (présentation des 4 modules)
│   ├── audit_geo.py       # Audit GEO (crawl, graphe, save/load, robots/LLM)
│   ├── authority_score.py # AI Authority Index (5 piliers, sitemap utilisé ici)
│   ├── geo_scoring.py
│   ├── master.py          # Master Data (Wikidata + Mistral, JSON-LD entité)
│   └── leaf.py            # Leaf Builder (JSON-LD par page, Mistral)
├── requirements.txt
├── README.md
└── CLAUDE.md              # Ce fichier
```

**Secrets attendus (Streamlit) :** `gcp_service_account`, `sheet_url`, `mistral.api_key`.

---

## 6. INSTRUCTIONS DE CODAGE (priorités)

| Élément | État | Action |
|--------|------|--------|
| Architecture app.py + CSS | ✅ Fait | — |
| Navigation (tabs) | ✅ Fait | Optionnel : ajouter sidebar menu (AUDIT GEO, TRANSFORMATION, PARAMÈTRES) si souhaité |
| Vault (clés API en GSheets) | ❌ Non fait | Ajouter onglet Paramètres, colonne api_vault dans users, chiffrement/déchiffrement au login |
| Data isolation (user_email) | ✅ Fait | — |
| Core Scraper (crawl + patterns) | ✅ Fait | Optionnel : "Sitemap First" dans scraping ou audit_geo |
| AI Engine (renommage catégories) | ✅ Code prêt dans ai_clustering | Brancher dans audit_geo (clusters → Mistral → labels graphe) |
| Save/Load audits | ✅ Fait | — |

**EXÉCUTION recommandée :** 1) Vault (Paramètres + api_vault) si besoin de ne plus dépendre des secrets par déploiement. 2) Brancher `ai_clustering.analyze_clusters_with_mistral` dans le flux Audit GEO pour le Smart Architect (renommage des nœuds du graphe).
