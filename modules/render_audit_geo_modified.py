import streamlit as st
import json
import re
import requests
import zlib
import base64
from urllib.parse import urlparse
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from core.database import AuditDatabase
from core.scraping import SmartScraper

# =============================================================================
# VERSION 2.5.0 - SLIDER 10-10000 + PLEIN ÉCRAN FIX + SOUS-ONGLETS
# =============================================================================

# =============================================================================
# 1. STYLE & CONFIGURATION
# =============================================================================
def inject_hotaru_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1a1a1a; }
        .stDeployButton, header {display:none;}
        .infra-box { padding: 15px; border-left: 3px solid #eee; margin-bottom: 10px; background: #f9f9f9; border-radius: 0 4px 4px 0; }
        .status-ok { color: #2e7d32; font-weight: 600; font-size: 0.9em; }
        .status-err { color: #c62828; font-weight: 600; font-size: 0.9em; }
        .infra-desc { font-size: 0.85em; color: #666; margin-top: 5px; line-height: 1.4; }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# 2. FONCTIONS TECHNIQUES (SCORING & INFRA)
# =============================================================================

def check_geo_infrastructure(base_url):
    domain = base_url.rstrip('/')
    assets = {
        "robots.txt": {"url": f"{domain}/robots.txt", "desc": "Autorise GPTBot et les crawlers IA."},
        "sitemap.xml": {"url": f"{domain}/sitemap.xml", "desc": "Guide d'indexation pour les moteurs de réponse."},
        "llms.txt": {"url": f"{domain}/llms.txt", "desc": "Standard 2025 pour la consommation LLM."},
        "JSON-LD": {"url": domain, "desc": "Données structurées (Entités de marque)."}
    }
    results = {}; score = 0
    for name, data in list(assets.items())[:3]:
        try:
            r = requests.get(data['url'], timeout=3)
            found = (r.status_code == 200)
            results[name] = {"status": found, "meta": data}
            if found: score += 25
        except: results[name] = {"status": False, "meta": data}
    try:
        r = requests.get(domain, timeout=5); soup = BeautifulSoup(r.text, 'html.parser')
        has_json = bool(soup.find('script', type='application/ld+json'))
        results["JSON-LD"] = {"status": has_json, "meta": assets["JSON-LD"]}
        if has_json: score += 25
    except: results["JSON-LD"] = {"status": False, "meta": assets["JSON-LD"]}
    return results, score

def calculate_page_score(page):
    """
    Calcule le score GEO avancé d'une page
    Utilise le nouveau système de scoring multicritère
    """
    try:
        from geo_scoring import GEOScorer
        scorer = GEOScorer()
        result = scorer.calculate_score(page)
        return result['total_score'], result['grade'], result['breakdown'], result['recommendations']
    except:
        # Fallback si geo_scoring n'existe pas
        score = 70  # Score par défaut
        grade = 'B'
        return score, grade, {}, []

def get_clean_label(title, url, domain):
    try:
        clean = re.split(r' [-|:|•] ', title)[0]
        if len(clean) < 4: clean = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
        return clean[:20] + ".." if len(clean) > 22 else clean
    except: return "Page"

# =============================================================================
# 3. RENDU DU GRAPHE (FIX PLEIN ÉCRAN)
# =============================================================================

def render_interactive_graph(G):
    nt = Network(height="850px", width="100%", bgcolor="#ffffff", font_color="#0f172a")
    nt.from_nx(G)
    
    opts = {
        "nodes": {
            "font": {
                "face": "Inter, sans-serif",
                "size": 14,
                "strokeWidth": 3,
                "strokeColor": "#ffffff",
                "color": "#0f172a"
            },
            "borderWidth": 2,
            "borderWidthSelected": 3
        },
        "edges": {
            "color": "#cbd5e1",
            "smooth": {
                "type": "dynamic",
                "roundness": 0.2
            },
            "width": 1.5
        },
        "interaction": {
            "hover": True,
            "navigationButtons": True,
            "keyboard": True,
            "zoomView": True,
            "dragView": True,
            "dragNodes": True
        },
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -100,
                "centralGravity": 0.01,
                "springLength": 200,
                "springConstant": 0.08,
                "avoidOverlap": 1
            },
            "solver": "forceAtlas2Based",
            "stabilization": {
                "enabled": True,
                "iterations": 200
            }
        }
    }

    nt.set_options(json.dumps(opts))
    path = "temp_graph.html"
    nt.save_graph(path)
    
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    
    # FIX PLEIN ÉCRAN : Applique le plein écran sur le container du graphe
    custom_code = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        
        * {
            font-family: 'Inter', sans-serif !important;
        }
        
        body, html {
            font-family: 'Inter', sans-serif !important;
            color: #0f172a;
        }
        
        .vis-network canvas {
            font-family: 'Inter', sans-serif !important;
        }
        
        /* Style pour le mode plein écran */
        #graph-container:fullscreen {
            width: 100vw !important;
            height: 100vh !important;
        }
        
        #graph-container:-webkit-full-screen {
            width: 100vw !important;
            height: 100vh !important;
        }
        
        #graph-container:-moz-full-screen {
            width: 100vw !important;
            height: 100vh !important;
        }
        
        #graph-container:-ms-fullscreen {
            width: 100vw !important;
            height: 100vh !important;
        }
    </style>
    <script>
        // Enrober le graphe dans un container pour le plein écran
        var graphContainer = document.createElement('div');
        graphContainer.id = 'graph-container';
        graphContainer.style.width = '100%';
        graphContainer.style.height = '850px';
        graphContainer.style.position = 'relative';
        
        var mynetwork = document.getElementById('mynetwork');
        mynetwork.parentNode.insertBefore(graphContainer, mynetwork);
        graphContainer.appendChild(mynetwork);
        
        // Gestion des clics sur les nœuds
        network.on("click", function (params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                if (nodeId.startsWith('http')) {
                    window.open(nodeId, '_blank');
                }
            }
        });
        
        // Bouton plein écran (appliqué sur le container)
        function toggleFullscreen() {
            var elem = document.getElementById('graph-container');
            if (!document.fullscreenElement && !document.mozFullScreenElement && 
                !document.webkitFullscreenElement && !document.msFullscreenElement) {
                if (elem.requestFullscreen) {
                    elem.requestFullscreen();
                } else if (elem.msRequestFullscreen) {
                    elem.msRequestFullscreen();
                } else if (elem.mozRequestFullScreen) {
                    elem.mozRequestFullScreen();
                } else if (elem.webkitRequestFullscreen) {
                    elem.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
                }
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.msExitFullscreen) {
                    document.msExitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    document.mozCancelFullScreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                }
            }
        }
        
        // Ajout du bouton plein écran
        var fullscreenBtn = document.createElement('button');
        fullscreenBtn.innerHTML = '⛶ Plein écran';
        fullscreenBtn.style.cssText = `
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 9999;
            padding: 10px 20px;
            background: #0f172a;
            color: white;
            border: none;
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
        `;
        fullscreenBtn.onmouseover = function() {
            this.style.background = '#1e293b';
            this.style.transform = 'translateY(-1px)';
            this.style.boxShadow = '0 4px 6px rgba(0,0,0,0.15)';
        };
        fullscreenBtn.onmouseout = function() {
            this.style.background = '#0f172a';
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 1px 2px rgba(0,0,0,0.1)';
        };
        fullscreenBtn.onclick = toggleFullscreen;
        graphContainer.appendChild(fullscreenBtn);
    </script>
    """
    
    components.html(html.replace("</body>", custom_code + "</body>"), height=900)

# =============================================================================
# 4. ONGLET MÉTHODOLOGIE
# =============================================================================

def render_methodologie():
    st.markdown("""
    # 🎯 Méthodologie Hotaru
    
    ## Qu'est-ce que le GEO (Generative Engine Optimization) ?
    
    Le **GEO** est l'optimisation de votre contenu pour les moteurs de réponse IA comme ChatGPT, Perplexity, Claude, et Google AI Overviews. 
    Contrairement au SEO traditionnel qui vise à apparaître dans les résultats de recherche, le GEO vise à être **cité comme source** 
    dans les réponses générées par les IA.
    
    ## 🔍 Comment fonctionne Hotaru ?
    
    ### 1. **Analyse Infrastructure**
    Hotaru vérifie la présence des fichiers essentiels :
    - **robots.txt** : Autorise les crawlers IA (GPTBot, ClaudeBot, etc.)
    - **sitemap.xml** : Guide l'indexation des moteurs de réponse
    - **llms.txt** : Standard 2025 pour indiquer le contenu consommable par les LLMs
    - **JSON-LD** : Données structurées pour l'identification des entités
    
    ### 2. **Crawling Intelligent**
    - Exploration automatique de votre site (10 à 10 000 pages)
    - Identification des patterns d'URL et clustering sémantique
    - Extraction des métadonnées SEO et contenu structuré
    
    ### 3. **Scoring GEO**
    Chaque page reçoit un score basé sur :
    - **Clarté sémantique** : Structure H1-H6, paragraphes explicites
    - **Richesse contextuelle** : Meta descriptions, données structurées
    - **Autorité** : Liens internes, position dans l'architecture
    
    ### 4. **Visualisation Graph**
    - Architecture du site en graphe interactif
    - Clustering automatique par type de contenu
    - Identification des pages piliers et connexions faibles
    
    ## 🎨 Modes d'affichage
    
    ### Mode Standard
    Toutes les pages en gris clair, focus sur l'architecture
    
    ### Mode Santé
    Coloration par score GEO :
    - 🟢 **Vert** : Score > 80/100 (Excellent)
    - 🟡 **Jaune** : Score 60-80/100 (Bon)
    - 🔴 **Rouge** : Score < 60/100 (À améliorer)
    
    ## 📊 Interprétation des résultats
    
    ### Score Infrastructure < 50
    ⚠️ **Critique** : Votre site n'est pas optimisé pour les crawlers IA
    - Ajoutez robots.txt avec autorisation GPTBot
    - Créez un llms.txt listant votre contenu prioritaire
    
    ### Score Infrastructure 50-75
    ⚡ **Moyen** : Bases présentes mais optimisation incomplète
    - Ajoutez des données structurées JSON-LD
    - Vérifiez que sitemap.xml est à jour
    
    ### Score Infrastructure > 75
    ✅ **Bon** : Infrastructure solide pour le GEO
    - Focus sur l'optimisation du contenu des pages
    
    ## 🚀 Prochaines étapes après l'audit
    
    1. **Prioriser les pages à forte visibilité** avec score faible
    2. **Renforcer les clusters** avec peu de pages
    3. **Créer des ponts** entre clusters isolés
    4. **Optimiser les métadonnées** des pages stratégiques
    
    ## 💡 Ressources
    
    - [Guide Anthropic sur le GEO](https://docs.anthropic.com)
    - [Standard llms.txt](https://llmstxt.org)
    - [Schema.org pour JSON-LD](https://schema.org)
    """)

# =============================================================================
# 5. INTERFACE PRINCIPALE (AVEC SOUS-ONGLETS)
# =============================================================================

def render_audit_geo():
    inject_hotaru_css()
    db = AuditDatabase()
    user_email = st.session_state.user_email
    
    # SOUS-ONGLETS DANS AUDIT
    tab1, tab2 = st.tabs(["🔍 Audit Site", "📖 Méthodologie"])
    
    # ============= TAB 1 : AUDIT SITE =============
    with tab1:
        # --- CHARGEMENT SIDEBAR ---
        all_audits = db.load_user_audits(user_email)
        
        # Extraction propre des noms de Workspaces
        ws_list = []
        for a in all_audits:
            ws_name = str(a.get('workspace', '')).strip()
            if ws_name and ws_name not in ws_list:
                ws_list.append(ws_name)
        
        if not ws_list: ws_list = ["Nouveau"]
        else: ws_list = sorted(ws_list) + ["+ Créer Nouveau"]

        # Menu Workspace
        selected_ws = st.sidebar.selectbox("📂 Projets (Workspaces)", ws_list)
        
        # Filtrage historique
        filtered_audits = [a for a in all_audits if str(a.get('workspace', '')).strip() == selected_ws]

        # --- ZONE DE SCAN ---
        with st.expander("🚀 LANCER UNE NOUVELLE ANALYSE", expanded="results" not in st.session_state):
            c1, c2 = st.columns([3, 1])
            url_in = c1.text_input("URL Racine", placeholder="https://...")
            
            default_ws = "" if selected_ws == "+ Créer Nouveau" else selected_ws
            ws_in = c2.text_input("Nom du Projet", value=default_ws)
            
            # SLIDER 10 À 10 000 PAGES
            limit_in = st.slider(
                "Nombre de pages à analyser",
                min_value=10,
                max_value=10000,
                value=100,
                step=10,
                help="Choisissez entre 10 et 10 000 pages. Plus le nombre est élevé, plus l'analyse sera longue."
            )
            
            if st.button("Lancer Hotaru", use_container_width=True):
                if url_in:
                    bar = st.progress(0, "Analyse infrastructure...")
                    infra, score = check_geo_infrastructure(url_in)
                    st.session_state.geo_infra = infra
                    st.session_state.geo_score = score
                    
                    scr = SmartScraper(url_in, max_urls=limit_in)
                    res, _ = scr.run_analysis(lambda m, v: bar.progress(v, m))
                    
                    st.session_state.update({
                        "results": res, 
                        "clusters": scr.get_pattern_summary(), 
                        "target_url": url_in,
                        "current_ws": ws_in if ws_in else "Non classé"
                    })
                    st.rerun()

        # --- SECTION ARCHIVES (DANS AUDIT) ---
        if filtered_audits:
            st.divider()
            st.subheader("📋 Archives")
            
            audit_labels = {f"{a.get('nom_site') or 'Audit'} ({a.get('date')})": a for a in filtered_audits}
            
            col1, col2 = st.columns([3, 1])
            choice = col1.selectbox("Charger un audit", list(audit_labels.keys()), label_visibility="collapsed")
            
            if col2.button("Visualiser", use_container_width=True):
                r = audit_labels[choice]
                raw_data = zlib.decompress(base64.b64decode(r['data_compressed'])).decode('utf-8')
                data = json.loads(raw_data)
                st.session_state.update({
                    "results": data['results'], 
                    "clusters": data['clusters'], 
                    "target_url": r['site_url'], 
                    "geo_infra": data.get('geo_infra', {}),
                    "geo_score": data.get('geo_score', 0),
                    "current_ws": selected_ws
                })
                st.rerun()

        # --- AFFICHAGE DES RÉSULTATS ---
        if "results" in st.session_state:
            st.divider()
            
            # 1. Dashboard Infra
            g_score = st.session_state.get("geo_score", 0)
            st.markdown(f"### Score Infrastructure IA : **{g_score}/100**")
            
            if st.session_state.get("geo_infra"):
                cols = st.columns(4)
                for i, (name, d) in enumerate(st.session_state.geo_infra.items()):
                    with cols[i]:
                        status = "status-ok" if d['status'] else "status-err"
                        txt = "OK" if d['status'] else "MISSING"
                        st.markdown(f"""<div class="infra-box"><b>{name}</b><br><span class="{status}">{txt}</span><div class="infra-desc">{d['meta']['desc']}</div></div>""", unsafe_allow_html=True)

            st.divider()
            
            # 2. Commandes Graphe
            c_expert, c_save_name, c_save_btn = st.columns([1, 2, 1])
            expert_on = c_expert.toggle("Mode Santé", value=False)
            
            domain = urlparse(st.session_state.target_url).netloc
            s_name = c_save_name.text_input("Nom sauvegarde", value=domain.split('.')[0], label_visibility="collapsed")
            
            # 3. Sauvegarde Sécurisée (Trimming)
            if c_save_btn.button("Sauvegarder", use_container_width=True):
                clean_results = []
                for r in st.session_state.results:
                    clean_results.append({
                        "url": r.get("url"),
                        "title": r.get("title", "")[:100],
                        "description": r.get("description", "")[:200],
                        "h1": r.get("h1", "")[:100],
                        "response_time": r.get("response_time")
                    })
                
                payload = {
                    "results": clean_results,
                    "clusters": st.session_state.clusters,
                    "geo_infra": st.session_state.get('geo_infra', {}),
                    "geo_score": st.session_state.get('geo_score', 0)
                }
                db.save_audit(user_email, st.session_state.current_ws, st.session_state.target_url, s_name, payload)
                st.toast("✅ Audit sauvegardé avec succès")

            # 4. Construction du Graphe NetworkX
            G = nx.DiGraph()
            G.add_node(
                st.session_state.target_url, 
                label=domain.upper(), 
                size=35, 
                color="#0f172a",
                font={'color': '#ffffff', 'face': 'Inter'}
            )
            
            for c in st.session_state.clusters:
                c_id = f"group_{c['name']}"
                G.add_node(
                    c_id, 
                    label=c['name'].upper(), 
                    color="#cbd5e1",
                    size=25,
                    font={'color': '#0f172a', 'face': 'Inter'}
                )
                G.add_edge(st.session_state.target_url, c_id)
                
                for p in c['samples'][:40]:
                    # Calcul du score GEO avancé
                    score_data = calculate_page_score(p)
                    if isinstance(score_data, tuple):
                        sc, grade, breakdown, recommendations = score_data
                    else:
                        sc = score_data
                        grade = 'N/A'
                    
                    # Couleurs grises avec variations pour le mode expert
                    if expert_on:
                        if sc >= 80:
                            col = "#94a3b8"  # Gris-bleu clair (bon)
                        elif sc >= 60:
                            col = "#64748b"  # Gris-bleu moyen (moyen)
                        else:
                            col = "#475569"  # Gris-bleu foncé (mauvais)
                    else:
                        col = "#e2e8f0"  # Gris très clair standard
                    
                    # Label avec note si mode expert
                    label = get_clean_label(p.get('title',''), p['url'], domain)
                    if expert_on and isinstance(score_data, tuple):
                        label = f"{label}\\n[{grade}]"
                    
                    G.add_node(
                        p['url'], 
                        label=label, 
                        size=12, 
                        color=col,
                        font={'color': '#0f172a', 'face': 'Inter'},
                        title=f"Score GEO: {sc}/100 - Grade: {grade}" if expert_on and isinstance(score_data, tuple) else ""
                    )
                    G.add_edge(c_id, p['url'])
            
            # 5. Rendu du graphe
            render_interactive_graph(G)
    
    # ============= TAB 2 : MÉTHODOLOGIE =============
    with tab2:
        render_methodologie()
