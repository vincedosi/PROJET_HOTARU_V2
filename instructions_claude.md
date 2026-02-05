Markdown
# 🚨 MISSION URGENTE : RÉPARATION NAVIGATION & GRAPHE

## CONTEXTE CRITIQUE
L'application est cassée sur 3 points majeurs :
1. **Navigation :** La sidebar disparaît, on est bloqué.
2. **Interaction Graphe :** Le clic sur un nœud recharge l'app avec une erreur (URL interne) au lieu d'ouvrir le site web.
3. **Qualité des données :** Le scraper génère des noms de groupes illisibles (`?$(102)`).

## INSTRUCTIONS DE CODAGE (À EXÉCUTER DANS L'ORDRE)

### 1. FIX NAVIGATION (Dans `app.py`)
La Sidebar doit être affichée **AVANT** toute autre logique conditionnelle pour ne jamais disparaître.
**Code obligatoire :**
```python
import streamlit as st
# ... imports ...

# CONFIGURATION PAGE & CSS
st.set_page_config(layout="wide", page_title="Hotaru V3")

# --- SIDEBAR PERSISTANTE ---
with st.sidebar:
    st.image("assets/logo.png", use_container_width=True)
    st.markdown("---")
    # Navigation qui contrôle l'affichage principal
    selected_page = st.radio("Menu", ["📊 Dashboard", "🔍 Audit GEO", "⚙️ Paramètres"], key="nav_main")

# --- ROUTEUR ---
if selected_page == "📊 Dashboard":
    # call dashboard function...
elif selected_page == "🔍 Audit GEO":
    # call audit function...
# ...
2. FIX INTERACTIVITÉ GRAPHE (Dans modules/audit_geo.py)
ABANDONNE streamlit-agraph. Utilise PyVis avec injection JavaScript manuelle pour gérer le clic (window.open).

Pattern de code OBLIGATOIRE à implémenter :

Python
from st_pyvis import network as net
import streamlit.components.v1 as components

def render_interactive_graph(graph_data):
    # 1. Création du graphe PyVis
    nt = net.Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    nt.from_nx(graph_data) # Si tu utilises networkx, sinon ajoute les noeuds manuellement

    # IMPORTANT : Assure-toi que chaque noeud a l'attribut 'url'
    # ex: nt.add_node(id, label="...", title="...", url="[https://site.com/page](https://site.com/page)")

    # 2. Force layout hiérarchique (Organigramme)
    nt.hrepulsion(node_distance=120, central_gravity=0.0)
    nt.set_options("""
    var options = {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed"
        }
      }
    }
    """)

    # 3. Génération HTML & Injection JS (Le Fix Vital)
    path = "temp_graph.html"
    nt.save_graph(path)
    
    with open(path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Script JS qui intercepte le clic et ouvre l'URL
    js_click_fix = """
    <script type="text/javascript">
        network.on("click", function (params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                var nodeData = nodes.get(nodeId);
                // Vérification et ouverture
                if (nodeData.url && nodeData.url.startsWith("http")) {
                    window.open(nodeData.url, '_blank');
                } else {
                    console.log("URL manquante pour ce noeud");
                }
            }
        });
    </script>
    </body>
    """
    html_content = html_content.replace("</body>", js_click_fix)

    # 4. Rendu final
    components.html(html_content, height=650, scrolling=False)
3. FIX DASHBOARD & SAUVEGARDE (Dans modules/audit_geo.py)
Restructure la page. Si aucun audit n'est chargé, affiche :

Bouton [📂 Charger un Audit] (Ouvre un tableau des audits GSheets).

Input URL + Bouton Analyser.

Si un audit est affiché, ajoute une barre d'outils au-dessus du graphe : [💾 Sauvegarder dans GSheets] [✨ Optimiser avec IA]

4. FIX NOMMAGE SCRAPER (Dans core/scraper.py)
Corrige la regex de clustering.

Logique : Récupérer le premier segment significatif après le domaine.

Nettoyage : Supprimer chiffres et caractères spéciaux.

Exemple : site.com/offres/job-12 -> Cluster "OFFRES".

Si le nom résultant est vide ou ?, forcer le nom "DIVERS".

ACTION REQUISE
Exécute ces 4 corrections. Commence par app.py pour la Sidebar, puis modules/audit_geo.py pour le fix PyVis/JS.




Une fois le fichier enregistré, lance simplement :

> `claude "Lis instructions_claude.md et exécute scrupuleusement les 4 étapes de réparation. C'est urgent pour débloquer l'interface."`
