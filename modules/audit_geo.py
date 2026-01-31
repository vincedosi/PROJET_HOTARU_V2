import streamlit as st
import json
import re
from urllib.parse import urlparse
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from core.database import AuditDatabase
from core.scraping import SmartScraper

def get_smart_label(title, url, domain):
    domain_clean = domain.split('.')[0]
    clean = re.split(r' [-|:] ', title)[0]
    if domain_clean.lower() in clean.lower() or len(clean) < 5:
        clean = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
        if not clean: clean = "Accueil"
    return clean[:25]

def render_interactive_graph(G):
    nt = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)
    nt.set_options('{"physics": {"forceAtlas2Based": {"gravitationalConstant": -60}, "solver": "forceAtlas2Based"}}')
    path = "temp_graph.html"
    nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f:
        components.html(f.read(), height=750)

def build_graph(site_url, pages, clusters, mode="structure"):
    G = nx.DiGraph()
    domain = urlparse(site_url).netloc.replace('www.', '')
    G.add_node("root", label=domain, size=30, color="#212121")
    for c in clusters:
        c_id = f"group_{c['name']}"
        G.add_node(c_id, label=c['name'].upper(), color="#FFD700", size=20)
        G.add_edge("root", c_id)
        for p in c['samples'][:12]:
            lbl = get_smart_label(p['title'], p['url'], domain)
            color = "#78909c"
            if mode == "score":
                score = 100 - (len(p['url']) % 60)
                color = "#4caf50" if score > 70 else "#f44336"
            G.add_node(p['url'], label=lbl, size=10, color=color, title=p['title'])
            G.add_edge(c_id, p['url'])
    return G

def render_audit_geo():
    db = AuditDatabase()
    user_email = st.session_state.get('user_email', 'demo@hotaru.app')
    is_admin = st.session_state.get('user_role') == "admin"

    st.title("🔍 Audit & Intelligence GEO")

    # --- HISTORIQUE (SIDEBAR) ---
    st.sidebar.title("📁 Historique")
    audits = db.load_user_audits(user_email, is_admin=is_admin)
    
    if audits:
        st.sidebar.info(f"✅ {len(audits)} audit(s) trouvé(s)")
        options = {f"{a['date']} | {a['site_url']}": a for a in audits}
        selection = st.sidebar.selectbox("Charger une version", list(options.keys()))
        
        if st.sidebar.button("📂 Restaurer l'audit"):
            data = options[selection]
            st.session_state.results = data['json_data']['results']
            st.session_state.clusters = data['json_data']['clusters']
            st.session_state.target_url = data['site_url']
            st.rerun()
    else:
        st.sidebar.write("Aucun audit sauvegardé.")

    # --- SCAN ---
    col_u, col_b = st.columns([4, 1])
    with col_u:
        url_input = st.text_input("URL", placeholder="https://...", label_visibility="collapsed")
    with col_b:
        if st.button("🚀 Scanner", use_container_width=True, type="primary"):
            scraper = SmartScraper(url_input, max_urls=80)
            res, stats = scraper.run_analysis()
            st.session_state.results = res
            st.session_state.clusters = scraper.get_pattern_summary()
            st.session_state.target_url = url_input
            st.rerun()

    # --- AFFICHAGE ---
    if "results" in st.session_state:
        st.markdown("---")
        c1, c2 = st.columns([3, 1])
        with c1: mode_geo = st.toggle("✨ Mode GEO Score")
        with c2:
            if st.button("💾 Sauvegarder"):
                payload = {"results": st.session_state.results, "clusters": st.session_state.clusters}
                if db.save_audit(user_email, st.session_state.target_url, payload, {}):
                    st.toast("Sauvegardé !")
                    st.rerun()

        G = build_graph(st.session_state.target_url, st.session_state.results, st.session_state.clusters, 
                        mode="score" if mode_geo else "structure")
        render_interactive_graph(G)
