"""
HOTARU - Audit GEO Module
VERSION CORRIGÉE : PyVis + JS Injection + IA Text Mode
"""

import streamlit as st
import networkx as nx
from st_pyvis import network as net
import streamlit.components.v1 as components
import json

# --- IMPORTS SÉCURISÉS ---
try:
    from core.scraping import SmartScraper
    # On importe la nouvelle fonction IA robuste (Texte Brut)
    from core.ai_clustering import analyze_clusters_with_mistral
except ImportError as e:
    st.error(f"Erreur d'import critique : {e}")
    st.stop()

# --- INITIALISATION ---
def init_session_state():
    """Initialise les variables de session."""
    defaults = {
        'audit_results': None,
        'current_graph_nx': None, # On stocke l'objet NetworkX directement
        'clusters_summary': {},   # Pour l'IA
        'ai_optimized': False,
        'mistral_api_key': ''
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# --- RENDU GRAPHIQUE (FIX CLIC & DESIGN) ---
def render_interactive_graph(G):
    """
    Génère et affiche le graphe PyVis avec le FIX JAVASCRIPT pour les clics.
    """
    if G is None or len(G.nodes) == 0:
        st.info("Aucune donnée graphique.")
        return

    # 1. Création du graphe PyVis
    nt = net.Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    nt.from_nx(G)

    # 2. Configuration Physique (Organigramme Hiérarchique)
    nt.set_options("""
    var options = {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed",
          "nodeSpacing": 150,
          "levelSeparation": 150
        }
      },
      "physics": {
        "hierarchicalRepulsion": {
          "nodeDistance": 120
        },
        "solver": "hierarchicalRepulsion"
      },
      "nodes": {
        "shape": "box",
        "font": { "size": 14, "face": "sans-serif" }
      },
      "edges": {
        "color": { "color": "#000000" },
        "smooth": { "type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.4 }
      }
    }
    """)

    # 3. Génération HTML & Injection JS (Le Fix Vital pour le Clic)
    try:
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
                    }
                }
            });
        </script>
        </body>
        """
        html_content = html_content.replace("</body>", js_click_fix)

        # 4. Rendu final
        components.html(html_content, height=650, scrolling=False)
        
    except Exception as e:
        st.error(f"Erreur de rendu graphique : {e}")

# --- LOGIQUE PRINCIPALE ---
def render_audit_geo():
    """Page principale Audit GEO."""
    init_session_state()

    st.markdown("## 🔍 Audit GEO")
    
    # Barre d'outils
    col1, col2 = st.columns([4, 1])
    with col1:
        # Valeur par défaut vide ou récupérée du state
        default_url = st.session_state.audit_results['url'] if st.session_state.audit_results else ""
        url = st.text_input("URL cible", value=default_url, placeholder="https://exemple.com", key="audit_url_input", label_visibility="collapsed")
    with col2:
        analyze_btn = st.button("Lancer l'Audit 🚀", use_container_width=True)

    if analyze_btn and url:
        run_audit(url)

    # Affichage des résultats
    if st.session_state.current_graph_nx:
        st.markdown("---")
        
        # Zone Actions
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            st.metric("Pages", len(st.session_state.current_graph_nx.nodes))
        with c2:
            st.metric("Clusters", len(st.session_state.clusters_summary))
        with c3:
            # BOUTON IA
            if not st.session_state.ai_optimized:
                if st.button("✨ Optimiser les noms (IA)", type="primary", use_container_width=True):
                    run_ai_renaming()
            else:
                st.success("✅ Optimisé par Mistral")

        # AFFICHAGE DU GRAPHE
        st.markdown("### 🗺️ Cartographie")
        render_interactive_graph(st.session_state.current_graph_nx)

# --- FONCTIONS METIER ---
def run_audit(url):
    """Lance le scraper et construit le graphe initial."""
    status = st.empty()
    progress = st.progress(0)
    
    try:
        status.info("🚀 Démarrage du scraping intelligent...")
        
        # Configuration du scraper
        scraper = SmartScraper(base_url=url, max_urls=300)
        
        # Lancement avec callback de progression
        results, stats = scraper.run_analysis(progress_callback=lambda m, v: progress.progress(v, text=m))
        
        # Construction du graphe NetworkX
        status.info("📐 Construction de l'architecture...")
        G, clusters = build_networkx_graph(url, results, scraper.get_pattern_summary())
        
        # Sauvegarde en session
        st.session_state.audit_results = results
        st.session_state.current_graph_nx = G
        st.session_state.clusters_summary = clusters # Important pour l'IA
        st.session_state.ai_optimized = False
        
        status.success("Terminé !")
        st.rerun()
        
    except Exception as e:
        st.error(f"Erreur durant l'audit : {e}")

def run_ai_renaming():
    """Appelle Mistral pour renommer les clusters."""
    if not st.session_state.get('mistral_api_key'):
        st.warning("⚠️ Clé API manquante (voir Config)")
        return

    clusters = st.session_state.get('clusters_summary', {})
    if not clusters:
        st.warning("Aucun cluster à renommer.")
        return

    with st.spinner("🧠 Mistral analyse la sémantique des groupes..."):
        # Appel à la fonction ROBUSTE (Texte Brut)
        new_names = analyze_clusters_with_mistral(clusters)
        
        if new_names:
            G = st.session_state.current_graph_nx
            count = 0
            
            # Mise à jour du graphe
            for node_id, data in G.nodes(data=True):
                group_id = data.get('group_id')
                if group_id and group_id in new_names:
                    # On met à jour le label avec l'emoji et le nom
                    new_label = f"{new_names[group_id]} ({data.get('count', 0)})"
                    G.nodes[node_id]['label'] = new_label
                    G.nodes[node_id]['title'] = new_label
                    count += 1
            
            st.session_state.current_graph_nx = G
            st.session_state.ai_optimized = True
            st.success(f"{count} groupes renommés avec succès !")
            st.rerun()
        else:
            st.error("L'IA n'a pas renvoyé de résultats.")

# --- UTILITAIRES GRAPHE ---
def build_networkx_graph(site_url, pages, patterns):
    """Convertit les résultats du scraper en objet NetworkX."""
    G = nx.DiGraph()
    clusters_data = {} # Pour l'IA
    
    # 1. Racine
    root_id = "root"
    G.add_node(root_id, label="🌐 Accueil", title=site_url, color="#000000", shape="box", url=site_url)
    
    # 2. Traitement des patterns (Clusters)
    # On trie pour garder les plus gros
    sorted_patterns = sorted(patterns, key=lambda x: -x['count'])[:15]
    
    for idx, p in enumerate(sorted_patterns):
        cluster_id = f"group_{idx}"
        pattern_name = p['name'] # Nom technique temporaire (ex: /produit/)
        count = p['count']
        samples = p.get('samples', [])
        
        # On sauvegarde les données pour l'IA
        clusters_data[cluster_id] = {
            "technical_name": pattern_name,
            "samples": samples
        }
        
        # Ajout du noeud Cluster
        label = f"📁 {pattern_name} ({count})"
        G.add_node(cluster_id, label=label, title=label, color="#FFD700", shape="box", group_id=cluster_id, count=count)
        G.add_edge(root_id, cluster_id)
        
        # Ajout des enfants (Specimens) - Max 3 pour ne pas surcharger
        for i, sample_url in enumerate(samples[:3]):
            child_id = f"{cluster_id}_p{i}"
            G.add_node(child_id, label="📄 Page", title=sample_url, color="#ffffff", shape="ellipse", url=sample_url)
            G.add_edge(cluster_id, child_id)
            
    return G, clusters_data
