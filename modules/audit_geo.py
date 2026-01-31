"""
HOTARU - Audit GEO Module (v0.9.1)
CORRECTION : Import PyVis standard (Fix ModuleNotFoundError)
"""

import streamlit as st
import networkx as nx
# --- CORRECTION ICI : On n'utilise plus 'st_pyvis' mais 'pyvis' ---
from pyvis.network import Network 
import streamlit.components.v1 as components
import json
from core.database import AuditDatabase
from urllib.parse import urlparse

# --- IMPORTS SÉCURISÉS ---
try:
    from core.scraping import SmartScraper
    from core.ai_clustering import analyze_clusters_with_mistral
except ImportError as e:
    st.error(f"Erreur d'import critique : {e}")
    st.stop()

# --- INITIALISATION ---
def init_session_state():
    defaults = {
        'audit_results': None,
        'current_graph': None,
        'current_stats': None,
        'current_clusters': None,
        'mistral_api_key': ''
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# --- RENDU GRAPHIQUE (FIX CLIC & DESIGN) ---
def render_interactive_graph(G):
    """
    Génère et affiche le graphe PyVis.
    """
    if G is None: return

    # --- CORRECTION ICI : Utilisation de Network() direct ---
    nt = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black")
    nt.from_nx(G)

    # Configuration Physique (Stacking propre)
    nt.set_options("""
    var options = {
      "nodes": {
        "shape": "box",
        "font": { "size": 16, "face": "sans-serif" },
        "borderWidth": 2
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -3000,
          "centralGravity": 0.3,
          "springLength": 200,
          "damping": 0.09
        },
        "minVelocity": 0.75
      }
    }
    """)

    # Génération HTML & Injection JS (Fix Clic)
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

        components.html(html_content, height=800, scrolling=True)
        
    except Exception as e:
        st.error(f"Erreur de rendu graphique : {e}")

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
            # Grosse section -> On fait UNE PILE
            label = f"📚 {c_name}\n({c_count} pages)"
            # On crée un tooltip avec les 10 premiers titres pour voir ce qu'il y a dedans
            samples_titles = [p['title'] for p in c['samples'][:10] if 'title' in p]
            title_hover = "\n".join(samples_titles) + "\n..."
            
            G.add_node(c_id, label=label, title=title_hover, color="#FFD700", shape="box", value=c_count)
            G.add_edge("root", c_id)
            
        else:
            # Petite section -> On dessine les feuilles
            G.add_node(c_id, label=f"📂 {c_name}", color="#e0e0e0", shape="box")
            G.add_edge("root", c_id)
            
            for p in c['samples']:
                p_id = p['url']
                # On utilise le vrai titre s'il existe
                raw_title = p.get('title', 'Page sans titre')
                p_label = raw_title[:20] + ".." if len(raw_title) > 20 else raw_title
                
                G.add_node(p_id, label=p_label, title=raw_title, url=p['url'], shape="ellipse", color="white")
                G.add_edge(c_id, p_id)
                
    return G

# --- LOGIQUE PRINCIPALE ---
def render_audit_geo():
    init_session_state()
    st.markdown("## 🔍 Audit & Cartographie")
    
    db = AuditDatabase()
    user_email = st.session_state.get('user_email', 'demo@hotaru.app')

    # --- ZONE DE CHARGEMENT ---
    with st.expander("📂 Charger un audit précédent", expanded=False):
        audits = db.load_user_audits(user_email)
        if audits:
            # On crée un dictionnaire pour lier le texte affiché à l'objet audit
            opts = {f"{a['date']} - {a['site_url']}": a for a in audits}
            selection = st.selectbox("Choisir un audit", list(opts.keys()))
            
            if st.button("Charger l'audit sélectionné"):
                chosen = opts[selection]
                st.session_state.audit_url_input = chosen['site_url']
                st.info("⚠️ Le rechargement complet du JSON sera activé dans la v1.0. Relancez l'analyse pour l'instant.")
        else:
            st.info("Aucun historique trouvé pour cet utilisateur.")

    # --- BARRE D'OUTILS ---
    col1, col2 = st.columns([4, 1])
    with col1:
        # Valeur par défaut
        url_val = st.session_state.get('audit_url_input', '')
        url = st.text_input("URL cible", value=url_val, placeholder="https://exemple.com", key="audit_url_input_real")
    with col2:
        analyze_btn = st.button("Lancer l'Audit 🚀", use_container_width=True)

    # --- LANCEMENT ANALYSE ---
    if analyze_btn and url:
        status = st.empty()
        progress = st.progress(0)
        
        try:
            status.info("🚀 Crawling intelligent (Links & Titles)...")
            
            # Appel au scraper Hybride
            scraper = SmartScraper(base_url=url, max_urls=150) # Limité à 150 pour la démo
            results, stats = scraper.run_analysis(progress_callback=lambda m, v: progress.progress(v, text=m))
            
            status.info("📐 Construction des Stacks...")
            clusters = scraper.get_pattern_summary()
            
            # Construction du graphe Stack
            G = build_stack_graph(url, results, clusters)
            
            # Sauvegarde Session
            st.session_state.current_graph = G
            st.session_state.current_stats = stats
            st.session_state.current_clusters = clusters
            
            status.success("Terminé !")
            st.rerun()
            
        except Exception as e:
            st.error(f"Erreur durant l'audit : {e}")

    # --- AFFICHAGE RESULTATS ---
    if 'current_graph' in st.session_state and st.session_state.current_graph:
        G = st.session_state.current_graph
        stats = st.session_state.current_stats or {}
        
        st.markdown("---")
        
        # Métriques
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pages Scannées", stats.get('total_urls', 0))
        c2.metric("Stacks (Groupes)", stats.get('patterns', 0))
        
        with c3:
            if st.button("💾 Sauvegarder"):
                # On sauvegarde juste les stats pour l'instant, le JSON graph viendra après
                graph_meta = {"nodes": len(G.nodes), "edges": len(G.edges)}
                if db.save_audit(user_email, url, graph_meta, stats):
                    st.toast("Audit sauvegardé dans Google Sheets !", icon="✅")
                else:
                    st.error("Erreur sauvegarde (Vérifiez la connexion GSheets)")

        with c4:
            if st.button("✨ IA Naming"):
                # Placeholder pour l'appel IA
                st.info("L'IA renommerait les Stacks ici (Connecter API Mistral).")

        # Rendu du graphe
        st.markdown("### 🗺️ Cartographie Sémantique")
        render_interactive_graph(G)
