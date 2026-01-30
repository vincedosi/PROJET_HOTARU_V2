# 🏮 PROJECT HOTARU V3 - MASTER INSTRUCTIONS (SaaS & Smart Audit)

## 1. UI/UX "ZEN" & NAVIGATION SAAS
- **Design System :** - Fond blanc partout (#FFFFFF). 
    - Boutons : bordures noires 1px, coins arrondis, police sans-serif très légère.
    - Supprimer tous les éléments de décoration Streamlit inutiles.
- **Navigation :** Créer une sidebar fixe (assets/logo.png en haut).
- **Onglets (Tabs) :** Audit, Transformation, Rapports, Paramètres.
- **Persistence :** Utiliser `st.session_state` pour ne pas perdre les données en changeant d'onglet.

## 2. MISSION : SCRAPING INTELLIGENT (SMART SAMPLING)
Le but est d'éviter la saturation sur les sites à gros volume (500+ fiches produits).

- **Fonction `detect_page_templates(urls)` :** - Analyser les patterns d'URL (ex: `/produit/*` ou `/cirfa/*`) via Regex.
    - Si un groupe > 5 pages : n'analyser que **3 spécimens** via Mistral/OpenAI.
    - Les autres pages du groupe "héritent" des scores et métadonnées du groupe.
- **Workflow de Visualisation :** 1. Construire d'abord un schéma de scraping brut.
    2. Lancer l'optimisation via IA (Mistral).
    3. Reconstruire le graphique final.

## 3. INTÉGRATION MISTRAL & GRAPHIQUE
- **Feedback visuel :** Utiliser `st.progress()` et `st.status()` pendant la phase de regroupement intelligent par Mistral.
- **Le Graphe (Organigramme) :** - Regrouper les fiches identiques sous un seul nœud parent "Cluster" pour la clarté.
    - **INTERACTIVITÉ :** Chaque nœud doit contenir le lien de la page web et être CLIQUABLE pour s'y rendre.
    - Nœuds blancs, bordure noire, pastilles GEO (🔴🟠🟢).

## 4. LOGIQUE DE SAUVEGARDE (VERSIONING)
- Utiliser l'onglet `audits` de la Google Sheet via `service_account.json`.
- Sauvegarder/Charger les états du JSON du graphe pour permettre le Load & Modify.

## 5. INSTRUCTIONS DE CODAGE IMMÉDIATES POUR CLAUDE CODE
1. Analyse mon fichier de crawl actuel.
2. Propose la modification pour inclure la détection de patterns (Regex).
3. Génère le code de la sidebar de navigation avec le logo.
4. Intègre la barre de progression dans la fonction qui appelle Mistral.
5. Implémente le lien cliquable sur les nœuds du graphique.

**LANCE L'AMÉLIORATION DE LA NAVIGATION ET LA LOGIQUE DE SAMPLING MAINTENANT.**
