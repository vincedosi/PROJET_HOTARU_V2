"""
HOTARU - Audit GEO Module (v0.9.6 - FIX DISPLAY)
Style: Organique & Robuste (Force Directed).
Correction: Graphique invisible corrigé (suppression hierarchy strict).
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

# --- RENDU GRAPHIQUE ROBUSTE ---
def render_interactive_graph(G):
    if G is None or len(G.nodes) == 0:
        st.warning("⚠️ Graphe vide.")
        return

    # Configuration PyVis "Full Screen"
    nt = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)

    # OPTIONS PHYSIQUES ROBUSTES (Force Atlas 2)
    # Cela force les noeuds à rester au centre et à ne pas s'envoler
    nt.set_options("""
    var options = {
      "nodes": {
        "shape": "dot",
        "font": { "size": 14, "face": "Roboto" },
        "borderWidth": 1,
        "shadow": true
      },
      "edges": {
        "color": { "color": "#cfd8dc", "highlight": "#000000" },
        "width": 1,
        "smooth": { "type": "continuous" }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08,
          "damping": 0.4
        },
        "maxVelocity": 50,
        "minVelocity": 0.1,
        "solver": "forceAtlas2Based"
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "zoomView": true
      }
    }
    """)

    try:
        path = "temp_graph.html"
        nt.save_graph(path)
        with open(path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Fix JS : Centrage forcé après 2 secondes
        js_fix = """
        <script type="text/javascript">
            network.once("stabilizationIterationsDone", function() {
                network.fit();
            });
            // Double sécurité pour le centrage
            setTimeout(function() { network.fit(); }, 2000);
            
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
        components.html(html_content, height=850, scrolling=False)
        
    except Exception as e:
        st.error(f"Erreur d'affichage : {e}")

# --- INTELLIGENCE DE CONSTRUCTION ---
def build_pro_graph(site_url, pages, clusters):
    G = nx.DiGraph()
    root_label = urlparse(site_url).netloc.replace('www.', '')
    
    # 1. RACINE
    G.add_node("root", 
               label=root_label, 
               title="Accueil", 
               color="#212121", # Noir
               size=40,
               shape="dot",
               font={'color': 'black', 'size': 20, 'face': 'Arial', 'vadjust': -50})
    
    # 2. TRAITEMENT DES DOSSIERS
    for c in clusters:
        c_name = c['name'].capitalize()
        c_count = c['count']
        c_id = f"group_{c_name}"
        
        # COULEUR : Jaune Or pour les dossiers
        G.add_node(c_id, 
                   label=f"{c_name} ({c_count})", 
                   color="#FFD700", 
                   shape="dot", 
                   size=25,
                   font={'size': 16, 'face': 'Arial'})
        
        G.add_edge("root", c_id, color="#90a4ae", width=2)
        
        # 3. SMART GROUPING (Limiter l'affichage des feuilles)
        # On limite à 10 feuilles par branche pour éviter l'explosion
        MAX_LEAVES = 10
        visible_pages = c['samples'][:MAX_LEAVES]
        
        for p in visible_pages:
            p_id = p['url']
            p_title = p['title'][:20] + ".." if len(p['title']) > 20 else p['title']
            
            # COULEUR : Gris Bleu (Visible sur blanc !)
            # AVANT c'était #ffffff (blanc) -> Invisible
            G.add_node(p_id, 
                       label=p_title, 
                       title=p['title'], 
                       url=p['url'], 
                       shape="dot", 
                       size=10, 
                       color="#78909c") # Gris bleu visible
            
            G.add_edge(c_id, p_id, color="#eceff1")
            
        # Nœud "Autres..."
        if c_count > MAX_LEAVES:
            more_id = f"{c_id}_more"
            hidden = c_count - MAX_LEAVES
            G.add_node(more_id, 
                       label=f"+ {hidden}", 
                       shape="dot", 
                       size=8,
                       color="#e0e0e0")
            G.add_edge(c_id, more_id, style="dashed")

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

    # SAUVEGARDE / CHARGEMENT
    with st.container():
        cols = st.columns([2, 1, 1])
        with cols[0]:
            audits = db.load_user_audits(user_email)
            if audits:
                opts = {f"{a['date']} - {a['site_url']}": a for a in audits}
                sel = st.selectbox("Historique", list(opts.keys()), label_visibility="collapsed")
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
            status.info("🕷️ Scraping Intelligent (Max 300)...")
            scraper = SmartScraper(base_url=url, max_urls=300)
            results, stats = scraper.run_analysis(lambda m, v: progress.progress(v, text=m))
            
            status.info("🎨 Génération Graphe...")
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
        k1, k2, k3 = st.columns(3)
        k1.metric("Pages", stats.get('total_urls', 0))
        k2.metric("Sections", stats.get('patterns', 0))
        
        with k3:
            if st.button("💾 Sauvegarder sur Drive"):
                success = db.save_audit(user_email, url, {"nodes": len(G.nodes)}, stats)
                if success:
                    st.toast("Sauvegardé !", icon="✅")
                else:
                    st.error("Échec sauvegarde (Vérifiez partage GSheet)")

        st.markdown("### 🗺️ Vue Sémantique")
        render_interactive_graph(G)
