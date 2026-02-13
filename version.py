# HOTARU — Version affichée dans l'app (header + footer + home)
# À chaque push : incrémenter VERSION. BUILD_DATE = heure système au démarrage de l'app.

VERSION = "3.0.48"
import datetime
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
RELEASE_NOTE = "Analyse JSON-LD : nombre de pages 1 à 10 000 (palier 10)."
