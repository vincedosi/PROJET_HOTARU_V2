"""
HOTARU - Audit GEO Module (v0.9.3 - PRO VIZ)
Style: Zen Minimaliste (Black/Gold/White)
Layout: Hiérarchique Strict (Tree)
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

# --- INITIALISATION ---
def init_session_state():
    if 'audit_results' not in st.session_state: st.session_state['audit_results'] = None
    if 'current_graph' not in st.session_state: st.session_state['current_graph'] = None
    if 'current_stats' not in st.session_state: st.session_state['current_stats'] = None

# --- RENDU GRAPHIQUE PRO ---
def render_interactive_graph(G):
    if G is None: return

    # Hauteur augmentée et boutons de navigation activés
    nt = Network(height="850px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)

    # --- CONFIGURATION DU DESIGN "WORLD CLASS" ---
    # On active les boutons de contrôle en bas du graphe
    nt.show_buttons(filter_=['physics', 'interaction']) 
    
    nt.set_options("""
    var options = {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD", 
          "sortMethod": "directed",
          "nodeSpacing": 180,
          "levelSeparation": 200
        }
      },
      "nodes": {
        "font": { "face": "Helvetica Neue", "size": 14 },
        "shadow": { "enabled": true, "color": "rgba(0,0,0,0.1)", "size": 10 }
      },
      "edges": {
        "color": { "color": "#e0e0e0", "highlight": "#000000" },
        "width": 1,
        "smooth": { "type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.5 }
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": true
      },
      "physics": {
        "hierarchicalRepulsion": {
          "centralGravity": 0,
          "springLength": 100,
          "springConstant": 0.01,
          "nodeDistance": 180,
          "damping": 0.09
        },
        "solver": "hierarchicalRepulsion"
      }
    }
    """)

    try:
        path = "temp_graph.html"
        nt.save_graph(path)
        with open(path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Fix Click
        js_click_fix = """
        <script type="text/javascript">
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
        html_content = html_content.replace("</body>", js_click_fix)
        
        # Affichage avec scrolling activé pour le zoom
        components.html(html_content, height=900, scrolling=False)
        
    except Exception as e:
        st.error(f"Erreur rendu: {e}")

# --- CONSTRUCTION DU GRAPHE ---
def build_pro_graph(site_url, pages, clusters):
    G = nx.DiGraph()
    root_label = urlparse(site_url).netloc.replace('www.', '')
    
    # --- 1. RACINE (LE SOLEIL) ---
    G.add_node("root", 
               label=root_label.upper(), 
               title="Accueil", 
               color="#000000", # Noir mat
               font={'color': 'white', 'size': 20, 'face': 'Arial'},
               shape="box", 
               margin=15,
               borderWidth=0)
    
    # --- 2. BRANCHES (CLUSTERS) ---
    for c in clusters:
        c_name = c['name'].capitalize()
        c_count = c['count']
        c_id = f"group_{c_name}"
        
        # Si le cluster est significatif (> 3 pages)
        if c_count > 3:
            # STYLE : Boîte blanche avec bordure Or
            label = f"{c_name}\n({c_count})"
            samples = "\n".join([f"• {p['title']}" for p in c['samples'][:8]])
            
            G.add_node(c_id, 
                       label=label, 
                       title=samples, 
                       color="#ffffff", 
                       shape="box", 
                       borderWidth=2,
                       shapeProperties={'borderDashes': False},
                       font={'color': '#000000', 'face': 'Arial', 'weight': 'bold'})
            
            # Le lien Racine -> Cluster est épais
            G.add_edge("root", c_id, width=2, color="#000000")
            
            # --- 3. FEUILLES (PAGES) ---
            # Si le cluster est ÉNORME (> 20), on ne montre pas tout pour rester propre
            pages_to_show = c['samples'][:20] if c_count > 20 else c['samples']
            
            for p in pages_to_show:
                p_id = p['url']
                p_title = p['title']
                
                # STYLE : Petit point gris discret
                G.add_node(p_id, 
                           label=" ", # Pas de label pour éviter le bruit visuel (visible au survol)
                           title=p_title, # Tooltip
                           url=p['url'], 
                           shape="dot", 
                           size=8,
                           color="#888888")
                           
                G.add_edge(c_id, p_id, color="#cccccc", width=0.5)

    return G

# --- INTERFACE ---
def render_audit_geo():
    init_session_state()
    st.markdown("## 🔍 Audit & Cartographie")
    
    db = AuditDatabase()
    user_email = st.session_state.get('user_email', 'demo@hotaru.app')

    # --- INPUT BAR (Top) ---
    c1, c2 = st.columns([4, 1])
    with c1:
        url_val = st.session_state.get('audit_url_input', '')
        url = st.text_input("URL", value=url_val, placeholder="https://...", label_visibility="collapsed")
    with c2:
        launch = st.button("🚀 Analyser", use_container_width=True, type="primary")

    # --- ZONE DE CHARGEMENT / SAUVEGARDE (Plus visible) ---
    with st.container():
        cols = st.columns([1, 1, 3])
        with cols[0]:
            # CHARGEMENT
            audits = db.load_user_audits(user_email)
            if audits:
                opts = {f"{a['date']} - {a['site_url']}": a for a in audits}
                selection = st.selectbox("📂 Historique", list(opts.keys()), label_visibility="collapsed")
                if st.button("Charger l'Audit"):
                    st.session_state.audit_url_input = opts[selection]['site_url']
                    st.rerun()
            else:
                st.caption("Pas d'historique.")

    # --- LOGIQUE D'ANALYSE ---
    if launch and url:
        status = st.empty()
        progress = st.progress(0)
        
        try:
            status.info("🕷️ Scraping Profond (Max 500 URLs)...")
            scraper = SmartScraper(base_url=url, max_urls=500)
            results, stats = scraper.run_analysis(lambda m, v: progress.progress(v, text=m))
            
            status.info("📐 Organisation de l'Arborescence...")
            clusters = scraper.get_pattern_summary()
            
            # Construction PRO
            G = build_pro_graph(url, results, clusters)
            
            st.session_state.current_graph = G
            st.session_state.current_stats = stats
            
            status.success("Terminé !")
            st.rerun()
            
        except Exception as e:
            st.error(f"Erreur : {e}")

    # --- RESULTATS ---
    if st.session_state.current_graph:
        G = st.session_state.current_graph
        stats = st.session_state.current_stats or {}
        
        st.markdown("---")
        
        # Stats Bar
        kpi1, kpi2, kpi3 = st.columns([1, 1, 2])
        kpi1.metric("Pages", stats.get('total_urls', 0))
        kpi2.metric("Sections", stats.get('patterns', 0))
        
        with kpi3:
            # Bouton de sauvegarde bien visible
            if st.button("💾 Sauvegarder cet Audit"):
                 db.save_audit(user_email, url, {"nodes": len(G.nodes)}, stats)
                 st.toast("Sauvegarde réussie !", icon="✅")

        # TITRE & GRAPH
        st.markdown("### 🗺️ Structure du Site")
        st.caption("Utilisez les boutons en bas du graphe pour Zoomer / Plein écran.")
        render_interactive_graph(G)
