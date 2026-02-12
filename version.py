# HOTARU — Version affichée dans l'app (header + footer + home)
# VERSION : incrémenter à chaque push/PR. BUILD_DATE : heure système au chargement.

VERSION = "3.0.35"
import datetime
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
RELEASE_NOTE = "Fix database: initialisation sheet_file pour éviter AttributeError sur fusion clusters."
