import streamlit as st
import json
import re
from urllib.parse import urlparse
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from core.database import AuditDatabase
from core.scraping import SmartScraper

# --- UTILITAIRES ---
def get_smart_label(title, url, domain):
    domain_clean = domain.split('.')[0]
    clean = re.split(r' [-|:] ', title)[0]
    if domain_clean.lower() in clean.lower() or len(clean) < 5:
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
                # Logique de score simplifiée pour la démo
                score = 100 - (len(p['url']) % 60)
                color = "#4caf50" if score > 70 else "#f44336"
            
            G.add_node(p['url'], label=lbl, size=10, color=color, title=p['title'])
            G.add_edge(c_id, p['url'])
    return G

# --- MODULE PRINCIPAL ---
def render_audit_geo():
    db = AuditDatabase()
    user_email = st.session_state.user_email
    is_admin = st.session_state.user_role == "admin"

    st.title("🔍 Audit & Intelligence GEO")

    # --- 1. CHARGEMENT / HISTORIQUE ---
    st.sidebar.markdown("### 📁 Mes Sauvegardes")
    audits = db.load_user_audits(user_email, is_admin=is_admin)
    
    if audits:
        # Création d'une liste lisible pour le selectbox
        audit_options = {f"{a['date']} | {a['site_url']}": a for a in audits}
        selected_label = st.sidebar.selectbox("Choisir un audit réalisé", list(audit_options.keys()))
        
        if st.sidebar.button("📂 Restaurer cet audit"):
            selected_audit = audit_options[selected_label]
            saved_payload = json.loads(selected_audit['json_data'])
            
            # Restauration dans la session
            st.session_state.results = saved_payload['results']
            st.session_state.clusters = saved_payload['clusters']
            st.session_state.target_url = selected_audit['site_url']
            st.toast(f"Audit de {selected_audit['site_url']} restauré !")
            st.rerun()
    else:
        st.sidebar.info("Aucun audit trouvé dans la base.")

    # --- 2. ZONE DE SCAN ---
    col_u, col_b = st.columns([4, 1])
    with col_u:
        url = st.text_input("URL à analyser", placeholder="https://...", label_visibility="collapsed")
    with col_b:
        launch = st.button("🚀 Scanner", use_container_width=True, type="primary")

    if launch and url:
        # Initialisation de la barre de progression
        progress_bar = st.progress(0, text="Initialisation du crawler...")
        
        try:
            scraper = SmartScraper(url, max_urls=100)
            # Utilisation du callback pour mettre à jour la barre
            def update_progress(msg, val):
                progress_bar.progress(val, text=msg)
            
            results, stats = scraper.run_analysis(progress_callback=update_progress)
            
            st.session_state.results = results
            st.session_state.clusters = scraper.get_pattern_summary()
            st.session_state.target_url = url
            progress_bar.empty() # On enlève la barre une fois fini
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de l'audit : {e}")

    # --- 3. AFFICHAGE DES RÉSULTATS ---
    if "results" in st.session_state:
        st.markdown("---")
        c_mode, c_save = st.columns([3, 1])
        
        with c_mode:
            mode_geo = st.toggle("✨ Activer la vue GEO Score (IA)")
        
        with c_save:
            if st.button("💾 Sauvegarder l'audit", use_container_width=True):
                payload = {
                    "results": st.session_state.results,
                    "clusters": st.session_state.clusters
                }
                success = db.save_audit(
                    user_email, 
                    st.session_state.target_url, 
                    payload, 
                    {"total_urls": len(st.session_state.results)}
                )
                if success:
                    st.toast("Audit enregistré dans Google Sheets !", icon="✅")

        # Construction et affichage du graph
        G = build_graph(
            st.session_state.target_url, 
            st.session_state.results, 
            st.session_state.clusters, 
            mode="score" if mode_geo else "structure"
        )
        render_interactive_graph(G)
