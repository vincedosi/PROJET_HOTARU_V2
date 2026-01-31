"""
HOTARU - Audit GEO Module (v0.9.9 - FULL VERSIONING)
Sauvegarde l'intégralité des données pour une démo persistante.
"""
import streamlit as st
import networkx as nx
from pyvis.network import Network 
import streamlit.components.v1 as components
from core.database import AuditDatabase
from urllib.parse import urlparse
import re
import json

# --- NETTOYAGE LABELS ---
def get_smart_label(page_title, page_url, domain_name):
    domain_clean = domain_name.split('.')[0]
    parts = re.split(r' [-|:] ', page_title)
    best_candidate = ""
    for part in parts:
        part = part.strip()
        if domain_clean.lower() in part.lower(): continue
        if len(part) > len(best_candidate): best_candidate = part
    if len(best_candidate) < 4:
        path = urlparse(page_url).path.rstrip('/')
        slug = path.split('/')[-1] if '/' in path else path
        best_candidate = slug.replace('-', ' ').replace('_', ' ').capitalize()
    return best_candidate[:25] + "..." if len(best_candidate) > 25 else best_candidate

# --- SCORE GEO (LOGIQUE DÉMO) ---
def get_geo_score(page_title, page_url):
    score = 100
    reasons = []
    if len(page_title) < 15: 
        score -= 20
        reasons.append("Titre court")
    if len(page_url) > 70:
        score -= 15
        reasons.append("URL profonde")
    return max(20, score), reasons

# --- BUILDER DU GRAPHE ---
def build_pro_graph(site_url, pages, clusters, mode="structure"):
    G = nx.DiGraph()
    domain = urlparse(site_url).netloc.replace('www.', '')
    base_url_clean = site_url.rstrip('/')
    
    # RACINE
    G.add_node("root", label=domain, title="Racine", url=site_url, color="#212121", size=30)
    
    for c in clusters:
        c_id = f"group_{c['name']}"
        G.add_node(c_id, label=c['name'].capitalize(), color="#FFD700", size=20)
        G.add_edge("root", c_id)
        
        for p in c['samples'][:15]: # Limite pour fluidité
            p_id = p['url']
            lbl = get_smart_label(p['title'], p['url'], domain)
            
            if mode == "score":
                score, reasons = get_geo_score(p['title'], p['url'])
                color = "#4caf50" if score >= 80 else ("#ff9800" if score >= 50 else "#f44336")
                tooltip = f"GEO Score: {score}/100\n" + "\n".join(reasons)
            else:
                color = "#78909c"
                tooltip = p['title']

            G.add_node(p_id, label=lbl, title=tooltip, url=p['url'], size=10, color=color)
            G.add_edge(c_id, p_id)
    return G

# --- UI PRINCIPALE ---
def render_audit_geo():
    st.markdown("## 🔍 Audit & Cartographie")
    db = AuditDatabase()
    user_email = st.session_state.get('user_email', 'demo@hotaru.app')

    # Barre d'action
    c1, c2 = st.columns([4, 1])
    with c1:
        url = st.text_input("URL", placeholder="https://exemple.com", key="input_url")
    with c2:
        launch = st.button("🚀 Analyser", use_container_width=True, type="primary")

    # SECTION HISTORIQUE / VERSIONNING
    st.markdown("### 🕒 Historique des versions")
    audits = db.load_user_audits(user_email)
    if audits:
        cols = st.columns([3, 1])
        with cols[0]:
            # On affiche la date et l'URL pour choisir la version
            options = {f"{a['date']} - {a['site_url']}": a for a in audits}
            selected_ver = st.selectbox("Choisir une version", list(options.keys()))
        with cols[1]:
            if st.button("📂 Restaurer", use_container_width=True):
                data = options[selected_ver]
                # On restaure TOUTE la data sauvegardée
                raw_data = json.loads(data['json_data'])
                st.session_state.audit_results = raw_data['results']
                st.session_state.current_clusters = raw_data['clusters']
                st.session_state.restored_url = data['site_url']
                # On force la reconstruction du graphe
                G = build_pro_graph(data['site_url'], raw_data['results'], raw_data['clusters'])
                st.session_state.current_graph = G
                st.rerun()
    else:
        st.caption("Aucun historique disponible.")

    # LOGIQUE SCRAPING
    if launch and url:
        from core.scraping import SmartScraper
        with st.spinner("Analyse en cours..."):
            scraper = SmartScraper(base_url=url, max_urls=100)
            results, stats = scraper.run_analysis(lambda m, v: None)
            clusters = scraper.get_pattern_summary()
            
            st.session_state.audit_results = results
            st.session_state.current_clusters = clusters
            st.session_state.current_stats = stats
            st.session_state.current_graph = build_pro_graph(url, results, clusters)
            st.rerun()

    # AFFICHAGE DU GRAPHE ET BOUTON SAUVEGARDE
    if "current_graph" in st.session_state:
        st.markdown("---")
        m1, m2 = st.columns([3, 1])
        with m1:
            mode_geo = st.toggle("✨ Activer GEO Score (IA)", key="geo_toggle")
            view_mode = "score" if mode_geo else "structure"
        with m2:
            if st.button("💾 Sauvegarder cette version", type="primary", use_container_width=True):
                # ICI LE SECRET : On sauve tout le dictionnaire de données !
                payload = {
                    "results": st.session_state.audit_results,
                    "clusters": st.session_state.current_clusters
                }
                site_url = st.session_state.get('restored_url', url)
                if db.save_audit(user_email, site_url, payload, {"total_urls": len(st.session_state.audit_results)}):
                    st.toast("Version sauvegardée !", icon="✅")
                    st.rerun()

        # Rendu (Appel de ta fonction render_interactive_graph existante...)
        # Note: On reconstruit le graphe selon le mode (Score ou Structure)
        G = build_pro_graph(
            st.session_state.get('restored_url', url), 
            st.session_state.audit_results, 
            st.session_state.current_clusters,
            mode=view_mode
        )
        # Importe ici ta fonction render_interactive_graph (voir message précédent)
        from modules.audit_geo_utils import render_interactive_graph 
        render_interactive_graph(G)
