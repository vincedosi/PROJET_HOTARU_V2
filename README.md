# HOTARU

**SaaS d'audit et d'optimisation pour le web lisible par l'IA**

HOTARU (luciole) est une application Streamlit : crawl, scoring GEO, Authority Index (AI-Native), Master Data (JSON-LD entité), **Analyse JSON-LD** (clustering DOM, graphe interactif, génération JSON-LD optimisé via Mistral AI, **fusion multi-clusters** à choix multiples, export Google Sheets), **Eco-Score** (AIO Impact Calculator). Multi-utilisateurs avec **isolation stricte par `user_email` et par workspace**.

**Interface :** Français uniquement.

---

## Vision produit

- **Audit** : **Audit GEO** (structure du site, graphe interactif, patterns d'URL, renommage IA Mistral ; **charger un audit en priorité** puis nouvelle analyse ; sauvegarde unifiée), **Authority Score** (AI Authority Index — 5 piliers), **Scraping** (diagnostic URL + logs JSON-LD / techno / Selenium).
- **JSON-LD** : **Master** (données d'entité Wikidata + Mistral, JSON-LD Organization, audit & gap, sauvegarde audits), **Analyse JSON-LD** (clustering DOM, nommage Mistral, graphe, génération JSON-LD Schema.org par cluster, **fusion manuelle à choix multiples** : sélection de X clusters puis fusion en un seul ; **charger depuis Google Sheets en premier** puis nouvelle analyse ; sauvegarde/chargement unifié + onglet jsonld legacy).
- **Eco-Score** : **AIO Efficiency** — calculatrice d'impact carbone (tokens, kWh, gCO₂), paramètres site, Big Numbers, graphique Plotly 12 mois.
- **Design :** Fond blanc, noir + rouge `rgb(168, 27, 35)`. Titres `XX / TITRE`, rouge souligné.

---

## Versioning

À **chaque push ou merge sur `main`** (pull request), mettre à jour **`version.py`** :
- `VERSION` : incrémenter si besoin
- `BUILD_DATE` : date/heure courantes (automatique au chargement)
- `RELEASE_NOTE` : mini description (affichée sur la Home)

L'app affiche **V {VERSION} // {BUILD_DATE}** dans le header et le footer.

---

## Structure du projet

```
PROJET_HOTARU_V2/
├── app.py                      # Point d'entrée : auth, header (workspace + déconnexion), 4 tabs, footer
├── version.py                  # VERSION + BUILD_DATE (à mettre à jour à chaque push/PR)
├── packages.txt                # Streamlit Cloud : chromium, chromium-driver
├── requirements.txt
├── assets/
│   ├── logo.png
│   └── style.css               # Design system (noir, rouge, section-title)
├── core/
│   ├── auth.py                 # AuthManager (Google Sheets users)
│   ├── database.py             # AuditDatabase (audits, jsonld, unified_saves)
│   ├── runtime.py              # get_secrets(), get_session() — agnostique UI
│   ├── session_keys.py         # SESSION_*, get_current_user_email(), is_authenticated()
│   └── scraping.py             # SmartScraper (crawl, Selenium, fetch_page)
├── engine/
│   ├── master_handler.py       # MasterDataHandler, Wikidata + Mistral
│   ├── dynamic_handler.py      # Prédictions Mistral (LEAF)
│   └── template_builder.py     # Génération JSON-LD
├── services/                   # Logique métier réutilisable (Streamlit + API)
│   └── jsonld_service.py       # cluster_pages, generate_optimized_jsonld, extract_dom_structure (sans st)
├── views/                      # UI Streamlit (découplée des modules)
│   ├── audit_geo.py            # Audit GEO (charger en priorité, puis 01 Nouvelle analyse)
│   ├── audit_scraping.py
│   ├── authority_score.py
│   ├── jsonld_analyzer.py      # Analyse JSON-LD (onglet Charger d'abord, fusion multi-select)
│   ├── master.py
│   ├── eco_impact.py
│   ├── off_page.py
│   ├── leaf.py
│   └── methodologie_blocks.py
├── modules/                    # Ré-exports vers views/ (lazy load depuis app.py)
│   ├── home.py
│   ├── audit/                  # render_audit_geo, etc. (importe views)
│   ├── jsonld/                 # render_master_tab, render_jsonld_analyzer_tab
│   └── eco/
├── api/
│   └── main.py                 # FastAPI : /audit/authority, /health (base pour future API)
└── README.md
```

---

## SaaS : authentification et isolation

- **Login :** `core.auth.AuthManager` — email + mot de passe, hash en Google Sheets (onglet `users`).
- **Session :** `core.session_keys` — `get_current_user_email()`, `is_authenticated()`. Stockage via `core.runtime.get_session()` (compatible Streamlit ou autre runtime).
- **Workspace :** Sélecteur dans le header (`audit_workspace_select`). Toutes les listes de sauvegardes (Audit GEO, Analyse JSON-LD) filtrent par **workspace courant** pour une logique SaaS multi-projets.
- **Isolation :**
  - `AuditDatabase.load_user_audits(user_email)` — audits filtrés par email.
  - `AuditDatabase.list_unified_saves(user_email, workspace=selected_ws)` — sauvegardes unifiées par email + workspace.
  - `AuditDatabase.load_unified(save_id, user_email)` — vérifie `user_email` avant de renvoyer les données.
- **Usage :** Toujours utiliser `get_current_user_email()` et le workspace de session pour lire/écrire les données.

---

## Sauvegardes unifiées (unified_saves) — source unique du dashboard

**Tout le dashboard** lit et écrit dans l'onglet **unified_saves** (workspaces, audits GEO, JSON-LD, MASTER).

- **Onglet GSheet :** `unified_saves`
- **Colonnes (27) :**  
  `save_id`, `user_email`, `workspace`, `site_url`, `nom_site`, `created_at`,  
  `crawl_pages_count`, `geo_score`, `geo_clusters_count`, `jsonld_models_count`,  
  `geo_stats_pages_crawled`, `geo_stats_links_discovered`, `geo_stats_links_filtered`,  
  `geo_stats_links_duplicate`, `geo_stats_errors`,  
  `geo_infra_1`…`4`,  
  `crawl_data_1`, `crawl_data_2`, `geo_data_1`, `geo_data_2`, `jsonld_data_1`, `jsonld_data_2`,  
  **`master_json_1`, `master_json_2`** (MASTER DATA, blocs ≤ 45k car.).
- **API DB :** `save_unified(…, master_json=)`, `list_unified_saves()`, `load_unified()`, `update_master_for_unified()`.
- **À ajouter dans le GSheet** si l'onglet avait 25 colonnes : **`master_json_1`**, **`master_json_2`** à la fin.

---

## Navigation et flux UX

- **Header :** Logo, version, **Projets (Workspace)**, déconnexion.
- **Onglets principaux :** Accueil | Audit | JSON-LD | Eco-Score.
- **Audit GEO :** En tête d’onglet Audit Site → **CHARGER UN AUDIT** (unifié ou anciennes archives), puis **01 / NOUVELLE ANALYSE** (URLs, limite, Selenium, lancer le crawl).
- **Analyse JSON-LD :** Premier onglet **Charger depuis Google Sheets** (sauvegardes unifiées filtrées par workspace + anciennes jsonld), second onglet **Nouvelle analyse**. Dans les résultats, **01 — Charger depuis Google Sheets** puis 02 Génération, 03 Export, 04 Enregistrer, 05 Télécharger.

---

## Analyse JSON-LD (détail)

1. **Clustering** : Structure HTML, pattern URL, contenu sémantique — seuil configurable. Tolérances variables (h1, article, h2/h3…).
2. **Interface :** Onglet **Charger depuis Google Sheets** en premier (liste à choix unique), puis **Nouvelle analyse** (URL, nombre de pages, seuil).
3. **Nommage Mistral** : nom + type Schema.org par cluster.
4. **Graphe interactif** : domaine → clusters → URLs (pyvis + networkx).
5. **Onglets résultats :** GRAPHE | TABLEAU | EXPORT | **FUSION** | Logs.
6. **Fusion manuelle :** **Liste à choix multiples** (multiselect) — sélection de 2 clusters ou plus, bouton **FUSIONNER** → un seul cluster (Mistral renomme). Plus de dropdown source/cible.
7. **Génération JSON-LD** : GÉNÉRER par cluster (Mistral), export ZIP, sauvegarde Google Sheets (unifié + onglet jsonld).
8. **Sauvegarde :** `save_unified()` uniquement (unified_saves). Chargement via `list_unified_saves` + `load_unified`.

---

## Base de données (Google Sheets)

- **Onglet `users` / `USERS` :** email, password_hash, created_at, last_login, role.
- **Onglet `audits` (legacy) :** audit_id, user_email, workspace, date, site_url, nb_urls, data_compressed, nom_site, master_json. (Legacy ; préférer unified_saves.)
- **Onglet `jsonld` (legacy) :** site_url, model_id, model_name, page_count, url_pattern, sample_urls, dom_structure, existing_jsonld, recommended_schema, optimized_jsonld, created_at, workspace, user_email. (Legacy ; sauvegarde unifiée complète en plus.)
- **Onglet `unified_saves` :** 27 colonnes (voir ci-dessus). **Source unique** : workspaces, audits, JSON-LD, MASTER.
- **Onglets `audits` / `jsonld` :** plus utilisés par le dashboard (legacy).

**Source de vérité :** Tout le dashboard lit et écrit uniquement dans **unified_saves**.  
 Le dash pointe vers **unified_saves** pour la liste des workspaces (header), le chargement/sauvegarde des audits (Audit GEO) et le chargement/sauvegarde JSON-LD (Analyse JSON-LD). L’onglet `audits` reste en lecture pour le fallback « anciennes archives » et pour l’onglet Master (liste + colonne master_json).

---

## Structure SaaS et préparation API

### Checklist SaaS

- **Isolation par `user_email`** : toutes les lectures/écritures DB utilisent `get_current_user_email()`.
- **Workspace** : listes de sauvegardes filtrées par `audit_workspace_select` ; sauvegarde avec workspace courant.
- **Session** : `core.session_keys` + `core.runtime` pour rester découplé de l’UI.

### Préparation API (future)

- **Couche `services/`** : `services/jsonld_service.py` — clustering, Mistral, génération JSON-LD **sans Streamlit**. Réutilisable par une API.
- **`api/main.py`** (FastAPI) : routes existantes `POST /audit/authority`, `GET /health`. Base pour ajouter d’autres routes (analyse JSON-LD, crawl, etc.).
- **Recommandation API :** Pour une API multi-tenant, passer **`user_email`** (et optionnellement **`workspace`**) en header ou dans le corps des requêtes (ou les déduire d’un JWT / API key), et les fournir à `AuditDatabase` et aux services. Ne jamais faire confiance au client pour l’isolation ; toujours filtrer côté serveur par `user_email` (et workspace si besoin).

---

## Installation

**Prérequis :** Python 3.9+, clé API Mistral, Google Sheets (users + audits/jsonld/unified_saves). Pour **Streamlit Cloud** : `packages.txt` (chromium, chromium-driver).

```bash
git clone https://github.com/vincedosi/PROJET_HOTARU_V2.git
cd PROJET_HOTARU_V2
pip install -r requirements.txt
streamlit run app.py
```

**Secrets (`.streamlit/secrets.toml` ou paramètres Cloud) :**

```toml
[mistral]
api_key = "..."

[gcp_service_account]
# JSON compte de service Google

sheet_url = "https://docs.google.com/spreadsheets/d/..."
SERPAPI_KEY = "..."  # Optionnel, Audit Externe
```

---

## Conventions de code

- **Session :** `core.session_keys` et `get_current_user_email()` pour les données utilisateur.
- **Scraping :** `core.scraping.SmartScraper(…)` ; `fetch_page(url)` pour HTTP simple.
- **Titres :** Classe `.section-title`, format `XX / TITRE`.
- **Version :** `version.py` mis à jour à chaque push.

---

## Design system

- **Couleurs :** Fond `#FFFFFF`, texte `#000000`, accent rouge `rgb(168, 27, 35)`, noir `#0f172a`.
- **Scores :** Vert / orange / rouge selon niveau.

---

## Roadmap

- [x] Navigation SaaS, isolation par user_email
- [x] Workspace (header) et filtre workspace sur toutes les sauvegardes (Audit GEO, JSON-LD)
- [x] Sauvegardes unifiées (onglet unified_saves, 25 colonnes décomposées, JSON brut)
- [x] Flux UX : charger en priorité, puis nouvelle analyse / scrape (Audit GEO, JSON-LD)
- [x] Analyse JSON-LD : fusion manuelle à choix multiples (multiselect)
- [x] SmartScraper, Audit GEO, Authority Score, Master, Analyse JSON-LD, Eco-Score
- [x] Analyse JSON-LD : génération JSON-LD optimisé Mistral, sauvegarde/chargement Sheets
- [ ] Onglet Paramètres (profil, préférences)
- [ ] Vault : clés API chiffrées par utilisateur
- [ ] Rôle admin (stats, gestion comptes)
- [ ] API REST étendue (user_email/workspace en entrée, routes analyse/crawl)

---

## Licence

MIT — libre d’utilisation et de modification.

**HOTARU** — *Éclairer votre SEO comme une luciole dans la nuit*
