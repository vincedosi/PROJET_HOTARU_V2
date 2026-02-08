# HOTARU

**SaaS d'audit et d'optimisation pour le web lisible par l'IA**

HOTARU (luciole) est une application Streamlit : crawl, scoring GEO, Authority Index, Master Data (JSON-LD entité), LEAF (JSON-LD par page), Eco-Score. Multi-utilisateurs avec isolation stricte des données par utilisateur.

---

## Vision produit

- **Audit GEO** : structure du site, graphe interactif, patterns d’URL, renommage IA (Mistral).
- **Authority Score** : indice de probabilité de citation par les LLMs (5 piliers : Knowledge Graph, Structured Data, Citation Authority, Semantic Completeness, Content Freshness).
- **Master** : données d’entité (Wikidata + Mistral), génération JSON-LD Organization.
- **Leaf** : JSON-LD par page, prédictions IA.
- **Eco-Score** : calculatrice d’impact carbone (tokens économisés, kWh, gCO₂) et méthodologie scientifique.

**Design :** Fond blanc, noir + rouge `rgb(168, 27, 35)`. Titres de section au format `XX / TITRE`, rouge souligné.

---

## Structure du projet

```
PROJET_HOTARU_V2/
├── app.py                      # Point d’entrée : auth, header, tabs, footer
├── assets/
│   ├── logo.png
│   └── style.css               # Design system (noir, rouge, section-title, etc.)
├── core/
│   ├── auth.py                 # AuthManager (Google Sheets users)
│   ├── database.py             # AuditDatabase (audits, load_user_audits, save_audit)
│   ├── session_keys.py         # Clés de session SaaS
│   ├── scraping.py             # SmartScraper (crawl) + fetch_page(url) pour une page
│   └── ai_clustering.py        # Renommage clusters (Mistral)
├── engine/
│   ├── master_handler.py       # MasterDataHandler, Wikidata + Mistral
│   ├── dynamic_handler.py      # Prédictions Mistral (LEAF)
│   └── template_builder.py     # Génération JSON-LD
├── modules/
│   ├── home.py                 # Page d’accueil
│   ├── audit_geo.py            # Audit GEO (workspace, onglets Audit Site | Méthodologie)
│   ├── authority_score.py      # Authority Score (Analyse | Méthodologie)
│   ├── master.py               # Master Data (Données | Méthodologie)
│   ├── leaf.py                 # LEAF Builder (Builder | Méthodologie)
│   ├── eco_impact.py           # Eco-Score (Calculatrice | Méthodologie)
│   ├── methodologie_blocks.py  # Contenu Méthodologie réutilisable
│   └── geo_scoring.py          # Scoring GEO
├── requirements.txt
└── README.md                   # Ce fichier
```

---

## SaaS : authentification et isolation

- **Login :** `core.auth.AuthManager` — email + mot de passe, hash en Google Sheets (onglet `users`).
- **Session :** `st.session_state` avec `authenticated`, `user_email`, `user_role` (clés dans `core.session_keys`).
- **Isolation :** `AuditDatabase.load_user_audits(user_email)` filtre strictement par `user_email`. Un utilisateur ne voit que ses audits.
- **Usage :** `get_current_user_email()`, `is_authenticated()`, `is_admin()` depuis `core.session_keys`.

---

## Navigation

**Onglets principaux (app.py) :** Home | Audit | Authority Score | Master | Leaf | Eco-Score

**Sous-onglets par module :** Chaque module métier a deux sous-onglets (ex. Audit Site | Méthodologie). La Méthodologie est soit dédiée (Audit), soit fournie par `methodologie_blocks.render_methodologie_for_module("authority"|"master"|"leaf")`.

---

## Base de données (Google Sheets)

- **Onglet `users` :** email, password_hash, created_at, last_login, role.
- **Onglet `audits` :** audit_id, user_email, workspace, date, site_url, nb_pages, data_compressed, nom_site. Filtrage obligatoire par `user_email`.

---

## Installation

**Prérequis :** Python 3.9+, clé API Mistral (optionnel), Google Sheets pour auth/audits.

```bash
git clone https://github.com/vincedosi/PROJET_HOTARU_V2.git
cd PROJET_HOTARU_V2
pip install -r requirements.txt
streamlit run app.py
```

**Configuration :** Fichier `.streamlit/secrets.toml` (GCP service account, URL du spreadsheet). Les clés API (Mistral, etc.) peuvent être en session ou dans les secrets.

---

## Conventions de code

- **Session :** Utiliser `core.session_keys` et `get_current_user_email()` pour les audits.
- **Fetch d’une page :** `core.scraping.fetch_page(url, timeout=15)` — utilisé par eco_impact et réutilisable ailleurs.
- **Titres de section :** Classe CSS `.section-title`, format texte `XX / TITRE`.
- **Version :** `app.py` (VERSION, BUILD_DATE avec date+heure à chaque run).

---

## Design system

- **Couleurs :** Fond `#FFFFFF`, texte `#000000`, accent rouge `rgb(168, 27, 35)`.
- **Scores :** Vert (bon), orange (moyen), rouge (à améliorer).
- **Typographie :** Inter, uppercase pour labels, wide tracking.

---

## Roadmap

- [x] Navigation SaaS, isolation par user_email
- [x] Smart Scraping (patterns, SmartScraper), fetch_page
- [x] Audit GEO, Authority Score, Master, Leaf, Eco-Score
- [x] Onglets Méthodologie, design harmonisé
- [ ] Onglet Paramètres (profil, préférences)
- [ ] Vault : clés API chiffrées par utilisateur
- [ ] Rôle admin (stats globales, gestion comptes)
- [ ] Export PDF, API REST

---

## Licence

MIT — libre d’utilisation et de modification.

**HOTARU** — *Éclairer votre SEO comme une luciole dans la nuit*
