import streamlit as st
import json, re, requests, zlib, base64
from urllib.parse import urlparse
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from core.database import AuditDatabase
from core.scraping import SmartScraper

# --- NETTOYAGE DES TITRES ---
def get_clean_label(title, url, domain):
    site_brand = domain.split('.')[0].lower()
    clean = re.split(r' [-|:|•] ', title)[0]
    if site_brand in clean.lower() or len(clean) < 4:
        slug = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
        clean = slug if len(slug) > 2 else "Page"
    return clean[:25]

# --- RENDU DU GRAPHE ---
def render_interactive_graph(G):
    nt = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)
    
    options = {
        "physics": {"forceAtlas2Based": {"gravitationalConstant": -100}, "solver": "forceAtlas2Based"},
        "interaction": {"hover": true, "navigationButtons": true, "keyboard": true},
        "nodes": {"font": {"size": 14, "strokeWidth": 2, "strokeColor": "#ffffff"}}
    }
    nt.set_options(json.dumps(options))
    
    path = "temp_graph.html"
    nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f: html = f.read()
    
    click_js = """<script>network.on("click", function (params) { 
        if (params.nodes.length > 0) { 
            var nodeId = params.nodes[0]; 
            if (nodeId.indexOf('http') === 0) { window.open(nodeId, '_blank'); } 
        } 
    });</script>"""
    components.html(html.replace("</body>", click_js + "</body>"), height=800)

# --- MODULE PRINCIPAL ---
def render_audit_geo():
    db = AuditDatabase()
    user_email = st.session_state.user_email
    is_admin = st.session_state.user_role == "admin"

    st.title("🔍 Audit & Intelligence GEO")

    # --- SIDEBAR & WORKSPACES ---
    st.sidebar.title("🏢 Espaces Clients")
    audits = db.load_user_audits(user_email, is_admin=is_admin)
    
    if audits:
        ws_list = sorted(list(set([str(a.get('workspace', 'Non classé')) for a in audits])))
        selected_ws = st.sidebar.selectbox("Choisir un Client", ws_list)
        filtered = [a for a in audits if str(a.get('workspace')) == selected_ws]
        options = {f"📅 {a['date']} | 🌐 {a['site_url']}": a for a in filtered}
        choice = st.sidebar.selectbox("Historique", list(options.keys()))
        
        if st.sidebar.button("📂 Restaurer cet audit", use_container_width=True):
            row = options[choice]
            try:
                decoded = base64.b64decode(row['data_compressed'])
                data = json.loads(zlib.decompress(decoded).decode('utf-8'))
                st.session_state.update({
                    "results": data['results'], 
                    "clusters": data['clusters'], 
                    "target_url": row['site_url'], 
                    "current_ws": row['workspace']
                })
                st.rerun()
            except Exception as e: st.error(f"Erreur décodage: {e}")

    # --- FORMULAIRE D'AUDIT ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: url_in = st.text_input("URL du site", placeholder="https://...")
        with c2: ws_in = st.text_input("Nom Client (Workspace)", placeholder="Ex: Marine Nationale")
        with c3: limit_in = st.select_slider("Profondeur", options=[50, 100, 200, 500], value=100)

        if st.button("🚀 Lancer l'analyse complète", type="primary", use_container_width=True):
            if not ws_in or not url_in:
                st.error("URL et Nom Client requis.")
            else:
                p_bar = st.progress(0, text="Démarrage...")
                def p_cb(msg, val): p_bar.progress(val, text=msg)
                
                scraper = SmartScraper(url_in, max_urls=limit_in)
                res, stats = scraper.run_analysis(progress_callback=p_cb)
                
                st.session_state.update({
                    "results": res, 
                    "clusters": scraper.get_pattern_summary(), 
                    "target_url": url_in, 
                    "current_ws": ws_in
                })
                p_bar.empty()
                st.rerun()

    # --- RÉSULTATS ---
    if "results" in st.session_state:
        st.divider()
        
        # Dashboard Technique (Metrics)
        total = len(st.session_state.results)
        slow_pages = len([p for p in st.session_state.results if p.get('response_time', 0) > 1.2])
        missing_meta = len([p for p in st.session_state.results if not p.get('description')])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Pages", total)
        m2.metric("Qualité Meta", f"{total-missing_meta}/{total}", delta=f"-{missing_meta}" if missing_meta > 0 else None)
        m3.metric("Lenteur (>1.2s)", slow_pages, delta_color="inverse")

        if st.button("💾 Sauvegarder dans cet Espace Client", use_container_width=True):
            payload = {"results": st.session_state.results, "clusters": st.session_state.clusters}
            if db.save_audit(user_email, st.session_state.current_ws, st.session_state.target_url, payload):
                st.toast("Sauvegarde réussie !")

        # CONSTRUCTION DU GRAPHE
        G = nx.DiGraph()
        domain = urlparse(st.session_state.target_url).netloc
        G.add_node(st.session_state.target_url, label=domain, size=30, color="#212121", font={'color': 'white'})
        
        for c in st.session_state.clusters:
            c_id = f"group_{c['name']}"
            G.add_node(c_id, label=c['name'].upper(), color="#FFD700", size=25)
            G.add_edge(st.session_state.target_url, c_id)
            
            for p in c['samples'][:15]:
                lbl = get_clean_label(p.get('title', 'N/A'), p['url'], domain)
                
                # Tooltip Technique (Audit simple intégré)
                status = "✅ SEO OK" if p.get('description') else "⚠️ Meta Description Manquante"
                perf = f"⏱️ {p.get('response_time', 0):.2f}s"
                tooltip = f"URL: {p['url']}\n{status}\nPerformance: {perf}\nH1: {p.get('h1', 'Inconnu')[:50]}"
                
                # Couleur dynamique selon erreur
                color = "#f44336" if not p.get('description') else "#78909c"
                
                G.add_node(p['url'], label=lbl, size=12, color=color, title=tooltip)
                G.add_edge(c_id, p['url'])
        
        render_interactive_graph(G)
