import streamlit as st
import json, re, requests, zlib, base64
from urllib.parse import urlparse
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from core.database import AuditDatabase
from core.scraping import SmartScraper

# --- LOGIQUE DE NETTOYAGE DES TITRES ---
def get_clean_label(title, url, domain):
    """Retire le nom du site et les segments inutiles pour la clarté."""
    # Nettoyage des extensions courantes (ex: .gouv.fr, .com)
    site_brand = domain.split('.')[0].lower()
    
    # On retire le nom de marque s'il est dans le titre (ex: "Accueil - Marine" -> "Accueil")
    clean = re.split(r' [-|:|•] ', title)[0]
    
    # Si après nettoyage le titre est trop court ou contient toujours la marque
    if site_brand in clean.lower() or len(clean) < 4:
        # On utilise le dernier segment de l'URL (Slug) qui est souvent plus explicite
        slug = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
        clean = slug if len(slug) > 2 else "Page"
    
    return clean[:25]

def render_interactive_graph(G):
    nt = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)
    nt.set_options('{"physics": {"forceAtlas2Based": {"gravitationalConstant": -70}, "solver": "forceAtlas2Based"}, "interaction": {"hover": true}}')
    path = "temp_graph.html"; nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f: html = f.read()
    click_js = """<script>network.on("click", function (params) { if (params.nodes.length > 0) { var nodeId = params.nodes[0]; if (nodeId.indexOf('http') === 0) { window.open(nodeId, '_blank'); } } });</script>"""
    components.html(html.replace("</body>", click_js + "</body>"), height=650)

# --- INTERFACE PRINCIPALE ---
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
        choice = st.sidebar.selectbox("Versions", list(options.keys()))
        
        if st.sidebar.button("📂 Restaurer l'audit"):
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
        with c2: ws_in = st.text_input("Nom Client", placeholder="ex: Marine Nationale")
        with c3: limit_in = st.select_slider("Pages", options=[50, 100, 200, 500], value=100)

        if st.button("🚀 Lancer l'analyse complète", type="primary", use_container_width=True):
            if not ws_in or not url_in:
                st.error("URL et Nom Client requis.")
            else:
                scraper = SmartScraper(url_in, max_urls=limit_in)
                res, stats = scraper.run_analysis()
                st.session_state.results = res
                st.session_state.clusters = scraper.get_pattern_summary()
                st.session_state.target_url = url_in
                st.session_state.current_ws = ws_in
                st.rerun()

    # --- RENDU DES RÉSULTATS ---
    if "results" in st.session_state:
        st.divider()
        
        # Boîte d'aide pédagogique
        with st.expander("❓ Comprendre ce graphique (Guide GEO)", expanded=False):
            st.markdown("""
            **Comment lire la cartographie structurelle ?**
            * **Centre Noir :** La racine de votre site (Accueil).
            * **Noeuds Jaunes :** Les thématiques majeures (Clusters) détectées par l'IA.
            * **Noeuds Gris :** Vos pages réelles.
            
            **Objectif GEO :** Une structure bien organisée en silos (jaunes) aide les moteurs de réponse (IA) à mieux indexer votre expertise. Plus le maillage est cohérent, plus votre 'GEO Score' sera élevé.
            """)

        # Bouton de sauvegarde
        if st.button("💾 Sauvegarder dans cet Espace Client"):
            payload = {"results": st.session_state.results, "clusters": st.session_state.clusters}
            if db.save_audit(user_email, st.session_state.current_ws, st.session_state.target_url, payload):
                st.toast("Sauvegarde effectuée !")

        # Construction du graphe avec labels propres
        G = nx.DiGraph()
        domain = urlparse(st.session_state.target_url).netloc
        G.add_node(st.session_state.target_url, label=domain, size=30, color="#212121")
        
        for c in st.session_state.clusters:
            c_id = f"group_{c['name']}"
            G.add_node(c_id, label=c['name'].upper(), color="#FFD700", size=20)
            G.add_edge(st.session_state.target_url, c_id)
            
            for p in c['samples'][:15]:
                # On utilise la fonction de nettoyage ici
                lbl = get_clean_label(p['title'], p['url'], domain)
                G.add_node(p['url'], label=lbl, size=10, color="#78909c", title=p['url'])
                G.add_edge(c_id, p['url'])
        
        render_interactive_graph(G)
