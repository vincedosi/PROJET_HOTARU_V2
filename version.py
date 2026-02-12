# HOTARU — Version affichée dans l'app (header + footer + home)
# VERSION : incrémenter à chaque push/PR. BUILD_DATE : heure système au chargement.

VERSION = "3.0.36"
import datetime
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
RELEASE_NOTE = "Expanders → onglets (Eco-Score, JSON-LD), cache audits, audit code, suppression ai_clustering."
