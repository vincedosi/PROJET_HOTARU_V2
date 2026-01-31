"""
HOTARU - Audit GEO Module (v0.9.4 - FIX DISPLAY)
Objectif : Rendre le graphe visible à tout prix.
"""

import streamlit as st
import networkx as nx
from pyvis.network import Network 
import streamlit.components.v1 as components
from core.database import AuditDatabase
from urllib.parse import urlparse

# Import sécurisé
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

# --- RENDU GRAPHIQUE ROBUSTE ---
def render_interactive_graph(G):
    if G is None or len(G.nodes) == 0:
        st.warning("⚠️ Le graphe est vide. Aucune page trouvée.")
        return

    # Debug visible pour rassurer l'utilisateur
    st.caption(f"✅ Affichage de {len(G.nodes)} nœuds et {len(G.edges)} liens.")

    # 1. Configuration PyVis
    nt = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)

    # 2. Options de Visibilité (Centrage forcé)
    nt.set_options("""
    var options = {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed",
          "nodeSpacing": 200,
          "levelSeparation": 200
        }
      },
      "interaction": {
        "dragNodes": true,
        "dragView": true,
        "zoomView": true,
        "navigationButtons": true
      },
      "physics": {
        "hierarchicalRepulsion": {
          "nodeDistance": 250,
          "damping": 0.1
        },
        "minVelocity": 0.75,
        "solver": "hierarchicalRepulsion"
      }
    }
    """)

    # 3. Injection HTML + Fix JS
    try:
        path = "temp_graph.html"
        nt.save_graph(path)
        with open(path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Script pour forcer le zoom Fit et le clic
        js_fix = """
        <script type="text/javascript">
            // Force le centrage au démarrage
            network.once("stabilizationIterationsDone", function() {
                network.fit();
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
        
        # Rendu final
        components.html(html_content, height=850, scrolling=False)
        
    except Exception as e:
        st.error(f"Erreur d'affichage : {e}")

# --- CONSTRUCTION DU GRAPHE (SANS FILTRES CACHÉS) ---
def build_pro_graph(site_url, pages, clusters):
    G = nx.DiGraph()
    
    # Nettoyage de l'URL racine pour le label
    parsed = urlparse(site_url)
    root_label = parsed.netloc.replace('www.', '')
    
    # 1. RACINE
    G.add_node("root", 
               label=root_label.upper(), 
               title="Accueil", 
               color="#000000", 
               font={'color': 'white', 'size': 20},
               shape="box")
    
    # 2. BRANCHES (CLUSTERS)
    for c in clusters:
        c_name = c['name'].capitalize()
        c_count = c['count']
        c_id = f"group_{c_name}"
        
        # ON AFFICHE TOUT (Plus de if c_count > 3)
        # Mais on adapte la taille selon l'importance
        is_big = c_count > 5
        
        node_color = "#ffffff" if is_big else "#f0f0f0"
        node_size = 30 if is_big else 20
        font_weight = "bold" if is_big else "normal"
        
        label = f"{c_name}\n({c_count})"
        
        G.add_node(c_id, 
                   label=label, 
                   color=node_color, 
                   shape="box", 
                   font={'face': 'Arial', 'weight': font_weight},
                   borderWidth=2)
        
        G.add_edge("root", c_id, color="#333333", width=2)
        
        # 3. FEUILLES (PAGES)
        # On limite l'affichage des enfants pour ne pas crasher le navigateur si > 50 pages
        max_display = 30
        pages_to_show = c['samples'][:max_display]
        
        for p in pages_to_show:
            p_id = p['url']
            # Petit point gris
            G.add_node(p_id, 
                       label=" ", # Invisible par défaut pour clarté
                       title=p['title'], # Visible au survol
                       url=p['url'], 
                       shape="dot", 
                       size=8, 
                       color="#aaaaaa")
            
            G.add_edge(c_id, p_id, color="#dddddd", width=1)
            
    return G

# --- INTERFACE ---
def render_audit_geo():
    init_session_state()
    st.markdown("## 🔍 Audit & Cartographie")
    
    db = AuditDatabase()
    user_email = st.session_state.get('user_email', 'demo@hotaru.app')

    # Barre de contrôle
    c1, c2 = st.columns([4, 1])
    with c1:
        url_val = st.session_state.get('audit_url_input', '')
        url = st.text_input("URL", value=url_val, placeholder="https://exemple.com")
    with c2:
        launch = st.button("🚀 Analyser", use_container_width=True, type="primary")

    # Zone Historique
    with st.expander("📂 Charger un audit précédent"):
        audits = db.load_user_audits(user_email)
        if audits:
            opts = {f"{a['date']} - {a['site_url']}": a for a in audits}
            sel = st.selectbox("Choisir", list(opts.keys()), label_visibility="collapsed")
            if st.button("Charger"):
                st.session_state.audit_url_input = opts[sel]['site_url']
                st.rerun()
        else:
            st.caption("Aucun historique.")

    # Logique
    if launch and url:
        status = st.empty()
        progress = st.progress(0)
        
        try:
            status.info("🕷️ Scraping en cours...")
            # Au lieu de 300 ou 500, mets 30 ou 50
            scraper = SmartScraper(base_url=url, max_urls=50)
            # scraper = SmartScraper(base_url=url, max_urls=300)
            results, stats = scraper.run_analysis(lambda m, v: progress.progress(v, text=m))
            
            status.info("📐 Génération du graphe...")
            clusters = scraper.get_pattern_summary()
            G = build_pro_graph(url, results, clusters)
            
            st.session_state.current_graph = G
            st.session_state.current_stats = stats
            
            status.success("Terminé !")
            st.rerun()
            
        except Exception as e:
            st.error(f"Erreur : {e}")

    # Résultat
    if st.session_state.current_graph:
        G = st.session_state.current_graph
        stats = st.session_state.current_stats
        
        st.markdown("---")
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Pages", stats.get('total_urls', 0))
        k2.metric("Dossiers", stats.get('patterns', 0))
        with k3:
            if st.button("💾 Sauvegarder"):
                db.save_audit(user_email, url, {"nodes": len(G.nodes)}, stats)
                st.toast("Sauvegardé !")
        
        render_interactive_graph(G)
