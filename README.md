# HOTARU

**SaaS d'audit et d'optimisation pour le web lisible par l'IA**

HOTARU (luciole) est une application Streamlit : crawl, scoring GEO, Authority Index (AI-Native), Master Data (JSON-LD entité), LEAF (JSON-LD par page), **Analyse JSON-LD** (clustering DOM, graphe interactif, export Google Sheets), **Eco-Score** (AIO Impact Calculator), AI Transformer. Multi-utilisateurs avec isolation stricte des données par utilisateur.

---

## Vision produit

- **Audit** : 3 sous-onglets — **Audit GEO** (structure du site, graphe interactif, patterns d’URL, renommage IA Mistral ; 3 tabs : Audit Site | Audit Externe | Méthodologie), **Authority Score** (AI Authority Index v2 — 5 piliers : Ancrage Knowledge Graph, Interopérabilité des Données, Autorité de Citation, Densité Vectorielle, Fraîcheur ; embeddings + sameAs), **Scraping** (diagnostic URL + logs JSON-LD / techno / Selenium).
- **JSON-LD** : 3 sous-onglets — **Master** (données d’entité Wikidata + Mistral, JSON-LD Organization, audit & gap, sauvegarde audits), **Leaf** (JSON-LD par page, prédictions IA), **Analyse JSON-LD** (clustering DOM, nommage Mistral, graphe interactif, sauvegarde/chargement Google Sheets).
- **Eco-Score** : **AIO Efficiency** — calculatrice d’impact carbone (tokens, kWh, gCO₂), paramètres site (pages catalogue, vues/jour), Big Numbers annuels, graphique Plotly 12 mois, méthodologie scientifique.
- **AI Transformer** : analyse, transformation et scoring de contenu (templates, comparaison).

**Design :** Fond blanc, noir + rouge `rgb(168, 27, 35)`. Titres de section au format `XX / TITRE`, rouge souligné.

---

## Versioning

À **chaque push ou merge sur `main`** (pull request), mettre à jour **`version.py`** :
- `BUILD_DATE = "YYYY-MM-DD HH:MM"` (date et heure courantes)
- `VERSION` : incrémenter si besoin (ex. 3.0.17 → 3.0.18)

L'app affiche **V {VERSION} // {BUILD_DATE}** dans le header et le footer. Ne jamais pusher sans mettre à jour `version.py`.

---

## Structure du projet

```
PROJET_HOTARU_V2/
├── app.py                      # Point d'entrée : auth, header, 5 tabs, footer
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
│   ├── master_handler.py       # MasterDataHandler, Wikidata + Mistral, heuristiques
│   ├── dynamic_handler.py      # Prédictions Mistral (LEAF)
│   └── template_builder.py     # Génération JSON-LD
├── docs/
│   └── CLAUDE.md               # Référence agent (voir README)
├── modules/
│   ├── home.py                 # Page d'accueil
│   ├── audit/                  # Onglet Audit (GEO, Authority, Scraping, Off-Page)
│   │   ├── __init__.py
│   │   ├── audit_geo.py        # Audit GEO (workspace, Audit Site | Externe | Méthodologie)
│   │   ├── audit_scraping.py   # Scraping debug (URL, logs JSON-LD, techno, Selenium)
│   │   ├── authority_score.py  # Authority Score AI-Native (5 piliers)
│   │   ├── off_page.py         # Audit Externe (réputation, Audit Miroir)
│   │   └── geo_scoring.py      # Scoring GEO
│   ├── jsonld/                 # Onglet JSON-LD (Master, Leaf, Analyse JSON-LD)
│   │   ├── __init__.py
│   │   ├── master.py           # Master Data (Wikidata/INSEE, audit gap, JSON-LD)
│   │   ├── leaf.py             # LEAF Builder (Builder | Méthodologie)
│   │   ├── jsonld_analyzer.py  # Analyse JSON-LD (clustering DOM, Mistral, graphe, export)
│   │   └── methodologie_blocks.py  # Contenu Méthodologie (Authority, Master, Leaf)
│   ├── eco/                    # Onglet Eco-Score
│   │   ├── __init__.py
│   │   └── eco_impact.py       # AIO Impact Calculator (tokens, kWh, gCO₂, Plotly)
│   └── ai_transformer/         # Onglet AI Transformer
│       ├── __init__.py
│       ├── ai_transformer_page.py
│       ├── analyzer.py
│       ├── transformer.py
│       ├── scorer.py
│       └── visualizer.py
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

**Onglets principaux (app.py) :** Home | Audit | JSON-LD | Eco-Score | AI Transformer

- **Audit** : sous-onglets **Audit GEO**, **Authority Score**, **Scraping**.
- **JSON-LD** : sous-onglets **Master**, **Leaf**, **Analyse JSON-LD**.
- **Eco-Score** : AIO Efficiency (paramètres site, Big Numbers, graphique 12 mois).
- Méthodologie par module : dédiée (Audit GEO, Off-Page, Eco) ou `methodologie_blocks.render_methodologie_for_module("authority"|"master"|"leaf")`.

---

## Analyse JSON-LD

Module dédié à la détection des types de pages par structure DOM et pattern d'URL :

1. **Clustering** : Structure HTML 40 %, Pattern URL 30 %, Contenu sémantique 30 % — seuil 85 %.
2. **Interface** : URL, slider pages (50–500), bouton Lancer l'analyse, bouton Effacer les résultats.
3. **Nommage Mistral** : chaque cluster reçoit un nom et un type Schema.org recommandé.
4. **Graphe interactif** : domaine → clusters → URLs exemples (pyvis + networkx). **Nœuds colorés** : domaine noir, chaque cluster couleur distincte, pages gris clair.
5. **Onglets** : GRAPHE (détail cluster sélectionné) | TABLEAU (tabs par cluster) | EXPORT.
6. **Sauvegarde / Chargement** : Google Sheets (onglet `jsonld`). Bouton **Charger depuis Google Sheets** (expander en haut + dans onglet EXPORT) pour recharger des analyses sauvegardées.
7. **Téléchargement JSON** : export complet des modèles.
8. **Cas 0 clusters** : message d’info, pas d’affichage des onglets.

---

## Eco-Score (AIO Efficiency)

- **AIOImpactCalculator** : compare page brute (HTML complet) vs page optimisée (signal pur).
- **Paramètres site** : nombre de pages catalogue (1–100k), vues/jour par page (1–1000).
- **Big Numbers** : CO₂ économisé/an (t ou g), énergie (MWh), équivalent vols Paris–NY.
- **Graphique Plotly** : 12 mois, 3 axes (tokens, kWh, gCO₂ cumulés).
- **Méthodologie** : triptyque AIO, formule Scale, cache Hash, tableau.

---

## Scraping & Selenium (Streamlit Cloud)

- **packages.txt** : `chromium`, `chromium-driver` pour l’environnement Linux Streamlit Cloud.
- **core/scraping.py** : `SmartScraper` avec `_init_selenium()` compatible Cloud (recherche binaires chromium/chromedriver via `shutil.which` et chemins `/usr/bin/...`). `fetch_page()` pour récupération HTTP simple.
- **Logs :** `log_callback` passé au SmartScraper (ex. dans Audit GEO et module Scraping) pour afficher les logs de crawl et de détection JSON-LD en temps réel.

---

## Base de données (Google Sheets)

- **Onglet `users` :** email, password_hash, created_at, last_login, role.
- **Onglet `audits` :** audit_id, user_email, workspace, date, site_url, nb_pages, data_compressed, nom_site, colonne `master_json` pour sauvegarde Master par audit. Filtrage obligatoire par `user_email`.
- **Onglet `jsonld` :** site_url, model_id, model_name, page_count, url_pattern, sample_urls, dom_structure, existing_jsonld, recommended_schema, optimized_jsonld, created_at, workspace, user_email. **AuditDatabase** : `save_jsonld_models()`, `load_jsonld_models()`, `list_jsonld_sites()`, `_decompress_from_sheet()` pour compression zlib+base64.

---

## Installation

**Prérequis :** Python 3.9+, clé API Mistral (optionnel), Google Sheets pour auth/audits. Pour **Streamlit Cloud**, le fichier `packages.txt` installe Chromium et ChromeDriver.

```bash
git clone https://github.com/vincedosi/PROJET_HOTARU_V2.git
cd PROJET_HOTARU_V2
pip install -r requirements.txt
streamlit run app.py
```

**Configuration :** `.streamlit/secrets.toml` (GCP service account, `sheet_url`, `mistral.api_key`, SERPAPI_KEY pour Audit Externe).

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
- [x] Onglet JSON-LD (Master + Leaf + **Analyse JSON-LD**), Master audit gap, sauvegarde audits
- [x] **Analyse JSON-LD** : clustering DOM, Mistral, graphe pyvis, sauvegarde/chargement Google Sheets, nœuds colorés
- [x] **Eco-Score** : AIO Impact Calculator, paramètres site, Big Numbers, graphique Plotly
- [x] Scraping debug (module Audit), AI Transformer
- [x] Méthodologie Audit Externe toujours visible
- [ ] Onglet Paramètres (profil, préférences)
- [ ] Vault : clés API chiffrées par utilisateur
- [ ] Rôle admin (stats globales, gestion comptes)
- [ ] Export PDF, API REST

---

## Licence

MIT — libre d'utilisation et de modification.

**HOTARU** — *Éclairer votre SEO comme une luciole dans la nuit*
