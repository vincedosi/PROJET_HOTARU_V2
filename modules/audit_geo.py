"""
HOTARU - Audit GEO Module (v0.9.2)
CORRECTION : Maillage interne (Connexions) + Titres Propres
"""

import streamlit as st
import networkx as nx
from pyvis.network import Network 
import streamlit.components.v1 as components
from core.database import AuditDatabase
from urllib.parse import urlparse

# --- IMPORTS SÉCURISÉS ---
try:
    from core.scraping import SmartScraper
except ImportError as e:
    st.error(f"Erreur d'import critique : {e}")
    st.stop()

# --- INITIALISATION ---
def init_session_state():
    defaults = {
        'audit_results': None,
        'current_graph': None,
        'current_stats': None,
        'current_clusters': None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# --- RENDU GRAPHIQUE ---
def render_interactive_graph(G):
    if G is None: return

    nt = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="black")
    nt.from_nx(G)

    # Physique adaptée pour le maillage (éviter que tout s'emmêle)
    nt.set_options("""
    var options = {
      "nodes": {
        "shape": "box",
        "font": { "size": 14, "face": "sans-serif" },
        "borderWidth": 1
      },
      "edges": {
        "smooth": { "type": "continuous", "roundness": 0 }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": { "iterations": 150 }
      }
    }
    """)

    try:
        path = "temp_graph.html"
        nt.save_graph(path)
        with open(path, "r", encoding="utf-8") as f:
            html_content = f.read()

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
        components.html(html_content, height=850, scrolling=True)
        
    except Exception as e:
        st.error(f"Erreur rendu: {e}")

# --- CONSTRUCTEUR DE GRAPHE "MAILLAGE" ---
def build_stack_graph(site_url, pages, clusters):
    G = nx.DiGraph()
    root_label = urlparse(site_url).netloc
    
    # Dictionnaire rapide pour vérifier l'existence des noeuds
    existing_nodes = set()

    # 1. Noeud Racine
    G.add_node("root", label=f"🏠 {root_label}", color="#000000", shape="box", title="Accueil", font={'color': 'white'})
    existing_nodes.add("root")
    
    # 2. Création des CLUSTERS et PAGES
    for c in clusters:
        c_name = c['name'].capitalize()
        c_count = c['count']
        c_id = f"group_{c_name}"
        
        # A. GROS CLUSTER (>5 pages) -> On fait une PILE
        if c_count > 5:
            label = f"📚 {c_name}\n({c_count})"
            samples_titles = [p['title'] for p in c['samples'][:15]]
            title_hover = "\n".join(samples_titles)
            
            G.add_node(c_id, label=label, title=title_hover, color="#FFD700", shape="box", value=c_count*2)
            G.add_edge("root", c_id, color="#000000", width=2) # Lien structurel fort
            existing_nodes.add(c_id)
            
        # B. PETIT CLUSTER -> On affiche les FEUILLES
        else:
            # Le dossier
            G.add_node(c_id, label=f"📂 {c_name}", color="#e0e0e0", shape="box")
            G.add_edge("root", c_id, color="#000000", width=2)
            existing_nodes.add(c_id)
            
            # Les pages enfants
            for p in c['samples']:
                p_id = p['url']
                p_label = p['title'][:25] + ".." if len(p['title']) > 25 else p['title']
                
                G.add_node(p_id, label=p_label, title=p['title'], url=p['url'], shape="ellipse", color="white")
                G.add_edge(c_id, p_id, color="#666666") # Lien hiérarchique
                existing_nodes.add(p_id)

    # 3. AJOUT DU MAILLAGE (Liens internes entre pages existantes)
    # C'est ça qui fait les "connexions" que tu demandais !
    for p in pages:
        source_id = p['url']
        
        # Si la page source est affichée (c'est-à-dire pas cachée dans une Pile)
        if source_id in existing_nodes:
            for target_link in p['links']:
                # Si la cible est aussi affichée
                if target_link in existing_nodes and target_link != source_id:
                    # On crée une arête GRISE et FINE
                    G.add_edge(source_id, target_link, color="#dddddd", width=0.5, style="dashed")

    return G

# --- LOGIQUE PRINCIPALE ---
def render_audit_geo():
    init_session_state()
    st.markdown("## 🔍 Audit & Maillage")
    
    db = AuditDatabase()
    user_email = st.session_state.get('user_email', 'demo@hotaru.app')

    # Chargement
    with st.expander("📂 Historique", expanded=False):
        audits = db.load_user_audits(user_email)
        if audits:
            opts = {f"{a['date']} - {a['site_url']}": a for a in audits}
            selection = st.selectbox("Choisir un audit", list(opts.keys()))
            if st.button("Charger"):
                st.session_state.audit_url_input = opts[selection]['site_url']

    # Input
    c1, c2 = st.columns([4, 1])
    with c1:
        url_val = st.session_state.get('audit_url_input', '')
        url = st.text_input("URL", value=url_val, placeholder="https://exemple.com")
    with c2:
        launch = st.button("🚀 Audit Complet", use_container_width=True)

    # Lancement
    if launch and url:
        status = st.empty()
        progress = st.progress(0)
        
        try:
            status.info("🕷️ Scraping profond + Nettoyage Titres...")
            
            # Augmentation de la profondeur
            scraper = SmartScraper(base_url=url, max_urls=300) 
            results, stats = scraper.run_analysis(lambda m, v: progress.progress(v, text=m))
            
            status.info("🕸️ Calcul du maillage interne...")
            clusters = scraper.get_pattern_summary()
            
            # Graphe avec Maillage
            G = build_stack_graph(url, results, clusters)
            
            st.session_state.current_graph = G
            st.session_state.current_stats = stats
            
            status.success("Terminé !")
            st.rerun()
            
        except Exception as e:
            st.error(f"Erreur : {e}")

    # Rendu
    if st.session_state.current_graph:
        G = st.session_state.current_graph
        stats = st.session_state.current_stats or {}
        
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Pages", stats.get('total_urls', 0))
        c2.metric("Groupes", stats.get('patterns', 0))
        with c3:
            if st.button("💾 Sauvegarder"):
                 db.save_audit(user_email, url, {"nodes": len(G.nodes)}, stats)
                 st.toast("Sauvegardé !")

        st.markdown("### 🗺️ Cartographie (Zoomable)")
        render_interactive_graph(G)
