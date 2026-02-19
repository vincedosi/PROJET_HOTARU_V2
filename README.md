# HOTARU

**SaaS d'audit et d'optimisation pour le web lisible par l'IA**

HOTARU (luciole) est une application Streamlit : crawl, scoring GEO, Authority Index (AI-Native), Master Data (JSON-LD entité), **Analyse JSON-LD** (clustering DOM, graphe interactif, génération JSON-LD optimisé via Mistral AI, **fusion multi-clusters** à choix multiples), **Sitemap Dynamique** (génération sitemaps SEO et GEO optimisés), **Eco-Score** (AIO Impact Calculator). Multi-utilisateurs avec **isolation par `user_email` et workspace**. **Deux backends au choix à la connexion :** Google Sheets ou **Supabase** (PostgreSQL). **Backoffice admin** (visible aux rôles admin) : gestion utilisateurs, rôles et accès par workspace.

**Interface :** Français uniquement.

---

## Vision produit

- **Audit** : **Audit GEO** (structure du site, graphe interactif, patterns d'URL, renommage IA Mistral ; **chargement et sauvegarde via la barre en haut** puis nouvelle analyse), **Authority Score** (AI Authority Index — 5 piliers), **Scraping** (diagnostic URL + logs JSON-LD / techno / Selenium).
- **JSON-LD** : **Master** (données d'entité Wikidata + Mistral, JSON-LD Organization, audit & gap), **Analyse JSON-LD** (clustering DOM, nommage Mistral, graphe, **traitement unitaire** (sélection nœud + optimisation Mistral + comparaison actuel/optimisé), **traitement en masse** (génération batch + validation par onglets), **comparaison visuelle gris/vert/rouge**, affichage du prompt Mistral, **fusion manuelle à choix multiples** ; chargement et sauvegarde **uniquement via la barre en haut**).
- **Sitemap Dynamique** : Génération de sitemaps **SEO** et **GEO** optimisés. Import CSV ou depuis données crawlées. Scoring par type de contenu, qualité JSON-LD, trafic, backlinks, fraîcheur. Prévisualisation, téléchargement XML, sauvegarde en base, historique des générations. Architecture API-ready (engine/strategies/xml_generator indépendants de Streamlit).
- **Eco-Score** : **AIO Efficiency** — calculatrice d'impact carbone (tokens, kWh, gCO₂), paramètres site, Big Numbers, graphique Plotly 12 mois.
- **Design :** Fond blanc, noir + rouge `rgb(168, 27, 35)`. Titres `XX / TITRE`, rouge souligné.

---

## Versioning (obligatoire)

**Toujours** mettre à jour **`version.py`** à chaque **merge** ou **pull request** (avant de merger ou de pousser sur `main`) :
- `VERSION` : incrémenter (ex. 3.0.53 → 3.0.54)
- `BUILD_DATE` : automatique au chargement (pas besoin de modifier)
- `RELEASE_NOTE` : courte description des changements (affichée sur la Home)

Règle : **pas de merge / pas de PR sans mise à jour de `version.py`.**

L'app affiche **V {VERSION} // {BUILD_DATE}** dans le header et le footer.

---

## Structure du projet

```
PROJET_HOTARU_V2/
├── app.py                      # Point d'entrée : auth (Sheets ou Supabase au choix), barre SaaS, 5 onglets + Backoffice (admin), footer
├── version.py                  # VERSION + BUILD_DATE (à mettre à jour à chaque push/PR)
├── packages.txt                # Streamlit Cloud : chromium, chromium-driver
├── requirements.txt
├── assets/
│   ├── logo.png
│   └── style.css               # Design system (noir, rouge, section-title)
├── core/
│   ├── auth.py                 # AuthManager (Google Sheets)
│   ├── auth_supabase.py        # AuthManager (Supabase)
│   ├── database.py             # AuditDatabase (Google Sheets : audits, jsonld, unified_saves, user_workspace_access)
│   ├── database_supabase.py    # AuditDatabase (Supabase / PostgreSQL)
│   ├── runtime.py              # get_secrets(), get_session() — agnostique UI
│   ├── session_keys.py         # SESSION_*, get_current_user_email(), is_authenticated(), is_admin()
│   ├── mistral_utils.py        # get_mistral_key() — accès centralisé à la clé Mistral
│   ├── scraping.py             # SmartScraper V1 (crawl, Selenium, fetch_page)
│   ├── scraping_v2.py          # SmartScraperV2 (Crawl4AI / Playwright)
│   ├── selenium_utils.py       # Utilitaires Selenium (drivers, options)
│   ├── link_extractor.py       # Extraction de liens (HTML, sitemap, Markdown)
│   └── logger.py               # Logger centralisé (UI-agnostique)
├── engine/
│   ├── master_handler.py       # MasterDataHandler, Wikidata + Mistral
│   ├── dynamic_handler.py      # Prédictions Mistral (LEAF)
│   └── template_builder.py     # Génération JSON-LD
├── services/                   # Logique métier réutilisable (Streamlit + API)
│   ├── jsonld_service.py       # cluster_pages, generate_optimized_jsonld, extract_dom_structure (sans st)
│   └── jsonld_diff.py          # compute_jsonld_diff, extract_modified_fields, render_comparison_html
├── views/                      # UI Streamlit (découplée des modules)
│   ├── audit_geo.py            # Audit GEO (charger en priorité, puis 01 Nouvelle analyse)
│   ├── audit_scraping.py
│   ├── authority_score.py
│   ├── jsonld_analyzer.py      # Analyse JSON-LD (graphe, comparaison visuelle, batch processing, fusion)
│   ├── backoffice.py           # Backoffice admin (tabs) : Utilisateurs, Workspaces (CRUD), Accès
│   ├── master.py
│   ├── eco_impact.py
│   ├── off_page.py
│   ├── leaf.py
│   └── methodologie_blocks.py
├── modules/                    # Lazy imports vers views/ + logique métier
│   ├── home.py
│   ├── audit/                  # render_audit_geo, etc. (importe views)
│   ├── jsonld/                 # render_master_tab, render_jsonld_analyzer_tab
│   ├── sitemap/                # Module Sitemap Dynamique (SEO + GEO)
│   │   ├── strategies.py       # Scoring SEO/GEO, citabilité, changefreq (pur Python)
│   │   ├── xml_generator.py    # Génération XML sitemap (pur Python)
│   │   ├── engine.py           # SitemapEngine orchestrateur (pur Python)
│   │   ├── database.py         # SitemapDatabase CRUD Supabase
│   │   └── ui.py               # Interface Streamlit 5 sections
│   └── eco/
├── docs/
│   ├── supabase_schema.sql     # Schéma Supabase (users, audits, jsonld, unified_saves, user_workspace_access)
│   ├── supabase_sitemap.sql    # Schéma Sitemap (sitemap_projects, sitemap_pages, sitemap_generations)
│   ├── supabase_insert_first_user.sql   # Premier utilisateur (upsert)
│   ├── supabase_migration_workspace_access.sql
│   └── SUPABASE_SECRETS.md     # Config secrets Streamlit pour Supabase
├── api/
│   └── main.py                 # FastAPI : /audit/authority, /health (base pour future API)
└── README.md
```

---

## Moteur de scraping V2 (Crawl4AI / Playwright)

L’app propose deux moteurs : **V1 (Selenium)** et **V2 (Crawl4AI + Playwright)**. Par défaut V2 est sélectionné.

**Pour utiliser le moteur V2**, les binaires Playwright (Chromium) doivent être installés **une fois** après l’installation des dépendances Python :

```bash
# Après : pip install -r requirements.txt
playwright install chromium
```

- **En local / CI :** exécuter la commande ci‑dessus dans le même environnement que l’app.
- **Docker / déploiement :** ajouter dans votre image ou script de build :
  ```bash
  RUN playwright install chromium
  ```
  (ou `playwright install-deps` si vous installez les dépendances système séparément.)
- **Streamlit Community Cloud :** le build standard ne lance pas `playwright install`. Pour utiliser V2 en Cloud, déployer avec une image Docker qui exécute `playwright install chromium`, ou utiliser le moteur **V1** (Selenium) qui ne nécessite pas Playwright.

Si l’erreur « Executable doesn't exist at …/ms-playwright/… » s’affiche, exécuter `playwright install chromium` puis relancer l’app, ou passer sur **V1 — Selenium** dans l’interface.

---

## SaaS : authentification et isolation

- **Login :** Sur la page de connexion, choix **Google Sheets** ou **Supabase**. Puis email + mot de passe. Auth via `core.auth.AuthManager` (Sheets) ou `core.auth_supabase.AuthManager` (Supabase). Hash stocké en base (onglet `users` ou table `users`).
- **Session :** `core.session_keys` — `get_current_user_email()`, `is_authenticated()`, **`is_admin()`**. Stockage via `core.runtime.get_session()`. Le backend choisi à la connexion (`auth_backend` = `sheets` ou `supabase`) est conservé pour toute la session (sauvegardes et chargement).
- **Barre SaaS (en haut) :** Ligne 1 = **Choix du workspace** + DÉCONNEXION. Ligne 2 = **Choix de la sauvegarde** + **VALIDER** (charge la sauvegarde) + **SAUVEGARDER** (nouvelle version) + **ÉCRASER** (remplace la sauvegarde chargée sans nouvelle version) ; stockage dans unified_saves — Sheets ou Supabase selon le backend).
- **Isolation :**
  - `AuditDatabase` (Sheets ou Supabase selon session) : `list_unified_saves(user_email, workspace)`, `load_unified(save_id, user_email)`, `save_unified(...)`.
  - Si **droits workspace** sont définis en backoffice pour un user, il ne voit que les sauvegardes des workspaces auxquels il a accès.
- **Backoffice (admin uniquement) :** Onglet **Backoffice** visible si `is_admin()`. Gestion des utilisateurs (liste, ajout, suppression, changement de rôle), et **accès par workspace** par utilisateur (cases à cocher + Enregistrer accès).

---

## Sauvegardes unifiées (unified_saves) — source unique du dashboard

**Tout le dashboard** lit et écrit dans **unified_saves** (workspaces, audits GEO, JSON-LD, MASTER), soit dans **Google Sheets** (onglet `unified_saves`), soit dans **Supabase** (table `unified_saves`) selon le backend choisi à la connexion.

- **Google Sheets :** onglet `unified_saves`
- **Supabase :** table `unified_saves` (voir `docs/supabase_schema.sql`)
- **Colonnes / champs (27) :**  
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

- **Header :** Logo, version, **barre SaaS** (2 lignes), déconnexion.
- **Onglets principaux :** Accueil | Audit | JSON-LD | **Sitemap** | Eco-Score. **Backoffice** (visible uniquement aux rôles admin) : gestion utilisateurs, rôles et accès par workspace.
- **Audit GEO :** En tête d’onglet Audit Site → 01 / NOUVELLE ANALYSE (URLs, limite, Selenium).
- **Analyse JSON-LD :** Chargement/sauvegarde via la barre en haut. Onglet Nouvelle analyse ; résultats : 02 Génération, 03 Export, 05 Télécharger.
- **Master :** Chargement/sauvegarde via la barre en haut (VALIDER charge tout ; SAUVEGARDER enregistre tout).

---

## Analyse JSON-LD (détail)

1. **Clustering** : Structure HTML, pattern URL, contenu sémantique — seuil configurable. Tolérances variables (h1, article, h2/h3…).
2. **Interface :** Chargement/sauvegarde **uniquement via la barre en haut**. Dans l'onglet : **Nouvelle analyse** (URL, nombre de pages, seuil).
3. **Nommage Mistral** : nom + type Schema.org par cluster.
4. **Graphe interactif** : domaine → clusters → URLs (pyvis + networkx).
5. **Onglets résultats :** GRAPHE | TABLEAU | EXPORT | **FUSION** | Logs.
6. **Fusion manuelle :** **Liste à choix multiples** (multiselect) — sélection de 2 clusters ou plus, bouton **FUSIONNER** → un seul cluster (Mistral renomme). Plus de dropdown source/cible.
7. **Génération JSON-LD** : GÉNÉRER par cluster (Mistral), export ZIP. Sauvegarde : bouton **SAUVEGARDER** en haut (unified_saves).
8. **Chargement / sauvegarde :** Uniquement via la **barre en haut** (Choix de la sauvegarde → VALIDER ; SAUVEGARDER).

---

## Base de données

**Deux backends possibles**, choisis à la connexion : **Google Sheets** ou **Supabase (PostgreSQL)**.

### Google Sheets

- **Onglet `users` :** email, password_hash, created_at, last_login, role.
- **Onglet `audits` (legacy) :** audit_id, user_email, workspace, date, site_url, nb_urls, data_compressed, nom_site, master_json.
- **Onglet `jsonld` (legacy) :** site_url, model_id, model_name, page_count, url_pattern, sample_urls, dom_structure, existing_jsonld, recommended_schema, optimized_jsonld, created_at, workspace, user_email.
- **Onglet `unified_saves` :** 27 colonnes — source unique du dashboard (workspaces, audits, JSON-LD, MASTER).
- **Onglet `user_workspace_access` :** user_email, workspace_name (droits par workspace, créé automatiquement si absent).

### Supabase (PostgreSQL)

Tables : `users`, `audits`, `jsonld`, `unified_saves`, `user_workspace_access`, **`sitemap_projects`**, **`sitemap_pages`**, **`sitemap_generations`**. Schéma complet : **`docs/supabase_schema.sql`**. Premier utilisateur : **`docs/supabase_insert_first_user.sql`**. Migration droits seuls : **`docs/supabase_migration_workspace_access.sql`**. Configuration des secrets : **`docs/SUPABASE_SECRETS.md`**.

### Comportement commun

**Source de vérité :** Le dashboard lit et écrit dans **unified_saves** (Sheets ou Supabase selon la session). Chargement/sauvegarde uniquement via la **barre SaaS en haut** (Choix workspace, Choix sauvegarde, VALIDER, SAUVEGARDER).

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

**Prérequis :** Python 3.9+, clé API Mistral. Backend au choix : **Google Sheets** (gcp_service_account + sheet_url) ou **Supabase** (supabase_url + supabase_service_role_key). Pour **Streamlit Cloud** : `packages.txt` (chromium, chromium-driver).

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

# Option 1 : Google Sheets (connexion avec "Google Sheets" sur la page de login)
[gcp_service_account]
# JSON compte de service Google
sheet_url = "https://docs.google.com/spreadsheets/d/..."

# Option 2 : Supabase (connexion avec "Supabase" sur la page de login)
[supabase]
supabase_url = "https://xxxx.supabase.co"
supabase_service_role_key = "eyJ..."

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
- [x] Sauvegardes unifiées (onglet unified_saves, 27 colonnes dont master_json_1/2)
- [x] Barre SaaS unique en haut : Choix workspace, Choix sauvegarde, VALIDER, SAUVEGARDER (sur toutes les pages)
- [x] Flux UX : chargement/sauvegarde uniquement via la barre en haut ; nouvelle analyse dans chaque onglet
- [x] Analyse JSON-LD : fusion manuelle à choix multiples (multiselect)
- [x] SmartScraper, Audit GEO, Authority Score, Master, Analyse JSON-LD, Eco-Score
- [x] Analyse JSON-LD : génération JSON-LD optimisé Mistral, sauvegarde/chargement Sheets
- [x] Backend Supabase (auth + unified_saves + chargement liste)
- [x] Backoffice admin : gestion utilisateurs, rôles, accès par workspace (onglet visible si admin)
- [x] Backoffice tabs : CRUD workspaces Supabase (créer, renommer, déplacer saves)
- [x] Fix scraping premier clic (on_click callback)
- [x] Comparaison JSON-LD visuelle (gris identique / vert ajouté-enrichi / rouge supprimé)
- [x] Affichage du prompt Mistral (transparence + debug)
- [x] Traitement en masse : batch generation + validation nœud par nœud (rollback)
- [x] Sauvegarde delta Supabase (champs modifiés uniquement)
- [x] Détail cluster sous le schéma des nœuds (layout pleine largeur)
- [x] Onglet Traitement unitaire (sélection nœud + optimisation Mistral + comparaison)
- [x] Validation en masse par onglets (plus d'accordéons)
- [x] Audit code complet : centralisation Mistral (`core/mistral_utils.py`), fix dépendances circulaires, lazy imports modules, pydantic dans requirements, fix bare except, fix `soup.title.string`, error handling restauration JSON-LD
- [x] Module Sitemap Dynamique (SEO + GEO, import CSV, scoring, preview, historique, XML)
- [x] Bouton ÉCRASER (mise à jour sauvegarde existante sans nouvelle version)
- [x] Master Data et JSON-LD Master intégrés dans les sauvegardes et restaurés au chargement
- [x] Suppression workspace avec confirmation et déplacement des sauvegardes
- [x] Fallback création workspace (unified_saves) si table user_workspace_access absente
- [x] Fix parse Mistral JSON-LD (nettoyage balises script/markdown)
- [ ] Onglet Paramètres (profil, préférences)
- [ ] Vault : clés API chiffrées par utilisateur
- [ ] API REST étendue (user_email/workspace en entrée, routes analyse/crawl)

---

## Licence

MIT — libre d’utilisation et de modification.

**HOTARU** — *Éclairer votre SEO comme une luciole dans la nuit*
