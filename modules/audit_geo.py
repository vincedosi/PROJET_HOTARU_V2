"""
AUDIT GEO MODULE
- Graphe avec "Stacks" (Piles) pour éviter le spaghetti
- Sauvegarde / Chargement GSheets
- Titres réels sur les noeuds
"""
import streamlit as st
import networkx as nx
from st_pyvis import network as net
import streamlit.components.v1 as components
import json
from core.database import AuditDatabase

# --- IMPORTS ---
try:
    from core.scraping import SmartScraper
    from core.ai_clustering import analyze_clusters_with_mistral
except ImportError as e:
    st.error(f"Erreur import: {e}")
    st.stop()

# --- GESTION GRAPHISME (STACKS) ---
def render_interactive_graph(G):
    """Affiche le graphe PyVis propre."""
    if G is None: return

    # Configuration PyVis Plein Écran & Physique
    nt = net.Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black")
    nt.from_nx(G)

    # Options Physics pour espacer les piles
    nt.set_options("""
    var options = {
      "nodes": {
        "shape": "box",
        "font": { "size": 16, "face": "sans-serif" },
        "borderWidth": 2
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -2000,
          "centralGravity": 0.3,
          "springLength": 200
        },
        "minVelocity": 0.75
      }
    }
    """)

    # Fix Click JS
    path = "temp_graph.html"
    nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
        
    js_fix = """
    <script>
        network.on("click", function (params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                if (node.url) window.open(node.url, '_blank');
            }
        });
    </script></body>
    """
    html = html.replace("</body>", js_fix)
    components.html(html, height=800, scrolling=True)

# --- CONSTRUCTEUR DE GRAPHE "STACK" ---
def build_stack_graph(site_url, pages, clusters):
    """
    Construit un graphe où les groupes > 5 pages deviennent des 'Piles'.
    """
    G = nx.DiGraph()
    root_label = urlparse(site_url).netloc
    
    # 1. Noeud Racine
    G.add_node("root", label=f"🏠 {root_label}", color="black", shape="box", title="Accueil", font={'color': 'white'})
    
    # 2. Traitement des Clusters
    for c in clusters:
        c_name = c['name'].capitalize()
        c_count = c['count']
        c_id = f"group_{c_name}"
        
        # LOGIQUE DE PILE (STACK)
        if c_count > 5:
            # C'est une grosse section -> On fait UNE PILE
            # On ne dessine PAS les 50 enfants, on fait un gros noeud
            label = f"📚 {c_name}\n({c_count} pages)"
            title_hover = "\n".join([f"- {p['title']}" for p in c['samples'][:10]]) + "\n..."
            
            G.add_node(c_id, label=label, title=title_hover, color="#FFD700", shape="box", value=c_count)
            G.add_edge("root", c_id)
            
        else:
            # C'est une petite section -> On dessine les feuilles
            G.add_node(c_id, label=f"📂 {c_name}", color="#e0e0e0")
            G.add_edge("root", c_id)
            
            for p in c['samples']:
                p_id = p['url']
                # ON UTILISE ENFIN LE VRAI TITRE
                p_label = p['title'][:20] + ".." if len(p['title']) > 20 else p['title']
                G.add_node(p_id, label=p_label, title=p['title'], url=p['url'], shape="ellipse", color="white")
                G.add_edge(c_id, p_id)
                
    return G

# --- PAGE PRINCIPALE ---
def render_audit_geo():
    st.markdown("## 🔍 Audit & Cartographie")
    
    db = AuditDatabase()
    user_email = st.session_state.get('user_email', 'demo@test.com')

    # --- BARRE DE CHARGEMENT (LOAD) ---
    with st.expander("📂 Charger un audit précédent", expanded=False):
        audits = db.load_user_audits(user_email)
        if audits:
            opts = {f"{a['date']} - {a['site_url']}": a for a in audits}
            selection = st.selectbox("Choisir un audit", list(opts.keys()))
            if st.button("Charger"):
                chosen = opts[selection]
                # Reconstruction des données depuis le JSON
                # Note: Simplifié pour l'exemple, idéalement on reconstruirait le graph object
                st.info("Fonction de rechargement JSON à finaliser selon format exact")
                # Pour l'instant on recharge juste l'URL pour relancer vite
                st.session_state.audit_url_input = chosen['site_url']
        else:
            st.info("Aucun historique trouvé.")

    # --- INPUT URL ---
    col1, col2 = st.columns([4, 1])
    with col1:
        url = st.text_input("URL du site", placeholder="https://...", key="audit_url_input")
    with col2:
        launch = st.button("🚀 Lancer", use_container_width=True)

    if launch and url:
        progress = st.progress(0)
        status = st.empty()
        
        try:
            status.info("🕷️ Crawling intelligent (Titres & Liens)...")
            scraper = SmartScraper(url, max_urls=100) # Max 100 pour test rapide
            results, stats = scraper.run_analysis(lambda m, v: progress.progress(v, text=m))
            
            clusters = scraper.get_pattern_summary()
            
            # Construction Graphe STACK
            G = build_stack_graph(url, results, clusters)
            
            st.session_state.current_graph = G
            st.session_state.current_results = results
            st.session_state.current_stats = stats
            st.session_state.current_clusters = clusters
            
            status.success("Terminé !")
            st.rerun()
            
        except Exception as e:
            st.error(f"Crash: {e}")

    # --- RESULTATS ---
    if 'current_graph' in st.session_state:
        G = st.session_state.current_graph
        stats = st.session_state.current_stats
        
        # Métriques
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pages", stats['total_urls'])
        c2.metric("Piles", stats['patterns'])
        
        # Bouton SAUVEGARDE
        with c3:
            if st.button("💾 Sauvegarder"):
                if db.save_audit(user_email, url, {"nodes": len(G.nodes)}, stats):
                    st.toast("Audit sauvegardé !", icon="✅")
        
        # Bouton IA
        with c4:
            if st.button("✨ IA Naming"):
                st.info("L'IA renommerait ici les piles 'Produits' en 'Meubles'...")
                # Appel à analyze_clusters_with_mistral ici
        
        st.markdown("---")
        render_interactive_graph(G)
