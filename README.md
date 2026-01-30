# HOTARU 蛍

**Application SaaS d'Audit SEO GEO avec Intelligence Artificielle**

HOTARU (firefly/luciole en japonais) est une application Streamlit conçue pour analyser la structure de sites web et optimiser leur architecture d'information grâce à l'IA.

---

## 🎯 Objectif

Créer un outil SaaS permettant aux professionnels du SEO de :
- Scanner automatiquement la structure d'un site web
- Détecter les patterns d'URL (pages produits, articles, fiches locales...)
- Visualiser l'architecture sous forme de graphe interactif
- Optimiser le regroupement des pages avec Mistral AI

---

## ✨ Fonctionnalités

### 1. Navigation SaaS
- Sidebar fixe avec navigation entre modules
- Dashboard, Audit GEO, Rapports, Paramètres
- Vault d'API sécurisé (clés stockées en session uniquement)
- Design Zen japonais (blanc pur, accents dorés)

### 2. Smart Scraping
- Détection automatique du sitemap
- **Smart Sampling** : détection de patterns d'URL via regex
  - Ex: `/produit/*`, `/cirfa/*`, `/blog/*`
  - Analyse de seulement 3 spécimens par pattern
  - Héritage des scores pour les autres pages du pattern
- Économie de tokens API et de temps d'analyse

### 3. Optimisation IA (Mistral)
- Catégorisation intelligente des URLs
- Renommage des pages en labels lisibles
- Création de clusters sémantiques
- Barre de progression et logs en temps réel

### 4. Visualisation
- Graphe interactif (streamlit-agraph)
- Nœuds cliquables vers les URLs
- Code couleur selon le score SEO
- Groupement des pages similaires

---

## 🏗️ Architecture

```
PROJET_HOTARU_V2/
├── app.py                  # Point d'entrée, navigation SaaS
├── requirements.txt        # Dépendances Python
├── assets/
│   ├── style.css          # CSS Zen Design
│   └── logo.png           # Logo (optionnel)
├── core/
│   ├── auth.py            # Authentification
│   ├── database.py        # Connexion Google Sheets
│   ├── scraping.py        # Smart Scraper avec patterns
│   └── ai_clustering.py   # Intégration Mistral AI
├── modules/
│   ├── dashboard.py       # Page d'accueil
│   ├── audit_geo.py       # Module principal d'audit
│   ├── reports.py         # Rapports et exports
│   └── settings.py        # Paramètres
└── .streamlit/
    └── secrets.toml       # Configuration (API keys, etc.)
```

---

## 🚀 Installation

### Prérequis
- Python 3.9+
- Compte Streamlit Cloud (pour déploiement)
- Clé API Mistral (gratuite sur console.mistral.ai)

### Local

```bash
# Cloner le repo
git clone https://github.com/votrecompte/PROJET_HOTARU_V2.git
cd PROJET_HOTARU_V2

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py
```

### Streamlit Cloud

1. Connectez votre repo GitHub à Streamlit Cloud
2. Configurez les secrets dans les paramètres de l'app
3. Déployez !

---

## ⚙️ Configuration

### Secrets Streamlit (.streamlit/secrets.toml)

```toml
[gcp_service_account]
type = "service_account"
project_id = "votre-projet"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "compte@projet.iam.gserviceaccount.com"

[spreadsheet]
url = "https://docs.google.com/spreadsheets/d/..."
```

### Clé API Mistral

La clé API Mistral est saisie directement dans l'interface et stockée uniquement en session (non persistée pour des raisons de sécurité).

---

## 📊 Smart Sampling

Le système de Smart Sampling détecte automatiquement les patterns d'URL répétitifs :

| Pattern détecté | Exemple | Action |
|----------------|---------|--------|
| `/produit/*` | 500 fiches produits | Analyse 3 spécimens |
| `/cirfa/*` | 200 centres CIRFA | Analyse 3 spécimens |
| `/blog/*` | 100 articles | Analyse 3 spécimens |
| Pages uniques | Contact, À propos | Analyse complète |

**Avantage** : Un site de 500 pages peut être analysé avec seulement ~30 requêtes HTTP au lieu de 500.

---

## 🎨 Design System

### Couleurs
- **Fond** : Blanc pur `#FFFFFF`
- **Texte** : Noir pur `#000000`
- **Accent** : Or `#FFD700` (éléments actifs uniquement)
- **Scores** :
  - Vert `#22C55E` (bon, 70+)
  - Orange `#F97316` (moyen, 40-69)
  - Rouge `#EF4444` (à améliorer, <40)

### Typographie
- Police sans-serif légère (Inter, system fonts)
- Hiérarchie claire avec tailles définies

---

## 🔒 Sécurité

- Clés API stockées en session uniquement (non persistées)
- Authentification via Google Sheets
- Pas de stockage de données sensibles côté client

---

## 📝 Roadmap

- [x] Navigation SaaS sidebar
- [x] Smart Scraping avec patterns
- [x] Intégration Mistral AI
- [x] Graphe interactif cliquable
- [x] Barre de progression IA
- [ ] Export PDF des rapports
- [ ] Historique des audits
- [ ] Mode comparaison avant/après
- [ ] API REST pour intégration externe

---

## 🤝 Contribution

Les contributions sont bienvenues ! N'hésitez pas à ouvrir une issue ou une PR.

---

## 📄 Licence

MIT License - Libre d'utilisation et de modification.

---

**HOTARU** 蛍 - *Éclairer votre SEO comme une luciole dans la nuit*
