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
        "llms.txt": "/llms.txt" # Nouveau standard pour les IA
    }
    results = {}
    for name, path in files.items():
        try:
            r = requests.get(base_url.rstrip('/') + path, timeout=5)
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
    # JS POUR REPARER LES LIENS CLIQUABLES
    nt.set_options("""
    var options = {
        "physics": {"forceAtlas2Based": {"gravitationalConstant": -60}, "solver": "forceAtlas2Based"},
        "interaction": {"hover": true}
    }
    """)
    path = "temp_graph.html"
    nt.save_graph(path)
    
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Injection du script de clic
    click_js = """
    <script>
    network.on("click", function (params) {
        if (params.nodes.length > 0) {
            var nodeId = params.nodes[0];
            if (nodeId.startsWith('http')) { window.open(nodeId, '_blank'); }
        }
    });
    </script>
    """
    html = html.replace("</body>", click_js + "</body>")
    components.html(html, height=750)

def build_graph(site_url, pages, clusters, mode="structure"):
    G = nx.DiGraph()
    domain = urlparse(site_url).netloc
    G.add_node("root", label=domain, size=30, color="#212121", url=site_url)
    for c in clusters:
        c_id = f"group_{c['name']}"
        G.add_node(c_id, label=c['name'].upper(), color="#FFD700", size=20)
        G.add_edge("root", c_id)
        for p in c['samples'][:12]:
            lbl = get_smart_label(p['title'], p['url'], domain)
            G.add_node(p['url'], label=lbl, size=10, color="#78909c", title=p['title'])
            G.add_edge(c_id, p['url'])
    return G

def render_audit_geo():
    db = AuditDatabase()
    user_email = st.session_state.user_email
    is_admin = st.session_state.user_role == "admin"

    st.title("🔍 Audit & Intelligence GEO")

    # --- 1. GESTION DU WORKSPACE ---
    audits = db.load_user_audits(user_email, is_admin=is_admin)
    
    # Groupement par Workspace (Domaine)
    workspaces = sorted(list(set([a['workspace'] for a in audits if a['workspace']]))) if audits else []
    
    st.sidebar.title("🏢 Espaces Clients")
    if workspaces:
        selected_ws = st.sidebar.selectbox("Choisir un Client", ["Tous"] + workspaces)
        
        # Filtrage des audits pour la liste
        display_audits = audits
        if selected_ws != "Tous":
            display_audits = [a for a in audits if a['workspace'] == selected_ws]
        
        # Affichage avec Date & URL
        options = {f"📅 {a['date']} - 🌐 {a['site_url']}": a for a in display_audits}
        choice = st.sidebar.selectbox("Versions disponibles", list(options.keys()))
        
        if st.sidebar.button("📂 Restaurer"):
            data = options[choice]
            st.session_state.results = data['json_data']['results']
            st.session_state.clusters = data['json_data']['clusters']
            st.session_state.target_url = data['site_url']
            st.rerun()
    else:
        st.sidebar.info("Aucun client enregistré.")

    # --- 2. SCAN & ANALYSE IA ---
    url_input = st.text_input("URL du site", placeholder="https://...")
    if st.button("🚀 Lancer l'Analyse Complète"):
        with st.status("Audit technique IA...") as s:
            st.write("Vérification robots.txt, sitemap, llms.txt...")
            ai_files = check_ai_files(url_input)
            st.session_state.ai_files = ai_files
            
            st.write("Scraping structurel...")
            scraper = SmartScraper(url_input, max_urls=80)
            res, stats = scraper.run_analysis()
            
            st.session_state.results = res
            st.session_state.clusters = scraper.get_pattern_summary()
            st.session_state.target_url = url_input
            s.update(label="Analyse terminée !", state="complete")
        st.rerun()

    # --- 3. AFFICHAGE ---
    if "results" in st.session_state:
        # Widget IA Files
        st.markdown("### 🤖 Diagnostic Accessibilité IA")
        cols = st.columns(3)
        for i, (f, exists) in enumerate(st.session_state.get('ai_files', {}).items()):
            cols[i].metric(f, "✅ Présent" if exists else "❌ Manquant", delta=None)

        if st.button("💾 Sauvegarder dans l'Espace Client"):
            domain = urlparse(st.session_state.target_url).netloc
            payload = {
                "results": st.session_state.results, 
                "clusters": st.session_state.clusters,
                "ai_files": st.session_state.get('ai_files', {})
            }
            if db.save_audit(user_email, st.session_state.target_url, domain, payload, {}):
                st.toast(f"Sauvegardé dans le Workspace : {domain}")
                st.rerun()

        G = build_graph(st.session_state.target_url, st.session_state.results, st.session_state.clusters)
        render_interactive_graph(G)
