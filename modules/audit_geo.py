import streamlit as st
import json
import re
from urllib.parse import urlparse
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from core.database import AuditDatabase
from core.scraping import SmartScraper

# --- UTILITAIRES DE NETTOYAGE ET RENDU ---
def get_smart_label(title, url, domain):
    """Nettoie les titres pour un affichage propre dans le graphe."""
    domain_clean = domain.split('.')[0]
    # On prend la partie avant le premier séparateur (pipe, tiret, etc.)
    clean = re.split(r' [-|:] ', title)[0]
    if domain_clean.lower() in clean.lower() or len(clean) < 5:
        # Si le titre est vide ou contient juste le nom du site, on utilise le slug de l'URL
        clean = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
        if not clean: clean = "Accueil"
    return clean[:25]

def render_interactive_graph(G):
    """Génère le HTML pour le graphe interactif Pyvis."""
    nt = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#333333")
    nt.from_nx(G)
    nt.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {"gravitationalConstant": -100, "centralGravity": 0.01, "springLength": 100},
        "solver": "forceAtlas2Based",
        "stabilization": {"enabled": true, "iterations": 100}
      },
      "nodes": {"font": {"size": 12, "face": "Arial"}},
      "edges": {"smooth": {"type": "continuous"}}
    }
    """)
    path = "temp_graph.html"
    nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f:
        components.html(f.read(), height=750)

def build_graph(site_url, pages, clusters, mode="structure"):
    """Construit l'objet NetworkX pour le graphe."""
    G = nx.DiGraph()
    domain = urlparse(site_url).netloc.replace('www.', '')
    
    # Noeud Racine (Le site)
    G.add_node("root", label=domain, size=30, color="#212121", font={'color': 'white'})

    for c in clusters:
        c_id = f"group_{c['name']}"
        # Noeuds Clusters (Thématiques)
        G.add_node(c_id, label=c['name'].upper(), color="#FFD700", size=20)
        G.add_edge("root", c_id)
        
        # Noeuds Pages
        for p in c['samples'][:15]: # Limite pour la performance visuelle
            lbl = get_smart_label(p['title'], p['url'], domain)
            color = "#78909c" # Couleur par défaut (Structure)
            
            if mode == "score":
                # Simulation de score GEO pour la démo
                score = 100 - (len(p['url']) % 60)
                color = "#4caf50" if score > 70 else ("#ff9800" if score > 40 else "#f44336")
                tooltip = f"GEO Score: {score}/100"
            else:
                tooltip = p['title']
            
            G.add_node(p['url'], label=lbl, size=10, color=color, title=tooltip)
            G.add_edge(c_id, p['url'])
    return G

# --- FONCTION PRINCIPALE DU MODULE ---
def render_audit_geo():
    db = AuditDatabase()
    user_email = st.session_state.get('user_email', 'demo@hotaru.app')
    is_admin = st.session_state.get('user_role') == "admin"

    st.title("🔍 Audit & Intelligence GEO")

    # --- 1. BARRE LATERALE : HISTORIQUE ET CHARGEMENT ---
    st.sidebar.markdown("### 📁 Historique des Audits")
    audits = db.load_user_audits(user_email, is_admin=is_admin)
    
    if audits:
        # Création d'une liste lisible : "Date | URL"
        options = {f"{a['date']} | {a['site_url']}": a for a in audits}
        # Si Admin, on ajoute le nom de l'utilisateur
        if is_admin:
            options = {f"👤 {a['user_email']} | {a['date']} | {a['site_url']}": a for a in audits}
            
        selected_label = st.sidebar.selectbox("Choisir une version", list(options.keys()))
        
        if st.sidebar.button("📂 Restaurer cet audit"):
            selected_audit = options[selected_label]
            # La donnée est déjà désérialisée/décompressée par Database.py
            payload = selected_audit['json_data']
            
            st.session_state.results = payload['results']
            st.session_state.clusters = payload['clusters']
            st.session_state.target_url = selected_audit['site_url']
            st.toast("Audit restauré avec succès !")
            st.rerun()
    else:
        st.sidebar.info("Aucun audit sauvegardé.")

    # --- 2. ZONE DE LANCEMENT (SCRAPER) ---
    col_u, col_b = st.columns([4, 1])
    with col_u:
        url_input = st.text_input("URL du site à auditer", placeholder="https://exemple.com", label_visibility="collapsed")
    with col_b:
        launch = st.button("🚀 Lancer l'analyse", use_container_width=True, type="primary")

    if launch and url_input:
        # Barre de progression dynamique
        progress_bar = st.progress(0, text="Démarrage du crawler...")
        
        try:
            # Callback pour mettre à jour la barre de progression en temps réel
            def update_progress(msg, val):
                progress_bar.progress(val, text=msg)
            
            scraper = SmartScraper(url_input, max_urls=80)
            results, stats = scraper.run_analysis(progress_callback=update_progress)
            
            # Stockage en session
            st.session_state.results = results
            st.session_state.clusters = scraper.get_pattern_summary()
            st.session_state.target_url = url_input
            
            progress_bar.empty()
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de l'analyse : {e}")

    # --- 3. AFFICHAGE DES RÉSULTATS ET GRAPH ---
    if "results" in st.session_state and st.session_state.results:
        st.markdown("---")
        c1, c2, c3 = st.columns([2, 1, 1])
        
        with c1:
            mode_geo = st.toggle("✨ Activer l'analyse GEO Score (IA)", help="Colore les noeuds selon leur potentiel de visibilité")
        
        with c3:
            if st.button("💾 Sauvegarder cette version", use_container_width=True):
                payload = {
                    "results": st.session_state.results,
                    "clusters": st.session_state.clusters
                }
                # Appel à la fonction de sauvegarde compressée
                stats = {"total_urls": len(st.session_state.results)}
                if db.save_audit(user_email, st.session_state.target_url, payload, stats):
                    st.toast("Audit sauvegardé dans la base !", icon="✅")
                    st.rerun()

        # Construction du graphe selon le mode choisi
        view_mode = "score" if mode_geo else "structure"
        G = build_graph(
            st.session_state.target_url, 
            st.session_state.results, 
            st.session_state.clusters, 
            mode=view_mode
        )
        
        # Affichage interactif
        render_interactive_graph(G)
        
        # Petit tableau récapitulatif sous le graph
        with st.expander("📄 Liste des pages détectées"):
            st.table([{"Page": p['title'][:60], "URL": p['url']} for p in st.session_state.results[:20]])
