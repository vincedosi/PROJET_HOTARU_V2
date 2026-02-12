# HOTARU — Version affichée dans l'app (header + footer + home)
# VERSION : incrémenter à chaque push/PR. BUILD_DATE : heure système au chargement.

VERSION = "3.0.33"
import datetime
BUILD_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
RELEASE_NOTE = "Clustering intelligent (h2/h3 ±60%), fusion manuelle clusters, indicateur variabilité DOM."
