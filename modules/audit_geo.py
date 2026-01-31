import streamlit as st
import json, re, requests
from urllib.parse import urlparse
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from core.database import AuditDatabase
from core.scraping import SmartScraper

# --- CHECK FICHIERS IA ---
def check_ai_files(base_url):
    files = {
        "robots.txt": "/robots.txt",
        "sitemap.xml": "/sitemap.xml",
        "llms.txt": "/llms.txt" 
    }
    results = {}
    for name, path in files.items():
        try:
            r = requests.get(base_url.rstrip('/') + path, timeout=3)
            results[name] = r.status_code == 200
        except:
            results[name] = False
    return results

def get_smart_label(title, url, domain):
    domain_clean = domain.split('.')[0]
    clean = re.split(r' [-|:] ', title)[0]
    if domain_clean.lower() in clean.lower() or len(clean) < 5:
        clean = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
    return clean[:25]

def render_interactive_graph(G):
    nt = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)
    
    # Configuration pour rendre les noeuds cliquables via URL
    nt.set_options("""
    {
      "physics": {"forceAtlas2Based": {"gravitationalConstant": -60}, "solver": "forceAtlas2Based"},
      "interaction": {"hover": true, "navigationButtons": true}
    }
    """)
    
    path = "temp_graph.html"
    nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Injection JS pour ouvrir les URLs au clic
    click_js = """
    <script>
    network.on("click", function (params) {
        if (params.nodes.length > 0) {
            var nodeId = params.nodes[0];
            // Si le nodeId ressemble à une URL, on l'ouvre
            if (nodeId.indexOf('http') === 0) {
                window.open(nodeId, '_blank');
            }
        }
    });
    </script>
    """
    html = html.replace("</body>", click_js + "</body>")
    components.html(html, height=750)

def build_graph(site_url, pages, clusters):
    G = nx.DiGraph()
    domain = urlparse(site_url).netloc
    # On met l'URL comme ID du noeud racine
    G.add_node(site_url, label=domain, size=30, color="#212121", title="Page d'accueil")
    
    for c in clusters:
        c_id = f"group_{c['name']}"
        G.add_node(c_id, label=c['name'].upper(), color="#FFD700", size=20)
        G.add_edge(site_url, c_id)
        
        for p in c['samples'][:15]:
            lbl = get_smart_label(p['title'], p['url'], domain)
            # L'ID du noeud EST l'URL pour le clic JS
            G.add_node(p['url'], label=lbl, size=10, color="#78909c", title=p['title'])
            G.add_edge(c_id, p['url'])
    return G

def render_audit_geo():
    db = AuditDatabase()
    user_email = st.session_state.user_email
    is_admin = st.session_state.user_role == "admin"

    st.title("🔍 Audit & Intelligence GEO")

    # --- 1. GESTION DU WORKSPACE (SAAS) ---
    st.sidebar.title("🏢 Espaces Clients")
    audits = db.load_user_audits(user_email, is_admin=is_admin)
    
    # Correction du crash KeyError
    workspaces = sorted(list(set([a.get('workspace', 'Ancien') for a in audits]))) if audits else []

    if workspaces:
        selected_ws = st.sidebar.selectbox("Filtrer par Client", ["Tous"] + workspaces)
        
        display_audits = audits
        if selected_ws != "Tous":
            display_audits = [a for a in audits if a.get('workspace') == selected_ws]
        
        # Affichage riche : Date + URL
        options = {f"📅 {a['date']} | 🌐 {a['site_url']}": a for a in display_audits}
        choice = st.sidebar.selectbox("Restaurer une version", list(options.keys()))
        
        if st.sidebar.button("📂 Charger l'audit"):
            data = options[choice]
            # On récupère le JSON décompressé par database.py
            payload = data['json_data']
            st.session_state.results = payload['results']
            st.session_state.clusters = payload['clusters']
            st.session_state.target_url = data['site_url']
            st.session_state.ai_files = payload.get('ai_files', {})
            st.rerun()
    else:
        st.sidebar.info("Aucun audit sauvegardé.")

    # --- 2. SCAN & ANALYSE ---
    url_input = st.text_input("Saisir une URL pour un nouvel audit", placeholder="https://...")
    if st.button("🚀 Lancer l'Analyse"):
        with st.status("Audit en cours...") as s:
            st.write("Vérification accessibilité IA...")
            st.session_state.ai_files = check_ai_files(url_input)
            
            st.write("Scraping et cartographie...")
            scraper = SmartScraper(url_input, max_urls=100)
            res, stats = scraper.run_analysis()
            
            st.session_state.results = res
            st.session_state.clusters = scraper.get_pattern_summary()
            st.session_state.target_url = url_input
            s.update(label="Analyse terminée !", state="complete")
        st.rerun()

    # --- 3. DASHBOARD RÉSULTATS ---
    if "results" in st.session_state:
        st.markdown("---")
        
        # Indicateurs IA
        st.subheader("🤖 Diagnostic IA (GEO Readiness)")
        cols = st.columns(3)
        files = st.session_state.get('ai_files', {})
        for i, (name, exists) in enumerate(files.items()):
            cols[i].metric(name, "✅ OK" if exists else "❌ Absent", 
                         delta="Recommandé" if not exists else None, delta_color="inverse")

        # Sauvegarde
        if st.button("💾 Sauvegarder dans l'Espace Client"):
            domain = urlparse(st.session_state.target_url).netloc
            payload = {
                "results": st.session_state.results, 
                "clusters": st.session_state.clusters,
                "ai_files": st.session_state.get('ai_files', {})
            }
            # On passe le domaine comme nom de Workspace
            if db.save_audit(user_email, st.session_state.target_url, domain, payload, {"total_urls": len(st.session_state.results)}):
                st.toast(f"Sauvegardé sous le client : {domain}")
                st.rerun()

        # Graph interactif
        G = build_graph(st.session_state.target_url, st.session_state.results, st.session_state.clusters)
        render_interactive_graph(G)
