# HOTARU — Version affichée dans l'app (header + footer + home)
# À chaque push : incrémenter VERSION, mettre à jour RELEASE_NOTE et prépendre à RELEASE_HISTORY.

import datetime

VERSION = "3.2.2"
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
RELEASE_NOTE = "Workspace creation fallback : fonctionne sans table user_workspace_access (fallback unified_saves). Rename resilient, placeholders filtres."

# Historique des notes de version (précédentes uniquement, plus récente en premier) — date/heure de release
RELEASE_HISTORY = [
    {"version": "3.2.1", "date": "2026-02-18", "note": "Fix PGRST205 workspace, fix double-clic Lancer Analyse, Mistral timeout 90s + retry + logs detailles."},
    {"version": "3.2.0", "date": "2026-02-18", "note": "Audit complet : centralisation Mistral, fix deps circulaires, onglet Traitement unitaire, validation par tabs, error handling, pydantic, fix bugs scraping/DB."},
    {"version": "3.1.3", "date": "2026-02-18", "note": "Fix IndentationError jsonld_analyzer.py - noms de clusters Mistral restaures."},
    {"version": "3.1.2", "date": "2026-02-18", "note": "Logs détaillés backoffice + database_supabase (create/rename/move workspace, users, accès)."},
    {"version": "3.1.1", "date": "2026-02-18", "note": "Fix creation workspace Supabase (insert + erreurs remontees)."},
    {"version": "3.1.0", "date": "2026-02-18", "note": "Backoffice tabs + CRUD workspaces. Fix scraping 1er clic. Comparaison JSON-LD (gris/vert/rouge). Prompt Mistral visible. Traitement en masse avec validation noeud par noeud. Delta Supabase."},
    {"version": "3.0.86", "date": "2026-02-17", "note": "README : Supabase, backoffice admin, structure et secrets à jour."},
    {"version": "3.0.85", "date": "2026-02-17", "note": "Supabase: chargement liste sauvegardes (ilike + fallback backend). Vue ensemble: fix widget jsonld_cluster_select."},
    {"version": "3.0.84", "date": "2026-02-17", "note": "Backoffice: correctif st.expander (sans key) pour compat Streamlit Cloud."},
    {"version": "3.0.83", "date": "2026-02-17", "note": "Backoffice admin : onglet réservé aux admins — gestion utilisateurs, rôles et accès par workspace (Sheets + Supabase)."},
    {"version": "3.0.82", "date": "2026-02-17", "note": "Supabase: sauvegarde unifiée activée (SAUVEGARDER fonctionne avec connexion Supabase)."},
    {"version": "3.0.81", "date": "2026-02-17", "note": "AUDIT SCRAPING OPTIMIZED: Reset complet + HTML fallback (sites sans JSON-LD) + Cleanup resources. sengager.fr fonctionne maintenant!"},
    {"version": "3.0.80", "date": "2026-02-17", "note": "OPTIMIZATIONS MASSIVES (Phase 1-3): Utilities centralisées (-100 LOC duplication) + Regex cache (+20% perf) + Exponential backoff Mistral + HTML truncation (-66% mémoire) + LinkExtractor unified."},
    {"version": "3.0.79", "date": "2026-02-17", "note": "PHASE 2: Regex compile cache (+20% clustering perf), Exponential backoff Mistral (1s, 2s, 4s, 8s), date validation optimized."},
    {"version": "3.0.78", "date": "2026-02-17", "note": "PHASE 1: Extract utilities (selenium_utils, link_extractor, logger), remove 100+ LOC duplication, HTML truncation -66% memory."},
    {"version": "3.0.77", "date": "2026-02-17", "note": "Audit scraping V1/V2 complete: Link extraction merge (all sources fused) + Crawl4AI exclude_external_links=False + better logging."},
    {"version": "3.0.76", "date": "2026-02-17", "note": "Crawl V2 : delay 2s + extraction liens Markdown/data-href (sites sans JSON-LD, 1 seule page)."},
    {"version": "3.0.75", "date": "2026-02-16", "note": "Scraping V1/V2 : constantes, logs domaines rattachés, champ 2e domaine en bleu (CSS)."},
    {"version": "3.0.74", "date": "2026-02-16", "note": "Audit GEO : domaine(s) rattaché(s) — site sous deux domaines, crawl des deux (V1 + V2)."},
    {"version": "3.0.73", "date": "2026-02-16", "note": "Audit GEO : étape 2 (Flash/Selenium) hors bloc Lancer — geo_step2_pending pour que le clic soit pris en compte."},
    {"version": "3.0.72", "date": "2026-02-16", "note": "Audit GEO : bloc « crawl en attente » exécuté en premier au rerun pour que « Continuer en Flash » lance bien le crawl."},
    {"version": "3.0.71", "date": "2026-02-16", "note": "Sauvegarde audit : version allégée (crawl + clusters) + compression si > 2 cellules pour éviter JSON tronqué au rechargement."},
    {"version": "3.0.70", "date": "2026-02-16", "note": "Graphes : point (?) avec tableau comparatif Audit GEO vs JSON-LD au survol (section Maillage + Vue d'ensemble)."},
    {"version": "3.0.69", "date": "2026-02-16", "note": "Playwright V2 : auto-install Chromium au démarrage (app.py) pour faciliter les tests du moteur Crawl4AI."},
    {"version": "3.0.68", "date": "2026-02-16", "note": "Scraping : toggle V1 Selenium / V2 Crawl4AI dans les écrans de scrape (Audit, JSON-LD, debug, off-page, eco, master)."},
    {"version": "3.0.67", "date": "2026-02-16", "note": "Scrape unifié : fallback Vue d'ensemble si erreur clustering/Mistral (toujours remplir JSON-LD)."},
    {"version": "3.0.66", "date": "2026-02-16", "note": "Un seul scrape (Audit ou JSON-LD) remplit Audit GEO + Vue d'ensemble. Une sauvegarde enregistre les deux."},
    {"version": "3.0.65", "date": "2026-02-16 18:00", "note": "Vue d'ensemble : affichage du JSON-LD Master (avec modifs) sur le nœud central."},
    {"version": "3.0.64", "date": "2026-02-16 18:00", "note": "Vue d'ensemble : bloc Votre Master visible (nœud central), entité + URL + template."},
    {"version": "3.0.63", "date": "2026-02-16 17:00", "note": "MASTER : page = URL du site (nœud central noir) uniquement, plus de liste."},
    {"version": "3.0.62", "date": "2026-02-16 16:00", "note": "Vue d'ensemble : nœud central = page du site (Master), pas un cluster. Clic nœud central ou menu."},
    {"version": "3.0.61", "date": "2026-02-16 15:00", "note": "Vue d'ensemble = onglet principal. Bouton Valider page Master. Clic nœud met à jour Détails. MASTER/LEAF liés."},
    {"version": "3.0.60", "date": "2026-02-16 14:00", "note": "VUE ENSEMBLE: onglet renommé, JSON-LD actuel/optimisé au clic nœud, nœuds en dégradé de bleus."},
    {"version": "3.0.59", "date": "2026-02-16 12:00", "note": "JSON-LD: 3 onglets TRANSFORMER / MASTER / LEAF. Master: sélecteur page + reset. Fusion intelligente dans LEAF."},
    {"version": "3.0.58", "date": "2026-02-16 08:29", "note": "Home : affichage du README.md sur la page d'accueil."},
    {"version": "3.0.57", "date": "2026-02-16 08:15", "note": "JSON-LD: init master_data (fix ouverture onglet MASTER depuis Analyse). Revue modules."},
    {"version": "3.0.56", "date": "2026-02-16", "note": "Analyse JSON-LD : module Master intégré en onglet (GRAPHE > MASTER > TABLEAU). Sélection nœud principal par défaut."},
]
