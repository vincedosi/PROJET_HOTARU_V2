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
    """Nettoyage agressif des titres."""
    domain_clean = domain.split('.')[0]
    # On retire le nom du site s'il est dans le titre
    clean = re.split(r' [-|:] ', title)[0]
    if domain_clean.lower() in clean.lower() or len(clean) < 5:
        # On replie sur le dernier segment de l'URL (Slug)
        clean = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
    return clean[:25]

def render_interactive_graph(G):
    nt = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)
    nt.set_options('{"physics": {"forceAtlas2Based": {"gravitationalConstant": -50, "centralGravity": 0.01}, "solver": "forceAtlas2Based"}}')
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
                # Simu score pour la démo
                score = 100 - (len(p['url']) % 60)
                color = "#4caf50" if score > 70 else "#f44336"
            
            G.add_node(p['url'], label=lbl, size=10, color=color, title=p['title'])
            G.add_edge(c_id, p['url'])
    return G

def render_audit_geo():
    db = AuditDatabase()
    user_email = st.session_state.user_email
    is_admin = st.session_state.user_role == "admin"

    st.title("🔍 Audit GEO")

    # --- HISTORIQUE & VERSIONING ---
    with st.expander("🕒 Historique des audits", expanded=False):
        audits = db.load_user_audits(user_email, is_admin=is_admin)
        if audits:
            # Formatage du label pour l'admin
            options = {f"{'👤 '+a['user_email'] if is_admin else ''} | {a['date']} | {a['site_url']}": a for a in audits}
            choice = st.selectbox("Restaurer une version", list(options.keys()))
            if st.button("Restaurer cette version"):
                saved_data = json.loads(options[choice]['json_data'])
                st.session_state.results = saved_data['results']
                st.session_state.clusters = saved_data['clusters']
                st.session_state.target_url = options[choice]['site_url']
                st.rerun()
        else:
            st.write("Aucun audit trouvé.")

    # --- NOUVEL ANALYSE ---
    url = st.text_input("URL à analyser", placeholder="https://...")
    if st.button("🚀 Lancer l'analyse"):
        scraper = SmartScraper(url, max_urls=100)
        results, stats = scraper.run_analysis()
        st.session_state.results = results
        st.session_state.clusters = scraper.get_pattern_summary()
        st.session_state.target_url = url

    # --- AFFICHAGE & SAUVEGARDE ---
    if "results" in st.session_state:
        col_m, col_s = st.columns([3, 1])
        with col_m:
            mode_geo = st.toggle("✨ Mode GEO Score (Analyse IA)")
        with col_s:
            if st.button("💾 Sauvegarder cette version"):
                payload = {"results": st.session_state.results, "clusters": st.session_state.clusters}
                db.save_audit(user_email, st.session_state.target_url, payload, {"total_urls": len(st.session_state.results)})
                st.toast("Version archivée !")

        G = build_graph(st.session_state.target_url, st.session_state.results, st.session_state.clusters, 
                        mode="score" if mode_geo else "structure")
        render_interactive_graph(G)
