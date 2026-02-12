# Rapport d'audit code — HOTARU v2

**Date :** 2026-02  
**Objectifs :** bugs, code mort, optimisations, lenteur de chargement Streamlit

---

## 1. FICHIERS / FONCTIONS INUTILISÉS

### 1.1 Fichiers à supprimer ou archiver

| Fichier | Statut | Action recommandée |
|---------|--------|--------------------|
| `core/i18n.py` | Jamais importé (i18n désactivé) | Supprimer ou conserver pour usage futur |
| `core/ai_clustering.py` | Jamais importé | Supprimer : le nommage clusters est dans `services/jsonld_service.py` |
| `modules/jsonld/leaf.py` | Non utilisé dans l'app | Supprimer ou ajouter l'onglet Leaf dans la navigation |

### 1.2 Fonctions potentiellement mortes

- `core/ai_clustering.py` : tout le fichier (get_naming_prompt, etc.) — remplacé par `name_cluster_with_mistral` dans jsonld_service.

---

## 2. BUGS POTENTIELS

### 2.1 Corrigé récemment

- **database.py** : `sheet_file` non initialisé → AttributeError sur fusion clusters. Corrigé (v3.0.35).

### 2.2 À surveiller

- **workspace "+ Créer Nouveau"** : dans `app.py` et `jsonld_analyzer`, le texte exact varie (`"+ Creer Nouveau"`, `"+ Créer Nouveau"`, `"+ Create New"`). Risque de comportement incohérent — normaliser.
- **load_user_audits** : appelé à chaque run pour le workspace. Pas de cache sur l’appel Google Sheets (voir § 3.2).

---

## 3. OPTIMISATIONS — LENTEUR STREAMLIT

### 3.1 Tous les onglets sont exécutés

Avec `st.tabs()`, Streamlit exécute **tout le contenu** de tous les onglets à chaque run, même si un seul est visible.

**Effet :** à chaque chargement ou interaction :
- import de `audit_geo`, `authority_score`, `audit_scraping`, `off_page`, `geo_scoring`
- import de `master`, `jsonld_analyzer`, `methodologie_blocks`
- import de `eco_impact`
- import de `scraping` (Selenium), `sentence_transformers`, etc.

**Solution :** remplacer les onglets principaux par une navigation conditionnelle (ex. `st.radio` ou `st.selectbox`) pour ne charger que le module sélectionné :

```python
# Au lieu de st.tabs() pour les 4 sections principales
nav = st.radio("Navigation", ["Accueil", "Audit", "JSON-LD", "Eco-Score"], horizontal=True)
if nav == "Accueil":
    render_home()
elif nav == "Audit":
    # sous-tabs...
elif nav == "JSON-LD":
    # ...
elif nav == "Eco-Score":
    render_eco_tab()
```

### 3.2 Google Sheets à chaque run

`load_user_audits()` appelle `self.sheet.get_all_values()` à chaque exécution, sans cache.

**Effet :** requête API Google Sheets à chaque interaction.

**Solution :** mettre en cache le résultat brut des audits (ex. `@st.cache_data(ttl=60)` sur une fonction qui récupère les lignes), ou au minimum le résultat de `load_user_audits` par `user_email`.

### 3.3 Bibliothèques lourdes

| Package | Impact | Utilisé dans |
|---------|--------|---------------|
| `sentence-transformers` | Import lourd (torch, etc.) | `authority_score.py` |
| `selenium` | Import lourd | `core/scraping.py` |
| `trafilatura` | Moyen | `authority_score`, `eco_impact` |
| `tiktoken` | Moyen | `eco_impact` |
| `sklearn` | Moyen | (à vérifier) |

**Solution :**  
- Imports tardifs : charger `sentence_transformers` uniquement quand l’utilisateur ouvre l’onglet Authority Score.  
- `scraping.py` : importer Selenium seulement si `use_selenium=True` (lazy import dans la méthode qui lance le driver).

### 3.4 AuditDatabase et connexion GSheet

`get_cached_database()` crée la DB au premier appel. L’initialisation (OAuth, `open_by_url`) peut être lente.

**Solution :** garder le cache en session ; éventuellement précharger la DB en arrière-plan après le login.

---

## 4. RECOMMANDATIONS PRIORITAIRES

### Priorité haute (impact sur la vitesse)

1. **Navigation conditionnelle** : ne pas exécuter les onglets non affichés.
2. **Cache `load_user_audits`** : éviter d’appeler Google Sheets à chaque run.
3. **Imports tardifs** : charger `sentence_transformers` et `selenium` uniquement quand nécessaire.

### Priorité moyenne (nettoyage)

4. Supprimer `core/ai_clustering.py` et `core/i18n.py` si non utilisés.
5. Décider du sort de `modules/jsonld/leaf.py` (supprimer ou activer l’onglet).

### Priorité basse (robustesse)

6. Normaliser les chaînes de workspace ("+ Créer Nouveau", etc.).
7. Ajouter des tests unitaires sur les fonctions critiques.

---

## 5. RÉSUMÉ DES MODIFICATIONS SUGGÉRÉES

| Action | Fichier(s) | Gain estimé |
|--------|------------|-------------|
| Navigation conditionnelle | `app.py` | Fort — moins de code exécuté |
| Cache load_user_audits | `core/database.py`, `app.py` | Moyen — moins d’appels API |
| Suppression ai_clustering | `core/ai_clustering.py` | Léger — code plus clair |
| Suppression i18n | `core/i18n.py` | Léger |
| Lazy import sentence_transformers | `authority_score.py` | Moyen — chargement différé |
| Lazy import selenium | `scraping.py` | Moyen — si mode Selenium peu utilisé |

---

## 6. STRUCTURE ACTUELLE (VALIDÉE)

- `core/` : auth, database, scraping, session_keys
- `engine/` : master_handler, dynamic_handler, template_builder
- `services/` : jsonld_service (logique réutilisable)
- `modules/` : home, audit, jsonld, eco

La séparation des responsabilités est correcte.
