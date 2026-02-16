# HOTARU — Version affichée dans l'app (header + footer + home)
# À chaque push : incrémenter VERSION, mettre à jour RELEASE_NOTE et prépendre à RELEASE_HISTORY.

import datetime

VERSION = "3.0.60"
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
RELEASE_NOTE = "VUE ENSEMBLE: onglet renommé, JSON-LD actuel/optimisé au clic sur nœud, nœuds en dégradé de bleus."

# Historique des notes de version (précédentes uniquement, plus récente en premier) — date/heure de release
RELEASE_HISTORY = [
    {"version": "3.0.59", "date": "2026-02-16 12:00", "note": "JSON-LD: 3 onglets TRANSFORMER / MASTER / LEAF. Master: sélecteur page + reset. Fusion intelligente dans LEAF."},
    {"version": "3.0.58", "date": "2026-02-16 08:29", "note": "Home : affichage du README.md sur la page d'accueil."},
    {"version": "3.0.57", "date": "2026-02-16 08:15", "note": "JSON-LD: init master_data (fix ouverture onglet MASTER depuis Analyse). Revue modules."},
    {"version": "3.0.56", "date": "2026-02-16", "note": "Analyse JSON-LD : module Master intégré en onglet (GRAPHE > MASTER > TABLEAU). Sélection nœud principal par défaut."},
]
