# HOTARU

**SaaS d'audit et d'optimisation pour le web lisible par l'IA**

HOTARU (luciole) est une application Streamlit : crawl, scoring GEO, Authority Index (AI-Native), Master Data (JSON-LD entité), **Analyse JSON-LD** (clustering DOM intelligent, graphe interactif, génération JSON-LD optimisé via Mistral AI, fusion manuelle des clusters, export Google Sheets), **Eco-Score** (AIO Impact Calculator). Multi-utilisateurs avec isolation stricte des données par utilisateur.

**Interface :** Français uniquement.

---

## Vision produit

- **Audit** : 3 sous-onglets — **Audit GEO** (structure du site, graphe interactif, patterns d'URL, renommage IA Mistral ; 3 tabs : Audit Site | Audit Externe | Méthodologie), **Authority Score** (AI Authority Index v2 — 5 piliers : Ancrage Knowledge Graph, Interopérabilité des Données, Autorité de Citation, Densité Vectorielle, Fraîcheur ; embeddings + sameAs), **Scraping** (diagnostic URL + logs JSON-LD / techno / Selenium).
- **JSON-LD** : 2 sous-onglets — **Master** (données d'entité Wikidata + Mistral, JSON-LD Organization, audit & gap, sauvegarde audits), **Analyse JSON-LD** (clustering DOM intelligent, nommage Mistral, graphe interactif, génération JSON-LD Schema.org optimisé par cluster, **fusion manuelle des clusters**, indicateur variabilité DOM, sauvegarde/chargement Google Sheets).
- **Eco-Score** : **AIO Efficiency** — calculatrice d'impact carbone (tokens, kWh, gCO₂), paramètres site (pages catalogue, vues/jour) dans un expander, Big Numbers annuels, graphique Plotly 12 mois, méthodologie scientifique.
- **Design :** Fond blanc, noir + rouge `rgb(168, 27, 35)`. Titres de section au format `XX / TITRE`, rouge souligné.

---

## Versioning

À **chaque push ou merge sur `main`** (pull request), mettre à jour **`version.py`** :
- `VERSION` : incrémenter si besoin (ex. 3.0.32 → 3.0.33)
- `BUILD_DATE` : heure système au chargement de l'app (automatique)
- `RELEASE_NOTE` : mini description des changements (affichée dans le cartouche Home)

L'app affiche **V {VERSION} // {BUILD_DATE}** dans le header et le footer. Un cartouche sur la Home affiche version, date/heure et description.

---

## Structure du projet

```
PROJET_HOTARU_V2/
├── app.py                      # Point d'entrée : auth, header, 4 tabs, footer
├── version.py                  # VERSION + BUILD_DATE (à mettre à jour à chaque push/PR)
├── packages.txt                # Streamlit Cloud : chromium, chromium-driver
├── requirements.txt            # Python deps (selenium, tiktoken, trafilatura, pyvis, networkx, etc.)
├── assets/
│   ├── logo.png
│   └── style.css               # Design system (noir, rouge, section-title)
├── core/
│   ├── auth.py                 # AuthManager (Google Sheets users)
│   ├── database.py             # AuditDatabase (audits, Master, jsonld : save/load/list)
│   ├── session_keys.py         # Clés de session SaaS
│   ├── scraping.py             # SmartScraper (crawl, Selenium Streamlit Cloud, fetch_page)
│   └── ai_clustering.py        # Renommage clusters (Mistral)
├── engine/
│   ├── master_handler.py        # MasterDataHandler, Wikidata + Mistral, heuristiques
│   ├── dynamic_handler.py      # Prédictions Mistral (LEAF)
│   └── template_builder.py     # Génération JSON-LD
├── services/                    # Logique métier réutilisable (Streamlit + API)
│   ├── __init__.py
│   └── jsonld_service.py       # Clustering, Mistral, génération JSON-LD (sans Streamlit)
├── docs/
│   └── CLAUDE.md               # Référence agent (voir README)
├── modules/
│   ├── home.py                 # Page d'accueil
│   ├── audit/                  # Onglet Audit (GEO, Authority, Scraping, Off-Page)
│   │   ├── __init__.py
│   │   ├── audit_geo.py         # Audit GEO (workspace, Audit Site | Externe | Méthodologie)
│   │   ├── audit_scraping.py   # Scraping debug (URL, logs JSON-LD, techno, Selenium)
│   │   ├── authority_score.py  # Authority Score AI-Native (5 piliers)
│   │   ├── off_page.py         # Audit Externe (réputation, Audit Miroir)
│   │   └── geo_scoring.py      # Scoring GEO
│   ├── jsonld/                 # Onglet JSON-LD (Master, Analyse JSON-LD)
│   │   ├── __init__.py
│   │   ├── master.py           # Master Data (Wikidata/INSEE, audit gap, JSON-LD)
│   │   ├── jsonld_analyzer.py  # Analyse JSON-LD (clustering, Mistral, graphe, fusion manuelle)
│   │   ├── leaf.py             # Leaf Builder (JSON-LD par page)
│   │   └── methodologie_blocks.py  # Contenu Méthodologie (Authority, Master)
│   └── eco/                    # Onglet Eco-Score
│       ├── __init__.py
│       └── eco_impact.py        # AIO Impact Calculator (tokens, kWh, gCO₂, Plotly)
└── README.md                   # Ce fichier
```

---

## SaaS : authentification et isolation

- **Login :** `core.auth.AuthManager` — email + mot de passe, hash en Google Sheets (onglet `users`).
- **Session :** `st.session_state` avec clés dans `core.session_keys` (`authenticated`, `user_email`, etc.).
- **Isolation :** `AuditDatabase.load_user_audits(user_email)` filtre strictement par `user_email`.
- **Usage :** `get_current_user_email()`, `is_authenticated()` depuis `core.session_keys`.

---

## Navigation

**Onglets principaux (app.py) :** Accueil | Audit | JSON-LD | Eco-Score — onglets classiques (st.tabs).

- **Header** : logo, version, workspace, déconnexion.
- **Audit** : sous-onglets **Audit GEO**, **Authority Score**, **Scraping**.
- **JSON-LD** : sous-onglets **Master**, **Analyse JSON-LD**.
- **Eco-Score** : AIO Efficiency (paramètres site dans expander, Big Numbers, graphique 12 mois).
- Méthodologie par module : dédiée (Audit GEO, Off-Page, Eco) ou `methodologie_blocks.render_methodologie_for_module("authority"|"master")`.

---

## Analyse JSON-LD

Module dédié à la détection des types de pages par structure DOM et pattern d'URL :

1. **Clustering intelligent** : Structure HTML 40 %, Pattern URL 30 %, Contenu sémantique 30 % — seuil 85 %. **Tolérances variables** : balises structurelles (h1, article, section, form, table) ±20 %, balises de contenu (h2, h3) ±60 % pour regrouper les fiches métiers malgré des variations de contenu.
2. **Interface** : URL, slider pages (50–500), bouton Lancer l'analyse, bouton Effacer les résultats.
3. **Nommage Mistral** : chaque cluster reçoit un nom et un type Schema.org recommandé.
4. **Graphe interactif** : domaine → clusters → URLs exemples (pyvis + networkx). Nœuds colorés : domaine noir, chaque cluster couleur distincte, pages gris clair.
5. **Onglets** : GRAPHE (détail cluster sélectionné, dropdown) | TABLEAU (tabs par cluster) | EXPORT | Logs.
6. **Indicateur variabilité DOM** : affichage "H2: 8-16" dans l'onglet DOM pour les clusters avec plusieurs pages (variation normale du contenu).
7. **Fusion manuelle** : dans "Actions avancées", l'utilisateur peut fusionner deux clusters (ex: "Fiches métiers" + "Offres d'emploi") — Mistral renomme le cluster fusionné.
8. **Génération JSON-LD optimisé** : bouton **GÉNÉRER** dans le panneau détails. Mistral AI analyse la structure DOM et génère un JSON-LD Schema.org complet. Messages d'erreur détaillés (timeout, parse, API).
9. **Sauvegarde / Chargement** : Google Sheets (onglet `jsonld`). Colonne `optimized_jsonld` pour les JSON-LD générés.
10. **Cas 0 clusters** : message d'info, pas d'affichage des onglets.

---

## Eco-Score (AIO Efficiency)

- **AIOImpactCalculator** : compare page brute (HTML complet) vs page optimisée (signal pur).
- **Paramètres site** : dans un expander "Paramètres du Site" (nombre de pages catalogue 1–100k, vues/jour par page 1–1000).
- **Big Numbers** : CO₂ économisé/an (t ou g), énergie (MWh), équivalent vols Paris–NY.
- **Graphique Plotly** : 12 mois, 3 axes (tokens, kWh, gCO₂ cumulés).
- **Méthodologie** : triptyque AIO, formule Scale, cache Hash, tableau.

---

## Scraping & Selenium (Streamlit Cloud)

- **packages.txt** : `chromium`, `chromium-driver` pour l'environnement Linux Streamlit Cloud.
- **core/scraping.py** : `SmartScraper` avec `_init_selenium()` compatible Cloud. `fetch_page()` pour récupération HTTP simple.
- **Logs :** `log_callback` passé au SmartScraper pour afficher les logs de crawl et de détection JSON-LD en temps réel.

---

## Base de données (Google Sheets)

- **Onglet `users` :** email, password_hash, created_at, last_login, role.
- **Onglet `audits` :** audit_id, user_email, workspace, date, site_url, nb_urls, data_compressed, nom_site, colonne `master_json`. Filtrage obligatoire par `user_email`.
- **Onglet `jsonld` :** site_url, model_id, model_name, page_count, url_pattern, sample_urls, dom_structure, existing_jsonld, recommended_schema, **optimized_jsonld**, created_at, workspace, user_email. **AuditDatabase** : `save_jsonld_models()`, `load_jsonld_models()`, `list_jsonld_sites()`, `_decompress_from_sheet()`.

---

## Structure SaaS et réutilisation pour une API

### Respect du pattern SaaS

Le projet respecte les principes SaaS :

- **Isolation par `user_email`** : toutes les requêtes DB filtrent par `get_current_user_email()`.
- **Session** : `core.session_keys` centralise les clés, `AuditDatabase` est la couche de persistance.
- **Core / Engine / Modules** : séparation nette (auth, DB, scraping) vs (logique métier) vs (UI Streamlit).

### Développer une API à partir des modules

**Structure actuelle :** Les modules mélangent logique métier et UI Streamlit. Cependant, `jsonld_analyzer.py` (et d'autres) exposent des fonctions **réutilisables sans Streamlit** :

- `extract_dom_structure(html_content)` → dict
- `extract_semantic_features(html_content, json_ld)` → dict
- `structure_similarity(struct_a, struct_b)` → float
- `page_similarity(page_a, page_b)` → float
- `cluster_pages(results, threshold)` → list
- `name_cluster_with_mistral(api_key, results, cluster_indices)` → dict
- `generate_optimized_jsonld(api_key, schema_type, dom_structure, sample_pages, existing_jsonld, url_pattern)` → tuple

Ces fonctions n'utilisent pas `st.*` ni `session_state`. Elles peuvent être importées et appelées depuis une API REST.

**Recommandation pour une API :**

1. **Couche `services/` en place** : `services/jsonld_service.py` centralise la logique JSON-LD (clustering, Mistral, graphe). Le module Streamlit `modules/jsonld/jsonld_analyzer.py` l'importe. Une API FastAPI peut importer directement :
   ```python
   from services.jsonld_service import cluster_pages, generate_optimized_jsonld, extract_dom_structure
   ```
2. **Pour étendre** : créer `api/main.py` (FastAPI) qui importe ces fonctions et expose des routes (ex: `POST /analyze`, `POST /generate-jsonld`).
3. **Authentification API** : passer `user_email` en paramètre ou le déduire du token JWT / API key.

---

## Installation

**Prérequis :** Python 3.9+, clé API Mistral (nommage clusters + génération JSON-LD optimisé), Google Sheets pour auth/audits. Pour **Streamlit Cloud**, le fichier `packages.txt` installe Chromium et ChromeDriver.

```bash
git clone https://github.com/vincedosi/PROJET_HOTARU_V2.git
cd PROJET_HOTARU_V2
pip install -r requirements.txt
streamlit run app.py
```

**Configuration — Streamlit Secrets :** Toutes les clés sont dans `st.secrets` (local : `.streamlit/secrets.toml` ; Cloud : paramètres de l'app > Secrets).

```toml
[mistral]
api_key = "votre-cle-mistral"

[gcp_service_account]
# JSON du compte de service Google

sheet_url = "https://docs.google.com/spreadsheets/d/..."
SERPAPI_KEY = "..."  # Optionnel, Audit Externe
```

---

## Conventions de code

- **Session :** `core.session_keys` et `get_current_user_email()` pour les données utilisateur.
- **Scraping :** `core.scraping.SmartScraper(start_urls, max_urls=..., log_callback=...)` ; `fetch_page(url)` pour requête HTTP simple.
- **Titres de section :** Classe CSS `.section-title`, format `XX / TITRE`.
- **Version :** `version.py` (VERSION, BUILD_DATE) — mis à jour à chaque push.

---

## Design system

- **Couleurs :** Fond `#FFFFFF`, texte `#000000`, accent rouge `rgb(168, 27, 35)`, noir `#0f172a`.
- **Scores :** Vert (bon), orange (moyen), rouge (à améliorer).
- **Typographie :** Inter, uppercase pour labels, wide tracking.

---

## Roadmap

- [x] Navigation SaaS, isolation par user_email
- [x] SmartScraper (Selenium Streamlit Cloud, log_callback, JSON-LD), packages.txt
- [x] Audit GEO (Audit Site | Audit Externe | Méthodologie), logs crawl
- [x] Authority Score AI-Native (5 piliers, embeddings, sameAs, méthodologie v2)
- [x] Onglet JSON-LD (Master + Analyse JSON-LD), Master audit gap, sauvegarde audits
- [x] Analyse JSON-LD : clustering DOM intelligent (h2/h3 ±60%), Mistral, graphe pyvis, sauvegarde/chargement Google Sheets
- [x] Analyse JSON-LD : génération JSON-LD optimisé via Mistral AI, messages d'erreur détaillés
- [x] Analyse JSON-LD : fusion manuelle des clusters, indicateur variabilité DOM
- [x] Eco-Score : AIO Impact Calculator, paramètres dans expander
- [x] Scraping debug (module Audit)
- [x] Méthodologie Audit Externe toujours visible
- [ ] Onglet Paramètres (profil, préférences)
- [ ] Vault : clés API chiffrées par utilisateur
- [ ] Rôle admin (stats globales, gestion comptes)
- [ ] Export PDF, API REST

---

## Licence

MIT — libre d'utilisation et de modification.

**HOTARU** — *Éclairer votre SEO comme une luciole dans la nuit*
