"""
HOTARU - Audit GEO Module (v0.9.7 - POLISHED)
Style: Organique & Robuste.
Améliorations :
1. Nettoyage intelligent des labels gris (Slug vs Titre).
2. Les dossiers jaunes sont maintenant cliquables (URL reconstruite).
"""

import streamlit as st
import networkx as nx
from pyvis.network import Network 
import streamlit.components.v1 as components
from core.database import AuditDatabase
from urllib.parse import urlparse
import re

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

    # Config Full Screen
    nt = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)

    # PHYSIQUE ORGANIQUE (Force Atlas 2)
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
          "gravitationalConstant": -80,
          "centralGravity": 0.005,
          "springLength": 120,
          "springConstant": 0.08,
          "damping": 0.4
        },
        "maxVelocity": 40,
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

        # JS : Click Handler Amélioré (Gère aussi les dossiers)
        js_fix = """
        <script type="text/javascript">
            network.once("stabilizationIterationsDone", function() {
                network.fit();
            });
            setTimeout(function() { network.fit(); }, 2000);
            
            network.on("click", function (params) {
                if (params.nodes.length > 0) {
                    var nodeId = params.nodes[0];
                    var nodeData = nodes.get(nodeId);
                    // On ouvre si une URL est attachée (Page ou Dossier)
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

# --- FONCTION NETTOYAGE LABEL ---
def get_smart_label(page_title, page_url, site_name):
    """Choisit le meilleur label entre le Titre et le Slug URL."""
    
    # 1. Nettoyage du nom de domaine dans le titre
    clean_title = page_title.lower().replace(site_name.lower(), "").strip()
    clean_title = re.sub(r'[-|_]\s*$', '', clean_title).strip() # Retire les tirets de fin
    
    # 2. Si le titre est vide ou trop court après nettoyage, on prend le SLUG
    if len(clean_title) < 3:
        # On prend le dernier bout de l'URL
        slug = page_url.rstrip('/').split('/')[-1]
        slug = slug.replace('-', ' ').replace('_', ' ').capitalize()
        # Si le slug est un chiffre ou vide (ex: index.php), on garde un truc générique
        if not slug or slug.isdigit():
            return "Page Info"
        return slug[:20]

    return page_title[:20] + ".." if len(page_title) > 20 else page_title

# --- CONSTRUCTION DU GRAPHE ---
def build_pro_graph(site_url, pages, clusters):
    G = nx.DiGraph()
    domain = urlparse(site_url).netloc.replace('www.', '')
    base_url_clean = site_url.rstrip('/')
    
    # 1. RACINE
    G.add_node("root", 
               label=domain, 
               title="Page d'accueil", 
               url=site_url, # La racine est cliquable
               color="#212121", 
               size=35,
               shape="dot",
               font={'color': 'black', 'size': 18, 'face': 'Arial', 'vadjust': -40})
    
    # 2. DOSSIERS (CLUSTERS)
    for c in clusters:
        c_name = c['name']
        c_count = c['count']
        c_id = f"group_{c_name}"
        
        # Reconstruction URL Dossier (Tentative)
        # Ex: site.com + / + metiers
        folder_url = f"{base_url_clean}/{c_name}"
        
        # Label Dossier (Capitalize)
        folder_label = c_name.capitalize().replace('-', ' ')
        
        G.add_node(c_id, 
                   label=f"{folder_label} ({c_count})", 
                   title=f"Dossier : {folder_url}", # Tooltip
                   url=folder_url, # REND LE DOSSIER CLIQUABLE !
                   color="#FFD700", 
                   shape="dot", 
                   size=25,
                   font={'size': 14, 'face': 'Arial'})
        
        G.add_edge("root", c_id, color="#90a4ae", width=1.5)
        
        # 3. PAGES (FEUILLES)
        MAX_LEAVES = 12 # Légère augmentation
        visible_pages = c['samples'][:MAX_LEAVES]
        
        for p in visible_pages:
            p_id = p['url']
            
            # --- LOGIQUE INTELLIGENTE DES LABELS ---
            smart_lbl = get_smart_label(p['title'], p['url'], domain)
            
            G.add_node(p_id, 
                       label=smart_lbl, 
                       title=p['title'], # Le titre complet reste au survol
                       url=p['url'], 
                       shape="dot", 
                       size=8, 
                       color="#78909c") # Gris Bleu
            
            G.add_edge(c_id, p_id, color="#eceff1")
            
        # Nœud "Autres"
        if c_count > MAX_LEAVES:
            more_id = f"{c_id}_more"
            hidden = c_count - MAX_LEAVES
            G.add_node(more_id, 
                       label=f"+ {hidden}", 
                       shape="dot", 
                       size=5,
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
            
            status.info("🎨 Optimisation Smart Labels...")
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

        st.markdown("### 🗺️ Vue Sémantique")
        render_interactive_graph(G)
