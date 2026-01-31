"""
HOTARU - Audit GEO Module (v0.9.5 - DATA VIZ PREMIUM)
Style: Compact, Iconique & Intelligent.
Correction: Gestion des gros volumes via "Smart Grouping".
"""

import streamlit as st
import networkx as nx
from pyvis.network import Network 
import streamlit.components.v1 as components
from core.database import AuditDatabase
from urllib.parse import urlparse

try:
    from core.scraping import SmartScraper
except ImportError as e:
    st.error(f"Erreur d'import critique : {e}")
    st.stop()

# --- INIT ---
def init_session_state():
    if 'audit_results' not in st.session_state: st.session_state['audit_results'] = None
    if 'current_graph' not in st.session_state: st.session_state['current_graph'] = None
    if 'current_stats' not in st.session_state: st.session_state['current_stats'] = None

# --- RENDU GRAPHIQUE HAUT DE GAMME ---
def render_interactive_graph(G):
    if G is None or len(G.nodes) == 0:
        st.warning("⚠️ Graphe vide.")
        return

    # Configuration PyVis "Premium"
    nt = Network(height="850px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)

    # OPTIONS DE PHYSIQUE & DESIGN (Le secret du rendu)
    nt.set_options("""
    var options = {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "hubsize", 
          "nodeSpacing": 150,
          "levelSeparation": 250,
          "treeSpacing": 200,
          "blockShifting": true,
          "edgeMinimization": true,
          "parentCentralization": true
        }
      },
      "nodes": {
        "shape": "dot",
        "font": { "face": "Roboto", "size": 14, "color": "#333" },
        "borderWidth": 2,
        "shadow": true
      },
      "edges": {
        "color": { "color": "#b0bec5", "highlight": "#000000" },
        "width": 1.5,
        "smooth": { "type": "cubicBezier", "roundness": 0.4 }
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": true,
        "zoomView": true
      }
    }
    """)

    try:
        path = "temp_graph.html"
        nt.save_graph(path)
        with open(path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Script JS : Zoom Fit automatique + Ouverture Liens
        js_fix = """
        <script type="text/javascript">
            network.once("stabilizationIterationsDone", function() {
                network.fit({
                    animation: { duration: 1000, easingFunction: "easeInOutQuad" }
                });
            });
            
            network.on("click", function (params) {
                if (params.nodes.length > 0) {
                    var nodeId = params.nodes[0];
                    var nodeData = nodes.get(nodeId);
                    if (nodeData.url && nodeData.url.startsWith("http")) {
                        window.open(nodeData.url, '_blank');
                    }
                }
            });
        </script>
        </body>
        """
        html_content = html_content.replace("</body>", js_fix)
        components.html(html_content, height=900, scrolling=False)
        
    except Exception as e:
        st.error(f"Erreur d'affichage : {e}")

# --- INTELLIGENCE DE CONSTRUCTION (SMART GROUPING) ---
def build_pro_graph(site_url, pages, clusters):
    G = nx.DiGraph()
    root_label = urlparse(site_url).netloc.replace('www.', '')
    
    # 1. RACINE (Style "Serveur Central")
    G.add_node("root", 
               label=f"🌐 {root_label}", 
               title="Page d'accueil", 
               color="#212121", # Noir profond
               shape="box",
               font={'color': 'white', 'size': 22})
    
    # 2. TRAITEMENT DES DOSSIERS
    for c in clusters:
        c_name = c['name'].capitalize()
        c_count = c['count']
        c_id = f"group_{c_name}"
        
        # Style du dossier (Jaune Or)
        G.add_node(c_id, 
                   label=f"📂 {c_name}\n({c_count})", 
                   color="#FFD700", 
                   shape="box", 
                   font={'size': 18, 'face': 'Arial', 'weight': 'bold'},
                   level=1) # Force le niveau hiérarchique
        
        G.add_edge("root", c_id, color="#424242", width=3)
        
        # 3. SMART GROUPING (C'est ici que la magie opère)
        # On n'affiche que les 8 premières pages pour éviter l'effet "Ligne Plate"
        MAX_VISIBLE_PAGES = 8
        
        visible_pages = c['samples'][:MAX_VISIBLE_PAGES]
        hidden_count = c_count - MAX_VISIBLE_PAGES
        
        for p in visible_pages:
            p_id = p['url']
            p_title = p['title'][:25] + ".." if len(p['title']) > 25 else p['title']
            
            # Style Page (Point blanc cerclé)
            G.add_node(p_id, 
                       label=p_title, 
                       title=p['title'], 
                       url=p['url'], 
                       shape="dot", 
                       size=10, 
                       color="#ffffff",
                       borderWidth=1,
                       shapeProperties={'borderDashes': False},
                       font={'size': 12, 'color': '#666'},
                       level=2)
            
            G.add_edge(c_id, p_id, color="#cfd8dc")
            
        # Si trop de pages, on crée un nœud "Groupe"
        if hidden_count > 0:
            more_id = f"{c_id}_more"
            G.add_node(more_id, 
                       label=f"+ {hidden_count} autres pages", 
                       title="Pages masquées pour la clarté", 
                       shape="ellipse", 
                       color="#e0e0e0", 
                       font={'size': 12, 'color': '#666'},
                       level=2)
            G.add_edge(c_id, more_id, color="#cfd8dc", style="dashed")

    return G

# --- UI ---
def render_audit_geo():
    init_session_state()
    st.markdown("## 🔍 Audit & Cartographie")
    
    db = AuditDatabase()
    user_email = st.session_state.get('user_email', 'demo@hotaru.app')

    # CONTROLES
    c1, c2 = st.columns([4, 1])
    with c1:
        url_val = st.session_state.get('audit_url_input', '')
        url = st.text_input("URL", value=url_val, placeholder="https://exemple.com")
    with c2:
        launch = st.button("🚀 Analyser", use_container_width=True, type="primary")

    # ZONE DE CHARGEMENT / SAUVEGARDE
    with st.container():
        cols = st.columns([2, 1, 1])
        with cols[0]:
            # Charger
            audits = db.load_user_audits(user_email)
            if audits:
                opts = {f"{a['date']} - {a['site_url']}": a for a in audits}
                sel = st.selectbox("Historique", list(opts.keys()), label_visibility="collapsed", placeholder="Charger un audit...")
                if st.button("📂 Ouvrir"):
                    st.session_state.audit_url_input = opts[sel]['site_url']
                    st.rerun()
            else:
                st.info("Connectez Google Sheets pour l'historique.")

    # LOGIQUE
    if launch and url:
        status = st.empty()
        progress = st.progress(0)
        try:
            status.info("🕷️ Scraping Intelligent...")
            scraper = SmartScraper(base_url=url, max_urls=300)
            results, stats = scraper.run_analysis(lambda m, v: progress.progress(v, text=m))
            
            status.info("🎨 Optimisation Data Viz...")
            clusters = scraper.get_pattern_summary()
            G = build_pro_graph(url, results, clusters)
            
            st.session_state.current_graph = G
            st.session_state.current_stats = stats
            status.success("Terminé !")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")

    # RESULTATS
    if st.session_state.current_graph:
        G = st.session_state.current_graph
        stats = st.session_state.current_stats
        
        st.markdown("---")
        
        # Barre d'info stylée
        k1, k2, k3 = st.columns(3)
        k1.metric("Pages Analysées", stats.get('total_urls', 0))
        k2.metric("Sections Clés", stats.get('patterns', 0))
        
        with k3:
            # Bouton SAUVEGARDE (Rouge si erreur, Vert si OK)
            if st.button("💾 Sauvegarder sur Drive", type="secondary"):
                try:
                    success = db.save_audit(user_email, url, {"nodes": len(G.nodes)}, stats)
                    if success:
                        st.toast("Sauvegardé avec succès !", icon="✅")
                    else:
                        st.error("Échec sauvegarde. Vérifiez le partage du Google Sheet.")
                except Exception as ex:
                    st.error(f"Erreur technique : {ex}")

        st.markdown("### 🗺️ Vue Sémantique")
        render_interactive_graph(G)
