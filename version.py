# HOTARU — Version affichée dans l'app (header + footer + home)
# À chaque push : incrémenter VERSION. BUILD_DATE = heure système au démarrage de l'app.

VERSION = "3.0.55"
import datetime
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
RELEASE_NOTE = "Docs : versioning obligatoire (version.py à chaque merge/PR) + règle Cursor."
