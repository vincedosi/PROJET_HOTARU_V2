# HOTARU — Version affichée dans l'app (header + footer + home)
# VERSION : incrémenter à chaque push/PR. BUILD_DATE : heure système au chargement.

VERSION = "3.0.38"
import datetime
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
RELEASE_NOTE = "Seuil clustering ajustable, fusion manuelle onglet dédié, prompt Mistral + fallback même nom."
