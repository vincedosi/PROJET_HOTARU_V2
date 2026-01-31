import streamlit as st
import json, re, requests, zlib, base64
from urllib.parse import urlparse
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from core.database import AuditDatabase
from core.scraping import SmartScraper

def get_clean_label(title, url, domain):
    site_brand = domain.split('.')[0].lower()
    clean = re.split(r' [-|:|•] ', title)[0]
    if site_brand in clean.lower() or len(clean) < 4:
        slug = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
        clean = slug if len(slug) > 2 else "Page"
    return clean[:25]

def render_interactive_graph(G):
    # Initialisation avec les boutons de navigation et plein écran
    nt = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)
    
    # Configuration avancée : Ajout du plein écran et de la barre de contrôle
    options = {
        "physics": {
            "forceAtlas2Based": {"gravitationalConstant": -100, "springLength": 100},
            "solver": "forceAtlas2Based",
            "stabilization": {"enabled": True, "iterations": 100}
        },
        "interaction": {
            "hover": True,
            "navigationButtons": True,  # Ajoute les flèches de navigation
            "multiselect": True,
            "keyboard": True
        },
        "nodes": {
            "borderWidth": 2,
            "font": {"size": 14}
        }
    }
    
    nt.set_options(json.dumps(options))
    
    path = "temp_graph.html"
    nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f: 
        html = f.read()
    
    # Injection JS pour les liens cliquables
    click_js = """
    <script>
    network.on("click", function (params) {
        if (params.nodes.length > 0) {
            var nodeId = params.nodes[0];
            if (nodeId.indexOf('http') === 0) { window.open(nodeId, '_blank'); }
        }
    });
    </script>
    """
    # Ajout d'une balise de style pour forcer le plein écran du conteneur
    full_screen_style = "<style>#mynetwork { background-color: #f8f9fa; border-radius: 10px; }</style>"
    
    components.html(html.replace("</body>", click_js + full_screen_style + "</body>"), height=800)

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
        choice = st.sidebar.selectbox("Charger une sauvegarde", list(options.keys()))
        
        if st.sidebar.button("📂 Restaurer l'audit", use_container_width=True):
            row = options[choice]
            decoded = base64.b64decode(row['data_compressed'])
            data = json.loads(zlib.decompress(decoded).decode('utf-8'))
            st.session_state.results = data['results']
            st.session_state.clusters = data['clusters']
            st.session_state.target_url = row['site_url']
            st.session_state.current_ws = row['workspace']
            st.rerun()
    
    # --- FORMULAIRE D'AUDIT ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: url_in = st.text_input("URL du site", placeholder="https://...")
        with c2: ws_in = st.text_input("Nom Client (Workspace)", placeholder="Marine Nationale")
        with c3: limit_in = st.select_slider("Profondeur", options=[50, 100, 200, 500], value=100)

        if st.button("🚀 Lancer l'analyse complète", type="primary", use_container_width=True):
            if not ws_in or not url_in:
                st.error("L'URL et le Workspace sont obligatoires.")
            else:
                # BARRE DE PROGRESSION RETROUVÉE
                progress_text = "Analyse en cours... veuillez patienter."
                my_bar = st.progress(0, text=progress_text)
                
                # On passe le callback de progression au scraper
                def p_callback(msg, val):
                    my_bar.progress(val, text=msg)

                scraper = SmartScraper(url_in, max_urls=limit_in)
                res, stats = scraper.run_analysis(progress_callback=p_callback)
                
                st.session_state.results = res
                st.session_state.clusters = scraper.get_pattern_summary()
                st.session_state.target_url = url_in
                st.session_state.current_ws = ws_in
                
                my_bar.empty() # On retire la barre à la fin
                st.rerun()

    # --- RENDU DES RÉSULTATS ---
    if "results" in st.session_state:
        st.divider()
        
        # Dashboard Info
        c_a, c_b, c_c = st.columns(3)
        c_a.metric("Pages analysées", len(st.session_state.results))
        c_b.metric("Clusters IA", len(st.session_state.clusters))
        c_c.metric("Workspace", st.session_state.current_ws)

        col_save, col_help = st.columns([1, 1])
        with col_save:
            if st.button("💾 Sauvegarder dans le Workspace", use_container_width=True):
                payload = {"results": st.session_state.results, "clusters": st.session_state.clusters}
                if db.save_audit(user_email, st.session_state.current_ws, st.session_state.target_url, payload):
                    st.toast("Sauvegarde effectuée !")

        with col_help:
            with st.expander("❓ Aide : Interpréter le graphique"):
                st.write("Cliquez sur une bulle pour ouvrir la page. Utilisez la molette pour zoomer.")

        # Construction du graphe
        G = nx.DiGraph()
        domain = urlparse(st.session_state.target_url).netloc
        G.add_node(st.session_state.target_url, label=domain, size=30, color="#212121")
        
        for c in st.session_state.clusters:
            c_id = f"group_{c['name']}"
            G.add_node(c_id, label=c['name'].upper(), color="#FFD700", size=25)
            G.add_edge(st.session_state.target_url, c_id)
            for p in c['samples'][:15]:
                lbl = get_clean_label(p['title'], p['url'], domain)
                G.add_node(p['url'], label=lbl, size=12, color="#78909c", title=p['url'])
                G.add_edge(c_id, p['url'])
        
        render_interactive_graph(G)
