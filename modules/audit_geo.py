# =============================================================================
# AUDIT GEO - VERSION AVEC LOGS EN TEMPS RÉEL
# =============================================================================


import streamlit as st
import json
import re
import requests
import zlib
import base64
from urllib.parse import urlparse
from collections import defaultdict
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from core.database import AuditDatabase
from core.scraping import SmartScraper

# =============================================================================
# VERSION 2.7.0 - LOGS + COMPTEURS + STATS DÉTAILLÉES
# =============================================================================

# =============================================================================
# 1. STYLE & CONFIGURATION
# =============================================================================
def inject_hotaru_css():
    """CSS is now centralized in assets/style.css - this is a no-op kept for interface stability."""
    pass

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

def fetch_file_content(base_url, filename):
    """Récupère le contenu d'un fichier (robots.txt, llms.txt) sur le site"""
    url = f"{base_url.rstrip('/')}/{filename}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.text.strip(), True
        else:
            return f"# {filename} non trouvé (HTTP {r.status_code})", False
    except Exception as e:
        return f"# Erreur de récupération : {e}", False

def generate_mistral_optimization(file_content, filename, site_url, found):
    """Appelle Mistral pour générer une version optimisée du fichier"""
    try:
        api_key = st.secrets["mistral"]["api_key"]
    except Exception:
        return "Clé API Mistral manquante dans les secrets Streamlit."

    if filename == "robots.txt":
        prompt = f"""Tu es un expert en SEO technique et AI-Readability.
Voici le fichier robots.txt actuel du site {site_url} :

{file_content if found else "Le fichier robots.txt n'existe pas ou est vide."}

Génère un robots.txt PARFAIT et optimisé pour les agents IA (GPTBot, ChatGPT-User, Google-Extended, ClaudeBot, PerplexityBot, Bingbot).
Le fichier doit :
1. Autoriser explicitement les crawlers IA importants
2. Référencer le sitemap.xml
3. Bloquer les ressources inutiles (/admin, /wp-login, etc.)
4. Suivre les meilleures pratiques 2025-2026

Réponds UNIQUEMENT avec le contenu du fichier robots.txt, sans aucun commentaire ni explication autour."""
    else:  # llms.txt
        prompt = f"""Tu es un expert en AI-Readability et standards LLM.
Voici le fichier llms.txt actuel du site {site_url} :

{file_content if found else "Le fichier llms.txt n'existe pas."}

Génère un llms.txt PARFAIT selon le standard llms.txt 2025.
Le fichier doit :
1. Présenter clairement l'organisation/entreprise
2. Lister les pages clés et sections du site
3. Fournir le contexte métier pour les LLMs
4. Inclure les informations de contact et liens importants
5. Suivre la spécification llms.txt (https://llmstxt.org/)

Le site est : {site_url}

Réponds UNIQUEMENT avec le contenu du fichier llms.txt, sans aucun commentaire ni explication autour."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": "Tu es un expert en optimisation de sites web pour les agents IA. Tu génères uniquement du code/config, jamais d'explications."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 2000
    }

    try:
        response = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Erreur API Mistral : {e}"

def render_mistral_optimization(base_url):
    """Affiche le module d'optimisation IA avec comparatif existant vs proposition Mistral"""
    if not base_url:
        return

    with st.expander("🤖 Optimisation IA (Mistral) — robots.txt & llms.txt", expanded=False):
        st.caption("Analyse et optimisation automatique de vos fichiers d'infrastructure IA")

        files_to_optimize = ["robots.txt", "llms.txt"]
        tabs = st.tabs([f"📄 {f}" for f in files_to_optimize])

        for idx, filename in enumerate(files_to_optimize):
            with tabs[idx]:
                # Récupérer le contenu existant
                content, found = fetch_file_content(base_url, filename)

                if found:
                    st.success(f"{filename} trouvé sur le site")
                else:
                    st.error(f"{filename} absent ou inaccessible (404)")

                # Bouton pour lancer l'optimisation
                cache_key = f"mistral_opt_{filename}"
                if st.button(f"Optimiser {filename} avec Mistral", key=f"btn_{filename}", use_container_width=True):
                    with st.spinner(f"Mistral analyse {filename}..."):
                        optimized = generate_mistral_optimization(content, filename, base_url, found)
                        st.session_state[cache_key] = optimized

                # Affichage côte à côte
                col_left, col_right = st.columns(2)

                with col_left:
                    st.markdown(f"**Existant** {'✅' if found else '❌'}")
                    st.code(content if found else f"# {filename} inexistant", language="text")

                with col_right:
                    st.markdown("**Proposition Mistral** 🤖")
                    if cache_key in st.session_state:
                        st.code(st.session_state[cache_key], language="text")
                    else:
                        st.info("Cliquez sur le bouton ci-dessus pour générer une proposition optimisée.")

def calculate_page_score(page):
    """
    Calcule le score GEO avancé d'une page
    Utilise le nouveau système de scoring multicritère
    """
    try:
        from modules.geo_scoring import GEOScorer
        scorer = GEOScorer()
        result = scorer.calculate_score(page)
        return result['total_score'], result['grade'], result['breakdown'], result['recommendations']
    except:
        # Fallback si geo_scoring n'existe pas
        score = 70  # Score par défaut
        grade = 'B'
        breakdown = {}
        recommendations = []
        return score, grade, breakdown, recommendations

def get_clean_label(title, url, domain):
    try:
        clean = re.split(r' [-|:|•] ', title)[0]
        if len(clean) < 4: clean = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
        return clean[:20] + ".." if len(clean) > 22 else clean
    except: return "Page"

# =============================================================================
# 2b. CATÉGORISATION INTELLIGENTE DES URLs
# =============================================================================

# Dictionnaire de patterns -> catégories pour la classification des URLs
URL_CATEGORY_PATTERNS = {
    "Offres d'emploi": ['metier', 'emploi', 'offre', 'recrutement', 'carriere', 'poste', 'job', 'candidat', 'postuler'],
    "Témoignages": ['temoignage', 'portrait', 'parcours', 'interview', 'histoire', 'vecu', 'retour-experience'],
    "Actualités": ['actualite', 'actu', 'news', 'blog', 'article', 'presse', 'communique', 'evenement'],
    "Formation": ['formation', 'ecole', 'cursus', 'diplome', 'stage', 'apprentissage', 'etude'],
    "Présentation": ['decouvrir', 'qui-sommes', 'a-propos', 'about', 'presentation', 'mission', 'valeur', 'histoire'],
    "FAQ / Aide": ['faq', 'aide', 'question', 'contact', 'support', 'assistance'],
    "Légal": ['mention', 'legal', 'cgu', 'cgv', 'confidentialite', 'cookie', 'politique', 'condition', 'rgpd'],
    "Médias": ['media', 'video', 'photo', 'galerie', 'image', 'reportage', 'documentaire'],
    "Espace candidat": ['espace', 'compte', 'profil', 'inscription', 'connexion', 'login', 'dashboard'],
}

def categorize_urls(results):
    """Classe les URLs crawlées par catégories intelligentes"""
    categories = defaultdict(list)

    for page in results:
        url = page.get('url', '')
        title = (page.get('title', '') or '').lower()
        h1 = (page.get('h1', '') or '').lower()
        path = urlparse(url).path.lower()

        # Texte combiné pour la recherche
        search_text = f"{path} {title} {h1}"

        matched = False
        for category, keywords in URL_CATEGORY_PATTERNS.items():
            if any(kw in search_text for kw in keywords):
                categories[category].append(page)
                matched = True
                break

        if not matched:
            # Fallback : catégoriser par premier segment de chemin
            segments = [s for s in path.split('/') if s and s not in ['fr', 'en', 'de', 'es', 'www']]
            if segments:
                group = segments[0].replace('-', ' ').replace('_', ' ').title()
                categories[f"📂 {group}"].append(page)
            else:
                categories["Pages statiques"].append(page)

    return dict(sorted(categories.items(), key=lambda x: -len(x[1])))

def render_url_journal(results):
    """Affiche le journal des URLs crawlées classées par catégories"""
    categories = categorize_urls(results)

    st.markdown("#### 📋 Journal des pages crawlées")
    st.caption(f"{len(results)} pages classées en {len(categories)} catégories")

    for cat_name, pages in categories.items():
        with st.expander(f"{cat_name} ({len(pages)} pages)", expanded=False):
            for p in pages:
                score_data = calculate_page_score(p)
                if isinstance(score_data, tuple):
                    sc, grade, _, _ = score_data
                else:
                    sc, grade = score_data, 'N/A'

                # Couleur selon score (sévère)
                if sc >= 95:
                    badge_color = "#10b981"
                elif sc >= 50:
                    badge_color = "#f97316"
                else:
                    badge_color = "#ef4444"

                title = p.get('title', 'Sans titre')
                url = p.get('url', '')
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #f1f5f9;">'
                    f'<span style="background:{badge_color};color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:700;min-width:32px;text-align:center;">{grade}</span>'
                    f'<span style="font-size:0.9rem;font-weight:500;">{title}</span>'
                    f'<span style="font-size:0.75rem;color:#94a3b8;margin-left:auto;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{url}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

# =============================================================================
# 3. RENDU DU GRAPHE (FIX VRAI PLEIN ÉCRAN + LÉGENDE)
# =============================================================================

def render_interactive_graph(G, show_health=False):
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
    
    # LÉGENDE MODE SANTÉ
    legend_html = ""
    if show_health:
        legend_html = """
        <div id="health-legend" style="
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            font-family: 'Inter', sans-serif;
            z-index: 9998;
        ">
            <div style="font-weight: 600; margin-bottom: 10px; font-size: 13px;">Score AI-READABLE</div>
            <div style="display: flex; align-items: center; margin-bottom: 6px;">
                <div style="width: 16px; height: 16px; background: #10b981; border-radius: 50%; margin-right: 8px;"></div>
                <span style="font-size: 12px;">95-100 : Optimisé IA</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 6px;">
                <div style="width: 16px; height: 16px; background: #f97316; border-radius: 50%; margin-right: 8px;"></div>
                <span style="font-size: 12px;">50-94 : Non optimisé</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 16px; height: 16px; background: #ef4444; border-radius: 50%; margin-right: 8px;"></div>
                <span style="font-size: 12px;">0-49 : Critique</span>
            </div>
        </div>
        """
    
    # CODE JS AMÉLIORÉ
    custom_code = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        
        * {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        body, html {{
            font-family: 'Inter', sans-serif !important;
            color: #0f172a;
            margin: 0;
            padding: 0;
        }}
        
        .vis-network canvas {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* VRAI PLEIN ÉCRAN */
        #mynetwork:fullscreen {{
            width: 100vw !important;
            height: 100vh !important;
        }}
        
        #mynetwork:-webkit-full-screen {{
            width: 100vw !important;
            height: 100vh !important;
        }}
        
        #mynetwork:-moz-full-screen {{
            width: 100vw !important;
            height: 100vh !important;
        }}
        
        #mynetwork:-ms-fullscreen {{
            width: 100vw !important;
            height: 100vh !important;
        }}
    </style>
    <script>
        // Gestion des clics sur les nœuds
        network.on("click", function (params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                if (nodeId.startsWith('http')) {{
                    window.open(nodeId, '_blank');
                }}
            }}
        }});
        
        // VRAI PLEIN ÉCRAN sur #mynetwork directement
        function toggleFullscreen() {{
            var elem = document.getElementById('mynetwork');
            if (!document.fullscreenElement && !document.mozFullScreenElement && 
                !document.webkitFullscreenElement && !document.msFullscreenElement) {{
                if (elem.requestFullscreen) {{
                    elem.requestFullscreen();
                }} else if (elem.msRequestFullscreen) {{
                    elem.msRequestFullscreen();
                }} else if (elem.mozRequestFullScreen) {{
                    elem.mozRequestFullScreen();
                }} else if (elem.webkitRequestFullscreen) {{
                    elem.webkitRequestFullscreen();
                }}
            }} else {{
                if (document.exitFullscreen) {{
                    document.exitFullscreen();
                }} else if (document.msExitFullscreen) {{
                    document.msExitFullscreen();
                }} else if (document.mozCancelFullScreen) {{
                    document.mozCancelFullScreen();
                }} else if (document.webkitExitFullscreen) {{
                    document.webkitExitFullscreen();
                }}
            }}
        }}
        
        // Ajout du bouton plein écran
        var fullscreenBtn = document.createElement('button');
        fullscreenBtn.innerHTML = '⛶ Plein écran';
        fullscreenBtn.style.cssText = `
            position: fixed;
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
        fullscreenBtn.onmouseover = function() {{
            this.style.background = '#1e293b';
            this.style.transform = 'translateY(-1px)';
            this.style.boxShadow = '0 4px 6px rgba(0,0,0,0.15)';
        }};
        fullscreenBtn.onmouseout = function() {{
            this.style.background = '#0f172a';
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 1px 2px rgba(0,0,0,0.1)';
        }};
        fullscreenBtn.onclick = toggleFullscreen;
        document.body.appendChild(fullscreenBtn);
    </script>
    {legend_html}
    """
    
    components.html(html.replace("</body>", custom_code + "</body>"), height=900)

# =============================================================================
# 4. ONGLET MÉTHODOLOGIE
# =============================================================================

def render_methodologie():
    """Méthodologie Hotaru - Version modulaire intégrée à l'onglet AUDIT"""

    st.markdown("""
    <style>
        .methodo-container { max-width: 900px; margin: auto; padding: 20px; }
        .methodo-title { font-size: 2.8rem; font-weight: 800; letter-spacing: -0.04em; margin-bottom: 0.2rem; color: #000; }
        .methodo-subtitle { font-size: 1.1rem; color: #94a3b8; margin-bottom: 4rem; font-weight: 400; text-transform: uppercase; letter-spacing: 0.1em; }
        .methodo-header { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em; color: #000; margin-bottom: 2rem; border-bottom: 2px solid #000; padding-bottom: 8px; width: fit-content; }
        .methodo-card { background: #ffffff; border: 1px solid #e2e8f0; padding: 30px; margin-bottom: -1px; transition: all 0.2s ease; }
        .methodo-card:hover { background: #f8fafc; z-index: 10; position: relative; }
        .methodo-badge { font-size: 0.65rem; font-weight: 800; color: #64748b; border: 1px solid #e2e8f0; padding: 2px 8px; margin-bottom: 15px; display: inline-block; }
        .methodo-grade-row { display: flex; justify-content: space-between; padding: 15px 0; border-bottom: 1px solid #f1f5f9; }
        .methodo-grade-letter { font-weight: 800; font-size: 1.2rem; }
        .methodo-grade-range { font-family: monospace; color: #64748b; }
        .methodo-health { border: 1px solid #000; padding: 40px; margin: 50px 0; background: #fff; }
        .methodo-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 10px; }
        .methodo-tips { list-style: none; padding: 0; }
        .methodo-tips li { padding: 15px 0; border-bottom: 1px solid #f1f5f9; color: #000; font-size: 1rem; display: flex; align-items: center; }
        .methodo-tips li::before { content: ""; width: 12px; height: 1px; background: #000; margin-right: 20px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="methodo-container">', unsafe_allow_html=True)
    st.markdown('<div class="methodo-title">MÉTHODOLOGIE HOTARU</div>', unsafe_allow_html=True)
    st.markdown('<div class="methodo-subtitle">2026 Framework</div>', unsafe_allow_html=True)

    # 01. CONCEPT
    st.markdown('<div class="methodo-header">01. CONCEPT</div>', unsafe_allow_html=True)
    st.write(
        "L'optimisation des actifs sémantiques pour la citation directe par les LLMs. "
        "Le score Hotaru mesure la capacité d'un contenu à être extrait et validé par les moteurs génératifs."
    )
    st.markdown('<div style="margin-bottom:4rem;"></div>', unsafe_allow_html=True)

    # 02. CRITÈRES
    st.markdown('<div class="methodo-header">02. CRITÈRES D\'ANALYSE</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="methodo-card">
            <div class="methodo-badge">15 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Meta Description</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Précision sémantique du résumé pour le crawling par les agents IA.</div>
        </div>
        <div class="methodo-card">
            <div class="methodo-badge">15 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Données Structurées</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Schémas JSON-LD, identification des entités et relations.</div>
        </div>
        <div class="methodo-card">
            <div class="methodo-badge">20 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Architecture Sémantique</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Logique de titrage Hn et structuration par listes/tableaux.</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="methodo-card">
            <div class="methodo-badge">15 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Profondeur & Sources</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Richesse textuelle et autorité des maillages externes.</div>
        </div>
        <div class="methodo-card">
            <div class="methodo-badge">10 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Richesse en Entités</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Extraction de faits, dates et données propriétaires.</div>
        </div>
        <div class="methodo-card">
            <div class="methodo-badge">25 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Technique IA-Ready</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Accessibilité bots et présence du standard llms.txt.</div>
        </div>
        """, unsafe_allow_html=True)

    # 03. SCORING
    st.markdown('<div style="margin-bottom:4rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="methodo-header">03. SCORING SYSTEM</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="methodo-grade-row"><span class="methodo-grade-letter">A+</span><span class="methodo-grade-range">90 - 100</span></div>
    <div class="methodo-grade-row"><span class="methodo-grade-letter">A</span><span class="methodo-grade-range">80 - 89</span></div>
    <div class="methodo-grade-row"><span class="methodo-grade-letter">B</span><span class="methodo-grade-range">70 - 79</span></div>
    <div class="methodo-grade-row"><span class="methodo-grade-letter">C</span><span class="methodo-grade-range">50 - 69</span></div>
    <div class="methodo-grade-row"><span class="methodo-grade-letter">F</span><span class="methodo-grade-range"> &lt; 50</span></div>
    """, unsafe_allow_html=True)

    # Health monitoring
    st.markdown("""
    <div class="methodo-health">
        <div style="font-weight:800; text-transform:uppercase; font-size:0.7rem; letter-spacing:0.2em; margin-bottom:2rem;">Health Monitoring</div>
        <div style="display:flex; gap:30px;">
            <div><span class="methodo-dot" style="background:#22c55e;"></span><span style="font-size:0.9rem; font-weight:600;">OPTIMAL</span></div>
            <div><span class="methodo-dot" style="background:#eab308;"></span><span style="font-size:0.9rem; font-weight:600;">AVERAGE</span></div>
            <div><span class="methodo-dot" style="background:#ef4444;"></span><span style="font-size:0.9rem; font-weight:600;">CRITICAL</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 04. DIRECTIVES
    st.markdown('<div class="methodo-header">04. STRATEGIC DIRECTIVES</div>', unsafe_allow_html=True)
    st.markdown("""
    <ul class="methodo-tips">
        <li>Privilégier les formats factuels (tableaux, data-points).</li>
        <li>Convertir les paragraphes denses en listes structurées.</li>
        <li>Implémenter le balisage JSON-LD spécifique.</li>
        <li>Utiliser des titres sous forme de questions directes.</li>
        <li>Maintenir une fraîcheur de donnée &lt; 90 jours.</li>
    </ul>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

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
            
            # ✅ NOUVEAU : Textarea pour URLs multiples
            url_input = c1.text_area(
                "URLs à analyser (une par ligne)",
                placeholder="https://example.com/\nhttps://example.com/section1\nhttps://example.com/section2",
                height=100,
                help="Entrez une ou plusieurs URLs du même domaine, une par ligne. Le scraper explorera toutes ces sections."
            )
            
            default_ws = "" if selected_ws == "+ Créer Nouveau" else selected_ws
            ws_in = c2.text_input("Nom du Projet", value=default_ws)
            
            # SLIDER 10 À 10 000 PAGES avec paliers intelligents
            limit_in = st.select_slider(
                "Nombre de pages à analyser",
                options=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
                value=100,
                help="Analyse de 10 à 10 000 pages. Plus le nombre est élevé, plus l'analyse sera longue."
            )
            
            if st.button("Lancer Hotaru", use_container_width=True):
                if url_input:
                    # ✅ Parser les URLs (une par ligne, ignorer les lignes vides)
                    urls = [line.strip() for line in url_input.strip().split('\n') if line.strip()]
                    
                    if not urls:
                        st.error("Veuillez entrer au moins une URL")
                        return
                    
                    # ✅ Vérifier que toutes les URLs sont du même domaine
                    domains = [urlparse(url).netloc for url in urls]
                    if len(set(domains)) > 1:
                        st.error(f"❌ Toutes les URLs doivent être du même domaine. Trouvé: {', '.join(set(domains))}")
                        return
                    
                    # Prendre la première URL comme URL de base pour l'infra check
                    base_url = urls[0]
                    
                    bar = st.progress(0, "Analyse infrastructure...")
                    infra, score = check_geo_infrastructure(base_url)
                    st.session_state.geo_infra = infra
                    st.session_state.geo_score = score
                    
                    # ✅ NOUVEAU : Lancement avec liste d'URLs
                    scr = SmartScraper(urls, max_urls=limit_in)
                    res, stats = scr.run_analysis(
                        progress_callback=lambda m, v: bar.progress(v, m)
                    )
                    
                    st.session_state.update({
                        "results": res, 
                        "clusters": scr.get_pattern_summary(), 
                        "target_url": base_url,  # Pour compatibilité avec le reste du code
                        "start_urls": urls,  # ✅ NOUVEAU : Garder la liste complète
                        "current_ws": ws_in if ws_in else "Non classé",
                        "crawl_stats": stats.get('stats', {})
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
                    "current_ws": selected_ws,
                    "crawl_stats": data.get('stats', {})
                })
                st.rerun()

        # --- AFFICHAGE DES RÉSULTATS ---
        if "results" in st.session_state:
            st.divider()
            
            # 1. Dashboard Infra avec couleur sévère
            g_score = st.session_state.get("geo_score", 0)
            if g_score >= 95:
                score_color = "#10b981"
                score_label = "Optimisé"
            elif g_score >= 50:
                score_color = "#f97316"
                score_label = "Non optimisé"
            else:
                score_color = "#ef4444"
                score_label = "Critique"

            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
                f'<h3 style="margin:0;">Score Infrastructure IA : <span style="color:{score_color};">{g_score}/100</span></h3>'
                f'<span style="background:{score_color};color:white;padding:4px 12px;border-radius:4px;font-size:0.8rem;font-weight:700;">{score_label}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            if st.session_state.get("geo_infra"):
                cols = st.columns(4)
                for i, (name, d) in enumerate(st.session_state.geo_infra.items()):
                    with cols[i]:
                        status = "status-ok" if d['status'] else "status-err"
                        txt = "OK" if d['status'] else "MISSING"
                        st.markdown(f"""<div class="infra-box"><b>{name}</b><br><span class="{status}">{txt}</span><div class="infra-desc">{d['meta']['desc']}</div></div>""", unsafe_allow_html=True)

            # ✅ Module Optimisation IA (Mistral) pour robots.txt et llms.txt
            render_mistral_optimization(st.session_state.get("target_url", ""))

            st.divider()

            # ✅ NOUVEAU : Stats détaillées du crawl
            if "crawl_stats" in st.session_state and st.session_state.crawl_stats:
                with st.expander("📊 Statistiques détaillées du crawl", expanded=True):
                    stats = st.session_state.crawl_stats
                    
                    # ✅ Afficher les URLs de départ si mode multi-URLs
                    if "start_urls" in st.session_state and len(st.session_state.start_urls) > 1:
                        st.markdown(f"**🔗 Points d'entrée : {len(st.session_state.start_urls)}**")
                        with st.expander("Voir les URLs de départ"):
                            for i, url in enumerate(st.session_state.start_urls, 1):
                                st.text(f"{i}. {url}")
                        st.markdown("---")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("✅ Pages crawlées", stats.get('pages_crawled', 0))
                        st.metric("⚠️ Pages ignorées", stats.get('pages_skipped', 0))
                    
                    with col2:
                        st.metric("🔗 Liens découverts", stats.get('links_discovered', 0))
                        st.metric("🚫 Liens filtrés", stats.get('links_filtered', 0))
                    
                    with col3:
                        st.metric("🔄 Doublons", stats.get('links_duplicate', 0))
                        st.metric("⛔ Queue pleine", stats.get('queue_full_blocks', 0))
                    
                    with col4:
                        st.metric("❌ Erreurs", stats.get('errors', 0))
                        st.metric("📍 URLs visitées", len(st.session_state.results))
                
                st.divider()

            # ✅ Journal des pages crawlées par catégories
            with st.expander("📋 Journal des pages crawlées (par catégories)", expanded=False):
                render_url_journal(st.session_state.results)

            st.divider()

            # 2. Commandes Graphe
            c_expert, c_save_name, c_save_btn = st.columns([1, 2, 1])
            expert_on = c_expert.toggle("Score AI-READABLE", value=False)
            
            domain = urlparse(st.session_state.target_url).netloc
            s_name = c_save_name.text_input("Nom sauvegarde", value=domain.split('.')[0], label_visibility="collapsed")
            
            # 3. Sauvegarde Sécurisée (Trimming + Limite)
            if c_save_btn.button("Sauvegarder", use_container_width=True):
                # ✅ LIMITE : Maximum 100 pages sauvegardées pour éviter erreur GSheet
                max_pages_to_save = 100
                results_to_save = st.session_state.results[:max_pages_to_save]
                
                clean_results = []
                for r in results_to_save:
                    clean_results.append({
                        "url": r.get("url"),
                        "title": r.get("title", "")[:50],  # ✅ Réduit de 100 à 50
                        "description": r.get("description", "")[:100],  # ✅ Réduit de 200 à 100
                        "h1": r.get("h1", "")[:50],  # ✅ Réduit de 100 à 50
                        "response_time": round(r.get("response_time", 0), 2),  # ✅ Arrondi
                        "has_structured_data": r.get("has_structured_data", False),
                        "h2_count": r.get("h2_count", 0)
                        # ✅ Suppression de lists_count et html_content
                    })
                
                # ✅ Limiter aussi les clusters (garder que les 5 premiers samples par cluster)
                compact_clusters = []
                for cluster in st.session_state.clusters:
                    compact_clusters.append({
                        "name": cluster["name"],
                        "count": cluster["count"],
                        "samples": []  # ✅ On ne garde PAS les samples (déjà dans results)
                    })
                
                payload = {
                    "results": clean_results,
                    "clusters": compact_clusters,
                    "geo_infra": st.session_state.get('geo_infra', {}),
                    "geo_score": st.session_state.get('geo_score', 0),
                    "stats": {
                        "pages_crawled": st.session_state.crawl_stats.get('pages_crawled', 0),
                        "links_discovered": st.session_state.crawl_stats.get('links_discovered', 0),
                        "start_urls_count": st.session_state.crawl_stats.get('start_urls_count', 1)
                    },
                    "start_urls": st.session_state.get('start_urls', [st.session_state.target_url])[:5]  # ✅ Max 5 URLs
                }
                
                # ✅ Afficher warning si limitation
                if len(st.session_state.results) > max_pages_to_save:
                    st.warning(f"⚠️ Seules les {max_pages_to_save} premières pages sur {len(st.session_state.results)} seront sauvegardées (limite Google Sheets)")
                
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
                        breakdown = {}
                        recommendations = []
                    
                    # ÉCHELLE DE COULEUR SÉVÈRE (vente : tout doit crier "problème")
                    if expert_on:
                        if sc >= 95:
                            col = "#10b981"  # Vert - Parfait uniquement
                        elif sc >= 50:
                            col = "#f97316"  # Orange alerte - Non optimisé
                        else:
                            col = "#ef4444"  # Rouge - Critique
                    else:
                        col = "#e2e8f0"  # Gris très clair standard
                    
                    # Label avec note si mode expert
                    label = get_clean_label(p.get('title',''), p['url'], domain)
                    if expert_on and isinstance(score_data, tuple):
                        label = f"{label}\\n[{grade}]"
                    
                    # TOOLTIP DÉTAILLÉ avec éléments manquants
                    tooltip_parts = []
                    if expert_on and isinstance(score_data, tuple):
                        tooltip_parts.append(f"Score AI-READABLE: {sc}/100 - Grade: {grade}")
                        
                        # Ajouter les éléments manquants
                        missing = []
                        if not p.get('description'):
                            missing.append("❌ Meta description")
                        if not p.get('h1'):
                            missing.append("❌ H1")
                        if not p.get('has_structured_data'):
                            missing.append("❌ JSON-LD")
                        if p.get('h2_count', 0) < 2:
                            missing.append("⚠️ Peu de H2")
                        
                        if missing:
                            tooltip_parts.append("\\n\\nÉléments manquants:\\n" + "\\n".join(missing))
                        
                        # Ajouter les recommandations principales
                        if recommendations:
                            top_reco = recommendations[:2]
                            tooltip_parts.append("\\n\\nRecommandations:\\n" + "\\n".join(f"• {r}" for r in top_reco))
                    
                    tooltip = "\\n".join(tooltip_parts) if tooltip_parts else ""
                    
                    G.add_node(
                        p['url'], 
                        label=label, 
                        size=12, 
                        color=col,
                        font={'color': '#0f172a', 'face': 'Inter'},
                        title=tooltip
                    )
                    G.add_edge(c_id, p['url'])
            
            # 5. Rendu du graphe avec légende si mode santé
            render_interactive_graph(G, show_health=expert_on)
    
    # ============= TAB 2 : MÉTHODOLOGIE =============
    with tab2:
        render_methodologie()
