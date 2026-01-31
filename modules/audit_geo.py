import streamlit as st
import json, re, requests
from urllib.parse import urlparse
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from core.database import AuditDatabase
from core.scraping import SmartScraper

def check_ai_files(base_url):
    files = {"robots.txt": "/robots.txt", "sitemap.xml": "/sitemap.xml", "llms.txt": "/llms.txt"}
    results = {}
    for name, path in files.items():
        try:
            r = requests.get(base_url.rstrip('/') + path, timeout=3)
            results[name] = r.status_code == 200
        except: results[name] = False
    return results

def render_interactive_graph(G):
    nt = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)
    nt.set_options('{"physics": {"forceAtlas2Based": {"gravitationalConstant": -60}, "solver": "forceAtlas2Based"}, "interaction": {"hover": true}}')
    path = "temp_graph.html"; nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f: html = f.read()
    # Script pour liens cliquables
    click_js = """<script>network.on("click", function (params) { if (params.nodes.length > 0) { var nodeId = params.nodes[0]; if (nodeId.indexOf('http') === 0) { window.open(nodeId, '_blank'); } } });</script>"""
    components.html(html.replace("</body>", click_js + "</body>"), height=750)

def build_graph(site_url, pages, clusters):
    G = nx.DiGraph()
    domain = urlparse(site_url).netloc
    G.add_node(site_url, label=domain, size=30, color="#212121")
    for c in clusters:
        c_id = f"group_{c['name']}"
        G.add_node(c_id, label=c['name'].upper(), color="#FFD700", size=20)
        G.add_edge(site_url, c_id)
        for p in c['samples'][:15]:
            G.add_node(p['url'], label=p['title'][:25], size=10, color="#78909c")
            G.add_edge(c_id, p['url'])
    return G

def render_audit_geo():
    db = AuditDatabase()
    user_email = st.session_state.user_email
    is_admin = st.session_state.user_role == "admin"

    st.title("🔍 Audit & Intelligence GEO")

    # --- HISTORIQUE & WORKSPACES ---
    st.sidebar.title("🏢 Espaces Clients")
    audits = db.load_user_audits(user_email, is_admin=is_admin)
    
    if audits:
        # On utilise la nouvelle colonne 'workspace'
        ws_list = sorted(list(set([str(a.get('workspace', 'Non classé')) for a in audits])))
        selected_ws = st.sidebar.selectbox("Choisir un Client", ws_list)
        
        filtered = [a for a in audits if a.get('workspace') == selected_ws]
        options = {f"📅 {a['date']} | 🌐 {a['site_url']}": a for a in filtered}
        choice = st.sidebar.selectbox("Historique des versions", list(options.keys()))
        
        if st.sidebar.button("📂 Charger l'audit"):
            row = options[choice]
            decoded = base64.b64decode(row['data_compressed'])
            data = json.loads(zlib.decompress(decoded).decode('utf-8'))
            st.session_state.results = data['results']
            st.session_state.clusters = data['clusters']
            st.session_state.target_url = row['site_url']
            st.session_state.ai_files = data.get('ai_files', {})
            st.session_state.current_ws = row['workspace']
            st.rerun()
    else:
        st.sidebar.info("Aucun audit sauvegardé.")

    # --- NOUVEL AUDIT ---
    c1, c2 = st.columns([2, 1])
    with c1: url_in = st.text_input("URL à analyser", placeholder="https://...")
    with c2: ws_in = st.text_input("Nom du Client (Workspace)", placeholder="ex: Marine Nationale")

    if st.button("🚀 Lancer l'Analyse"):
        if not ws_in: st.error("Précisez un nom de client.")
        else:
            with st.status("Audit technique...") as s:
                st.session_state.ai_files = check_ai_files(url_in)
                scraper = SmartScraper(url_in, max_urls=100)
                res, stats = scraper.run_analysis()
                st.session_state.results = res
                st.session_state.clusters = scraper.get_pattern_summary()
                st.session_state.target_url = url_in
                st.session_state.current_ws = ws_in
                s.update(label="Analyse terminée !", state="complete")
            st.rerun()

    # --- RÉSULTATS ---
    if "results" in st.session_state:
        st.markdown(f"### 🤖 Dashboard Client : **{st.session_state.get('current_ws')}**")
        cols = st.columns(3)
        files = st.session_state.get('ai_files', {})
        for i, (name, exists) in enumerate(files.items()):
            cols[i].metric(name, "✅ OK" if exists else "❌ Absent")

        if st.button("💾 Sauvegarder dans cet Espace Client"):
            payload = {
                "results": st.session_state.results, 
                "clusters": st.session_state.clusters,
                "ai_files": st.session_state.get('ai_files', {})
            }
            if db.save_audit(user_email, st.session_state.current_ws, st.session_state.target_url, payload):
                st.toast("Enregistré avec succès !")
                st.rerun()

        G = build_graph(st.session_state.target_url, st.session_state.results, st.session_state.clusters)
        render_interactive_graph(G)
