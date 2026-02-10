# HOTARU

**SaaS d'audit et d'optimisation pour le web lisible par l'IA**

HOTARU (luciole) est une application Streamlit : crawl, scoring GEO, Authority Index (AI-Native), Master Data (JSON-LD entité), LEAF (JSON-LD par page), Eco-Score, AI Transformer. Multi-utilisateurs avec isolation stricte des données par utilisateur.

---

## Vision produit

- **Audit** : 3 sous-onglets — **Audit GEO** (structure du site, graphe interactif, patterns d’URL, renommage IA Mistral ; 3 tabs : Audit Site | Audit Externe | Méthodologie), **Authority Score** (AI Authority Index v2 — 5 piliers : Ancrage Knowledge Graph, Interopérabilité des Données, Autorité de Citation, Densité Vectorielle, Fraîcheur ; embeddings + sameAs), **Scraping** (diagnostic URL + logs JSON-LD / techno / Selenium).
- **JSON-LD** : 2 sous-onglets — **Master** (données d’entité Wikidata + Mistral, JSON-LD Organization, audit & gap, sauvegarde audits), **Leaf** (JSON-LD par page, prédictions IA).
- **Eco-Score** : calculatrice d’impact carbone (tokens, kWh, gCO₂) et méthodologie scientifique.
- **AI Transformer** : analyse, transformation et scoring de contenu (templates, comparaison).

**Design :** Fond blanc, noir + rouge `rgb(168, 27, 35)`. Titres de section au format `XX / TITRE`, rouge souligné.

---

## Structure du projet

```
PROJET_HOTARU_V2/
├── app.py                      # Point d'entrée : auth, header, 5 tabs, footer
├── packages.txt                # Streamlit Cloud : chromium, chromium-driver
├── requirements.txt            # Python deps (selenium, webdriver-manager, sentence-transformers, etc.)
├── assets/
│   ├── logo.png
│   └── style.css               # Design system (noir, rouge, section-title)
├── core/
│   ├── auth.py                 # AuthManager (Google Sheets users)
│   ├── database.py             # AuditDatabase (audits, load_user_audits, save_audit, save_master_for_audit)
│   ├── session_keys.py         # Clés de session SaaS
│   ├── scraping.py             # SmartScraper (crawl, Selenium Streamlit Cloud, log_callback, get_page_details + JSON-LD)
│   └── ai_clustering.py        # Renommage clusters (Mistral)
├── engine/
│   ├── master_handler.py       # MasterDataHandler, Wikidata + Mistral, heuristiques
│   ├── dynamic_handler.py     # Prédictions Mistral (LEAF)
│   └── template_builder.py     # Génération JSON-LD
├── modules/
│   ├── home.py                 # Page d'accueil
│   ├── audit_geo.py            # Audit GEO (workspace, Audit Site | Audit Externe | Méthodologie, log_callback SmartScraper)
│   ├── audit_scraping.py       # Scraping debug (URL, logs JSON-LD, techno, Selenium)
│   ├── authority_score.py      # Authority Score AI-Native (5 piliers, sentence_transformers, sameAs)
│   ├── master.py               # Master Data (Données | Méthodologie, recherche Wikidata/INSEE, audit gap, hydrate JSON-LD)
│   ├── leaf.py                 # LEAF Builder (Builder | Méthodologie)
│   ├── off_page.py             # Audit Externe (réputation, Audit Miroir, Méthodologie toujours visible)
│   ├── eco_impact.py           # Eco-Score (Calculatrice | Méthodologie)
│   ├── methodologie_blocks.py  # Contenu Méthodologie (Authority v2, Master, Leaf)
│   ├── geo_scoring.py          # Scoring GEO
│   ├── ai_transformer_page.py  # AI Transformer (onglet principal)
│   └── ai_transformer/         # analyzer, transformer, scorer, visualizer, templates
├── CLAUDE.md                   # Référence agent (voir README)
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
- **JSON-LD** : sous-onglets **Master**, **Leaf** (plus d’onglets Master/Leaf au top).
- Méthodologie par module : dédiée (Audit GEO, Off-Page) ou `methodologie_blocks.render_methodologie_for_module("authority"|"master"|"leaf")`.

---

## Scraping & Selenium (Streamlit Cloud)

- **packages.txt** : `chromium`, `chromium-driver` pour l’environnement Linux Streamlit Cloud.
- **core/scraping.py** : `SmartScraper` avec `_init_selenium()` compatible Cloud (recherche binaires chromium/chromedriver via `shutil.which` et chemins `/usr/bin/...`). Pas d’undetected-chromedriver ni webdriver-manager en production Cloud.
- **Logs :** `log_callback` passé au SmartScraper (ex. dans Audit GEO et module Scraping) pour afficher les logs de crawl et de détection JSON-LD en temps réel.

---

## Base de données (Google Sheets)

- **Onglet `users` :** email, password_hash, created_at, last_login, role.
- **Onglet `audits` :** audit_id, user_email, workspace, date, site_url, nb_pages, data_compressed, nom_site, colonne `master_json` pour sauvegarde Master par audit. Filtrage obligatoire par `user_email`.

---

## Installation

**Prérequis :** Python 3.9+, clé API Mistral (optionnel), Google Sheets pour auth/audits. Pour **Streamlit Cloud**, le fichier `packages.txt` installe Chromium et ChromeDriver.

```bash
git clone https://github.com/vincedosi/PROJET_HOTARU_V2.git
cd PROJET_HOTARU_V2
pip install -r requirements.txt
streamlit run app.py
```

**Configuration :** `.streamlit/secrets.toml` (GCP service account, URL spreadsheet, Mistral, SERPAPI_KEY pour Audit Externe).

---

## Conventions de code

- **Session :** `core.session_keys` et `get_current_user_email()` pour les données utilisateur.
- **Scraping :** `core.scraping.SmartScraper(start_urls, max_urls=..., log_callback=...)` ; `get_page_details(url)` retourne `has_structured_data`, `json_ld`, etc.
- **Titres de section :** Classe CSS `.section-title`, format `XX / TITRE`.
- **Version :** `app.py` (VERSION, BUILD_DATE).

---

## Design system

- **Couleurs :** Fond `#FFFFFF`, texte `#000000`, accent rouge `rgb(168, 27, 35)`.
- **Scores :** Vert (bon), orange (moyen), rouge (à améliorer).
- **Typographie :** Inter, uppercase pour labels, wide tracking.

---

## Roadmap

- [x] Navigation SaaS, isolation par user_email
- [x] SmartScraper (Selenium Streamlit Cloud, log_callback, JSON-LD), packages.txt
- [x] Audit GEO (Audit Site | Audit Externe | Méthodologie), logs crawl
- [x] Authority Score AI-Native (5 piliers, embeddings, sameAs, méthodologie v2)
- [x] Onglet JSON-LD (Master + Leaf), Master audit gap, hydrate JSON-LD client, sauvegarde audits
- [x] Scraping debug (module Audit), AI Transformer
- [x] Méthodologie Audit Externe toujours visible
- [ ] Onglet Paramètres (profil, préférences)
- [ ] Vault : clés API chiffrées par utilisateur
- [ ] Rôle admin (stats globales, gestion comptes)
- [ ] Export PDF, API REST

---

## Licence

MIT — libre d’utilisation et de modification.

**HOTARU** — *Éclairer votre SEO comme une luciole dans la nuit*
