# =============================================================================
# AUDIT GEO - HOTARU DESIGN SYSTEM
# =============================================================================

import streamlit as st
import json
import re
import requests
import zlib
import base64
from urllib.parse import urlparse
from collections import defaultdict, Counter
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from core.database import AuditDatabase
from core.scraping import SmartScraper

# =============================================================================
# 1. FONCTIONS TECHNIQUES (SCORING & INFRA)
# =============================================================================

def check_geo_infrastructure(base_url):
    domain = base_url.rstrip('/')
    assets = {
        "robots.txt": {"url": f"{domain}/robots.txt", "desc": "Autorise GPTBot et les crawlers IA."},
        "sitemap.xml": {"url": f"{domain}/sitemap.xml", "desc": "Guide d'indexation pour les moteurs de reponse."},
        "llms.txt": {"url": f"{domain}/llms.txt", "desc": "Standard 2025 pour la consommation LLM."},
        "JSON-LD": {"url": domain, "desc": "Donnees structurees (Entites de marque)."}
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
    """Recupere le contenu d'un fichier (robots.txt, llms.txt) sur le site"""
    url = f"{base_url.rstrip('/')}/{filename}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.text.strip(), True
        else:
            return f"# {filename} non trouve (HTTP {r.status_code})", False
    except Exception as e:
        return f"# Erreur de recuperation : {e}", False


def generate_mistral_optimization(file_content, filename, site_url, found):
    """Appelle Mistral pour generer une version optimisee du fichier"""
    try:
        api_key = st.secrets["mistral"]["api_key"]
    except Exception:
        return "Cle API Mistral manquante dans les secrets Streamlit."

    if filename == "robots.txt":
        prompt = f"""Tu es un expert en SEO technique et AI-Readability.
Voici le fichier robots.txt actuel du site {site_url} :

{file_content if found else "Le fichier robots.txt n'existe pas ou est vide."}

Genere un robots.txt PARFAIT et optimise pour les agents IA (GPTBot, ChatGPT-User, Google-Extended, ClaudeBot, PerplexityBot, Bingbot).
Le fichier doit :
1. Autoriser explicitement les crawlers IA importants
2. Referencer le sitemap.xml
3. Bloquer les ressources inutiles (/admin, /wp-login, etc.)
4. Suivre les meilleures pratiques 2025-2026

Reponds UNIQUEMENT avec le contenu du fichier robots.txt, sans aucun commentaire ni explication autour."""
    else:  # llms.txt - Gold Standard hybride EN/FR
        prompt = f"""Tu es un expert en AI-Readability et standards LLM. Tu dois generer un fichier llms.txt "Gold Standard".

Voici le fichier llms.txt actuel du site {site_url} :

{file_content if found else "Le fichier llms.txt n'existe pas."}

Genere un llms.txt PARFAIT selon le standard llms.txt 2025 avec cette structure OBLIGATOIRE :

1. HEADER (EN ANGLAIS) : Une description courte du site et de son objectif en anglais.
   Cela maximise la comprehension contextuelle par les modeles LLM globaux (GPT, Claude, Gemini, etc.)

2. BODY (EN FRANCAIS) : La liste des liens et descriptions des sections principales du site,
   en francais, car c'est la langue cible du contenu et du recrutement.

3. JUSTIFICATION (commentaire en bas) : Ajoute un bloc de commentaire expliquant pourquoi
   cette structure hybride (Header EN / Contenu FR) maximise le score AI-Readability.
   Les LLMs globaux comprennent mieux le contexte en anglais, mais le contenu doit rester
   en francais pour referer correctement les pages.

Suis la specification llms.txt (https://llmstxt.org/).
Le site est : {site_url}

Reponds UNIQUEMENT avec le contenu du fichier llms.txt, sans aucune explication autour."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": "Tu es un expert en optimisation de sites web pour les agents IA. Tu generes uniquement du code/config, jamais d'explications."},
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
    """Module d'optimisation IA avec comparatif existant vs proposition Mistral"""
    if not base_url:
        return

    with st.expander("OPTIMISATION IA  /  robots.txt & llms.txt", expanded=False):
        st.markdown(
            '<p style="font-size:0.8rem;color:#94a3b8;margin-bottom:20px;">'
            'Analyse et generation automatique via Mistral AI</p>',
            unsafe_allow_html=True
        )

        files_to_optimize = ["robots.txt", "llms.txt"]
        tabs = st.tabs(files_to_optimize)

        for idx, filename in enumerate(files_to_optimize):
            with tabs[idx]:
                content, found = fetch_file_content(base_url, filename)

                # Status badge
                if found:
                    st.markdown(
                        f'<span class="status-badge status-complete">PRESENT</span>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<span class="status-badge status-failed">ABSENT</span>',
                        unsafe_allow_html=True
                    )

                st.markdown("<br>", unsafe_allow_html=True)

                cache_key = f"mistral_opt_{filename}"
                if st.button(f"Generer proposition optimisee", key=f"btn_{filename}", use_container_width=True):
                    with st.spinner(f"Mistral analyse {filename}..."):
                        optimized = generate_mistral_optimization(content, filename, base_url, found)
                        st.session_state[cache_key] = optimized

                col_left, col_right = st.columns(2)

                with col_left:
                    st.markdown("**Existant**")
                    st.code(content if found else f"# {filename} inexistant", language="text")

                with col_right:
                    st.markdown("**Proposition Mistral**")
                    if cache_key in st.session_state:
                        st.code(st.session_state[cache_key], language="text")
                    else:
                        st.caption("Cliquez sur le bouton pour generer une proposition.")


def calculate_page_score(page):
    """Calcule le score GEO avance d'une page"""
    try:
        from modules.geo_scoring import GEOScorer
        scorer = GEOScorer()
        result = scorer.calculate_score(page)
        return result['total_score'], result['grade'], result['breakdown'], result['recommendations']
    except:
        return 70, 'B', {}, []


def get_clean_label(title, url, domain):
    try:
        clean = re.split(r' [-|:|] ', title)[0]
        if len(clean) < 4: clean = url.rstrip('/').split('/')[-1].replace('-', ' ').capitalize()
        return clean[:20] + ".." if len(clean) > 22 else clean
    except: return "Page"


def _score_color(score):
    """Retourne la couleur selon l'echelle severe"""
    if score >= 95:
        return "#10b981"
    elif score >= 50:
        return "#f97316"
    else:
        return "#ef4444"


# =============================================================================
# 2. CATEGORISATION INTELLIGENTE DES URLs
# =============================================================================

URL_CATEGORY_PATTERNS = {
    "Offres d'emploi": ['metier', 'emploi', 'offre', 'recrutement', 'carriere', 'poste', 'job', 'candidat', 'postuler'],
    "Temoignages": ['temoignage', 'portrait', 'parcours', 'interview', 'histoire', 'vecu', 'retour-experience'],
    "Actualites": ['actualite', 'actu', 'news', 'blog', 'article', 'presse', 'communique', 'evenement'],
    "Formation": ['formation', 'ecole', 'cursus', 'diplome', 'stage', 'apprentissage', 'etude'],
    "Presentation": ['decouvrir', 'qui-sommes', 'a-propos', 'about', 'presentation', 'mission', 'valeur'],
    "FAQ / Aide": ['faq', 'aide', 'question', 'contact', 'support', 'assistance'],
    "Legal": ['mention', 'legal', 'cgu', 'cgv', 'confidentialite', 'cookie', 'politique', 'condition', 'rgpd'],
    "Medias": ['media', 'video', 'photo', 'galerie', 'image', 'reportage', 'documentaire'],
    "Espace candidat": ['espace', 'compte', 'profil', 'inscription', 'connexion', 'login', 'dashboard'],
}


def categorize_urls(results):
    """Classe les URLs crawlees par categories intelligentes"""
    categories = defaultdict(list)

    for page in results:
        url = page.get('url', '')
        title = (page.get('title', '') or '').lower()
        h1 = (page.get('h1', '') or '').lower()
        path = urlparse(url).path.lower()
        search_text = f"{path} {title} {h1}"

        matched = False
        for category, keywords in URL_CATEGORY_PATTERNS.items():
            if any(kw in search_text for kw in keywords):
                categories[category].append(page)
                matched = True
                break

        if not matched:
            segments = [s for s in path.split('/') if s and s not in ['fr', 'en', 'de', 'es', 'www']]
            if segments:
                group = segments[0].replace('-', ' ').replace('_', ' ').title()
                categories[group].append(page)
            else:
                categories["Pages statiques"].append(page)

    return dict(sorted(categories.items(), key=lambda x: -len(x[1])))


# =============================================================================
# 3. JOURNAUX (3 VUES)
# =============================================================================

def render_journal_crawled(results):
    """Vue A : Journal des pages crawlees (validees), classees par categories"""
    categories = categorize_urls(results)

    st.markdown(
        f'<p style="font-size:0.8rem;color:#94a3b8;margin-bottom:16px;">'
        f'{len(results)} pages  /  {len(categories)} categories</p>',
        unsafe_allow_html=True
    )

    for cat_name, pages in categories.items():
        with st.expander(f"**{cat_name}**  ({len(pages)})", expanded=False):
            for p in pages:
                score_data = calculate_page_score(p)
                if isinstance(score_data, tuple):
                    sc, grade, _, _ = score_data
                else:
                    sc, grade = score_data, 'N/A'

                col = _score_color(sc)
                title = p.get('title', 'Sans titre')
                url = p.get('url', '')

                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f1f5f9;">'
                    f'<span style="background:{col};color:white;padding:2px 8px;font-size:0.7rem;font-weight:800;min-width:28px;text-align:center;">{grade}</span>'
                    f'<a href="{url}" target="_blank" style="font-size:0.9rem;font-weight:600;color:#0f172a;text-decoration:none;border-bottom:1px solid #e2e8f0;">{title}</a>'
                    f'<span style="font-size:0.7rem;color:#94a3b8;margin-left:auto;max-width:350px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:monospace;">{urlparse(url).path}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )


def render_journal_filtered(filtered_log):
    """Vue B : Journal des liens filtres"""
    if not filtered_log:
        st.caption("Aucun lien filtre lors de ce crawl.")
        return

    st.markdown(
        f'<p style="font-size:0.8rem;color:#94a3b8;margin-bottom:16px;">'
        f'{len(filtered_log)} liens exclus par les filtres</p>',
        unsafe_allow_html=True
    )

    # Grouper par motif
    by_pattern = defaultdict(list)
    for url, pattern in filtered_log:
        by_pattern[pattern].append(url)

    for pattern, urls in sorted(by_pattern.items(), key=lambda x: -len(x[1])):
        with st.expander(f"**{pattern}**  ({len(urls)} liens)", expanded=False):
            for url in urls[:100]:  # Limiter l'affichage
                st.markdown(
                    f'<div style="padding:4px 0;border-bottom:1px solid #f8fafc;font-size:0.8rem;font-family:monospace;color:#64748b;">'
                    f'{url}</div>',
                    unsafe_allow_html=True
                )
            if len(urls) > 100:
                st.caption(f"... et {len(urls) - 100} autres")


def render_journal_duplicates(duplicate_log):
    """Vue C : Journal des doublons"""
    if not duplicate_log:
        st.caption("Aucun doublon detecte lors de ce crawl.")
        return

    # Compter les occurrences
    counts = Counter(duplicate_log)
    sorted_dupes = sorted(counts.items(), key=lambda x: -x[1])

    st.markdown(
        f'<p style="font-size:0.8rem;color:#94a3b8;margin-bottom:16px;">'
        f'{len(duplicate_log)} doublons detectes  /  {len(counts)} URLs uniques</p>',
        unsafe_allow_html=True
    )

    for url, count in sorted_dupes[:200]:
        path = urlparse(url).path or '/'
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;padding:6px 0;border-bottom:1px solid #f8fafc;">'
            f'<span style="background:#0f172a;color:white;padding:2px 10px;font-size:0.7rem;font-weight:800;min-width:20px;text-align:center;">{count}x</span>'
            f'<span style="font-size:0.85rem;font-family:monospace;color:#64748b;">{path}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    if len(sorted_dupes) > 200:
        st.caption(f"... et {len(sorted_dupes) - 200} autres URLs")


# =============================================================================
# 4. RENDU DU GRAPHE
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
            "smooth": {"type": "dynamic", "roundness": 0.2},
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
            "stabilization": {"enabled": True, "iterations": 200}
        }
    }

    nt.set_options(json.dumps(opts))
    path = "temp_graph.html"
    nt.save_graph(path)

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    legend_html = ""
    if show_health:
        legend_html = """
        <div id="health-legend" style="
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: white;
            padding: 15px;
            border-radius: 0;
            border: 1px solid #e2e8f0;
            font-family: 'Inter', sans-serif;
            z-index: 9998;
        ">
            <div style="font-weight: 800; margin-bottom: 12px; font-size: 0.65rem; letter-spacing: 0.2em; text-transform: uppercase; color: #94a3b8;">Score AI-Readable</div>
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <div style="width: 12px; height: 12px; background: #10b981; margin-right: 10px;"></div>
                <span style="font-size: 0.8rem; font-weight: 600;">95-100  Optimise</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <div style="width: 12px; height: 12px; background: #f97316; margin-right: 10px;"></div>
                <span style="font-size: 0.8rem; font-weight: 600;">50-94  Non optimise</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 12px; height: 12px; background: #ef4444; margin-right: 10px;"></div>
                <span style="font-size: 0.8rem; font-weight: 600;">0-49  Critique</span>
            </div>
        </div>
        """

    custom_code = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        * {{ font-family: 'Inter', sans-serif !important; }}
        body, html {{ font-family: 'Inter', sans-serif !important; color: #0f172a; margin: 0; padding: 0; }}
        #mynetwork:fullscreen {{ width: 100vw !important; height: 100vh !important; }}
        #mynetwork:-webkit-full-screen {{ width: 100vw !important; height: 100vh !important; }}
    </style>
    <script>
        network.on("click", function (params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                if (nodeId.startsWith('http')) {{ window.open(nodeId, '_blank'); }}
            }}
        }});

        function toggleFullscreen() {{
            var elem = document.getElementById('mynetwork');
            if (!document.fullscreenElement) {{
                elem.requestFullscreen && elem.requestFullscreen();
            }} else {{
                document.exitFullscreen && document.exitFullscreen();
            }}
        }}

        var fullscreenBtn = document.createElement('button');
        fullscreenBtn.innerHTML = 'Plein ecran';
        fullscreenBtn.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;padding:10px 24px;background:#0f172a;color:white;border:none;font-family:Inter,sans-serif;font-size:0.75rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;cursor:pointer;';
        fullscreenBtn.onclick = toggleFullscreen;
        document.body.appendChild(fullscreenBtn);
    </script>
    {legend_html}
    """

    components.html(html.replace("</body>", custom_code + "</body>"), height=900)


# =============================================================================
# 5. ONGLET METHODOLOGIE
# =============================================================================

def render_methodologie():
    """Methodologie Hotaru"""

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
    st.markdown('<div class="methodo-title">METHODOLOGIE HOTARU</div>', unsafe_allow_html=True)
    st.markdown('<div class="methodo-subtitle">2026 Framework</div>', unsafe_allow_html=True)

    st.markdown('<div class="methodo-header">01. CONCEPT</div>', unsafe_allow_html=True)
    st.write(
        "L'optimisation des actifs semantiques pour la citation directe par les LLMs. "
        "Le score Hotaru mesure la capacite d'un contenu a etre extrait et valide par les moteurs generatifs."
    )
    st.markdown('<div style="margin-bottom:4rem;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="methodo-header">02. CRITERES D\'ANALYSE</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="methodo-card">
            <div class="methodo-badge">15 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Meta Description</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Precision semantique du resume pour le crawling par les agents IA.</div>
        </div>
        <div class="methodo-card">
            <div class="methodo-badge">15 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Donnees Structurees</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Schemas JSON-LD, identification des entites et relations.</div>
        </div>
        <div class="methodo-card">
            <div class="methodo-badge">20 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Architecture Semantique</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Logique de titrage Hn et structuration par listes/tableaux.</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="methodo-card">
            <div class="methodo-badge">15 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Profondeur & Sources</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Richesse textuelle et autorite des maillages externes.</div>
        </div>
        <div class="methodo-card">
            <div class="methodo-badge">10 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Richesse en Entites</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Extraction de faits, dates et donnees proprietaires.</div>
        </div>
        <div class="methodo-card">
            <div class="methodo-badge">25 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Technique IA-Ready</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Accessibilite bots et presence du standard llms.txt.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="margin-bottom:4rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="methodo-header">03. SCORING SYSTEM</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="methodo-grade-row"><span class="methodo-grade-letter">A+</span><span class="methodo-grade-range">90 - 100</span></div>
    <div class="methodo-grade-row"><span class="methodo-grade-letter">A</span><span class="methodo-grade-range">80 - 89</span></div>
    <div class="methodo-grade-row"><span class="methodo-grade-letter">B</span><span class="methodo-grade-range">70 - 79</span></div>
    <div class="methodo-grade-row"><span class="methodo-grade-letter">C</span><span class="methodo-grade-range">50 - 69</span></div>
    <div class="methodo-grade-row"><span class="methodo-grade-letter">F</span><span class="methodo-grade-range"> &lt; 50</span></div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="methodo-health">
        <div style="font-weight:800; text-transform:uppercase; font-size:0.7rem; letter-spacing:0.2em; margin-bottom:2rem;">Health Monitoring</div>
        <div style="display:flex; gap:30px;">
            <div><span class="methodo-dot" style="background:#10b981;"></span><span style="font-size:0.9rem; font-weight:600;">OPTIMAL</span></div>
            <div><span class="methodo-dot" style="background:#f97316;"></span><span style="font-size:0.9rem; font-weight:600;">NON OPTIMISE</span></div>
            <div><span class="methodo-dot" style="background:#ef4444;"></span><span style="font-size:0.9rem; font-weight:600;">CRITICAL</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="methodo-header">04. STRATEGIC DIRECTIVES</div>', unsafe_allow_html=True)
    st.markdown("""
    <ul class="methodo-tips">
        <li>Privilegier les formats factuels (tableaux, data-points).</li>
        <li>Convertir les paragraphes denses en listes structurees.</li>
        <li>Implementer le balisage JSON-LD specifique.</li>
        <li>Utiliser des titres sous forme de questions directes.</li>
        <li>Maintenir une fraicheur de donnee &lt; 90 jours.</li>
    </ul>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# 6. INTERFACE PRINCIPALE
# =============================================================================

def render_audit_geo():
    db = AuditDatabase()
    user_email = st.session_state.user_email

    tab1, tab2 = st.tabs(["Audit Site", "Methodologie"])

    # ========================== TAB 1 : AUDIT ==========================
    with tab1:
        all_audits = db.load_user_audits(user_email)

        ws_list = []
        for a in all_audits:
            ws_name = str(a.get('workspace', '')).strip()
            if ws_name and ws_name not in ws_list:
                ws_list.append(ws_name)

        if not ws_list: ws_list = ["Nouveau"]
        else: ws_list = sorted(ws_list) + ["+ Creer Nouveau"]

        selected_ws = st.sidebar.selectbox("Projets (Workspaces)", ws_list)
        filtered_audits = [a for a in all_audits if str(a.get('workspace', '')).strip() == selected_ws]

        # --- ZONE DE SCAN ---
        with st.expander("LANCER UNE NOUVELLE ANALYSE", expanded="results" not in st.session_state):
            c1, c2 = st.columns([3, 1])

            url_input = c1.text_area(
                "URLs a analyser (une par ligne)",
                placeholder="https://example.com/\nhttps://example.com/section1",
                height=100,
                help="Entrez une ou plusieurs URLs du meme domaine, une par ligne."
            )

            default_ws = "" if selected_ws == "+ Creer Nouveau" else selected_ws
            ws_in = c2.text_input("Nom du Projet", value=default_ws)

            limit_in = st.select_slider(
                "Nombre de pages a analyser",
                options=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
                value=100,
                help="Analyse de 10 a 10 000 pages."
            )

            if st.button("Lancer Hotaru", use_container_width=True):
                if url_input:
                    urls = [line.strip() for line in url_input.strip().split('\n') if line.strip()]

                    if not urls:
                        st.error("Veuillez entrer au moins une URL")
                        return

                    domains = [urlparse(url).netloc for url in urls]
                    if len(set(domains)) > 1:
                        st.error(f"Toutes les URLs doivent etre du meme domaine. Trouve: {', '.join(set(domains))}")
                        return

                    base_url = urls[0]

                    bar = st.progress(0, "Analyse infrastructure...")
                    infra, score = check_geo_infrastructure(base_url)
                    st.session_state.geo_infra = infra
                    st.session_state.geo_score = score

                    scr = SmartScraper(urls, max_urls=limit_in)
                    res, stats = scr.run_analysis(
                        progress_callback=lambda m, v: bar.progress(v, m)
                    )

                    st.session_state.update({
                        "results": res,
                        "clusters": scr.get_pattern_summary(),
                        "target_url": base_url,
                        "start_urls": urls,
                        "current_ws": ws_in if ws_in else "Non classe",
                        "crawl_stats": stats.get('stats', {}),
                        "filtered_log": stats.get('filtered_log', []),
                        "duplicate_log": stats.get('duplicate_log', [])
                    })
                    st.rerun()

        # --- ARCHIVES ---
        if filtered_audits:
            st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Archives</p>', unsafe_allow_html=True)

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
                    "crawl_stats": data.get('stats', {}),
                    "filtered_log": data.get('filtered_log', []),
                    "duplicate_log": data.get('duplicate_log', [])
                })
                st.rerun()

        # --- RESULTATS ---
        if "results" in st.session_state:
            st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

            # ========== SCORE INFRASTRUCTURE ==========
            g_score = st.session_state.get("geo_score", 0)
            score_color = _score_color(g_score)

            if g_score >= 95:
                score_label = "OPTIMISE"
            elif g_score >= 50:
                score_label = "NON OPTIMISE"
            else:
                score_label = "CRITIQUE"

            st.markdown(
                f'<div style="display:flex;align-items:baseline;gap:16px;margin-bottom:4px;">'
                f'<span style="font-size:2.5rem;font-weight:900;color:{score_color};line-height:1;">{g_score}</span>'
                f'<span style="font-size:0.65rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:#94a3b8;">/100</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<span class="status-badge" style="background:{score_color};color:white;border-color:{score_color};">{score_label}</span>',
                unsafe_allow_html=True
            )
            st.markdown(
                '<p class="section-title" style="margin-top:24px;">Infrastructure IA</p>',
                unsafe_allow_html=True
            )

            if st.session_state.get("geo_infra"):
                cols = st.columns(4)
                for i, (name, d) in enumerate(st.session_state.geo_infra.items()):
                    with cols[i]:
                        status = "status-ok" if d['status'] else "status-err"
                        txt = "OK" if d['status'] else "MISSING"
                        st.markdown(
                            f'<div class="infra-box"><b>{name}</b><br>'
                            f'<span class="{status}">{txt}</span>'
                            f'<div class="infra-desc">{d["meta"]["desc"]}</div></div>',
                            unsafe_allow_html=True
                        )

            # ========== MISTRAL OPTIMIZATION ==========
            render_mistral_optimization(st.session_state.get("target_url", ""))

            st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

            # ========== STATISTIQUES DU CRAWL ==========
            if "crawl_stats" in st.session_state and st.session_state.crawl_stats:
                st.markdown('<p class="section-title">Statistiques du crawl</p>', unsafe_allow_html=True)

                stats = st.session_state.crawl_stats

                if "start_urls" in st.session_state and len(st.session_state.start_urls) > 1:
                    with st.expander(f"**Points d'entree : {len(st.session_state.start_urls)}**"):
                        for i, url in enumerate(st.session_state.start_urls, 1):
                            st.text(f"{i}. {url}")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.markdown(
                        '<div class="zen-metric">'
                        f'<div class="zen-metric-value">{stats.get("pages_crawled", 0)}</div>'
                        '<div class="zen-metric-label">Pages crawlees</div>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(
                        '<div class="zen-metric">'
                        f'<div class="zen-metric-value">{stats.get("links_discovered", 0)}</div>'
                        '<div class="zen-metric-label">Liens decouverts</div>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                with col3:
                    st.markdown(
                        '<div class="zen-metric">'
                        f'<div class="zen-metric-value">{stats.get("links_duplicate", 0)}</div>'
                        '<div class="zen-metric-label">Doublons</div>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                with col4:
                    st.markdown(
                        '<div class="zen-metric">'
                        f'<div class="zen-metric-value">{stats.get("errors", 0)}</div>'
                        '<div class="zen-metric-label">Erreurs</div>'
                        '</div>',
                        unsafe_allow_html=True
                    )

                st.markdown("<br>", unsafe_allow_html=True)

                # Metrics secondaires en plus petit
                s_col1, s_col2, s_col3 = st.columns(3)
                with s_col1:
                    st.caption(f"Pages ignorees : {stats.get('pages_skipped', 0)}")
                with s_col2:
                    st.caption(f"Liens filtres : {stats.get('links_filtered', 0)}")
                with s_col3:
                    st.caption(f"URLs visitees : {len(st.session_state.results)}")

            st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

            # ========== JOURNAUX (3 VUES) ==========
            st.markdown('<p class="section-title">Journaux</p>', unsafe_allow_html=True)

            j_tab1, j_tab2, j_tab3 = st.tabs([
                "Pages crawlees",
                "Liens filtres",
                "Doublons"
            ])

            with j_tab1:
                render_journal_crawled(st.session_state.results)

            with j_tab2:
                render_journal_filtered(st.session_state.get("filtered_log", []))

            with j_tab3:
                render_journal_duplicates(st.session_state.get("duplicate_log", []))

            st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

            # ========== GRAPHE ==========
            st.markdown('<p class="section-title">Graphe</p>', unsafe_allow_html=True)

            c_expert, c_save_name, c_save_btn = st.columns([1, 2, 1])
            expert_on = c_expert.toggle("Score AI-READABLE", value=False)

            domain = urlparse(st.session_state.target_url).netloc
            s_name = c_save_name.text_input("Nom sauvegarde", value=domain.split('.')[0], label_visibility="collapsed")

            # Sauvegarde
            if c_save_btn.button("Sauvegarder", use_container_width=True):
                max_pages_to_save = 100
                results_to_save = st.session_state.results[:max_pages_to_save]

                clean_results = []
                for r in results_to_save:
                    clean_results.append({
                        "url": r.get("url"),
                        "title": r.get("title", "")[:50],
                        "description": r.get("description", "")[:100],
                        "h1": r.get("h1", "")[:50],
                        "response_time": round(r.get("response_time", 0), 2),
                        "has_structured_data": r.get("has_structured_data", False),
                        "h2_count": r.get("h2_count", 0)
                    })

                compact_clusters = []
                for cluster in st.session_state.clusters:
                    compact_clusters.append({
                        "name": cluster["name"],
                        "count": cluster["count"],
                        "samples": []
                    })

                payload = {
                    "results": clean_results,
                    "clusters": compact_clusters,
                    "geo_infra": st.session_state.get('geo_infra', {}),
                    "geo_score": st.session_state.get('geo_score', 0),
                    "stats": {
                        "pages_crawled": st.session_state.crawl_stats.get('pages_crawled', 0),
                        "links_discovered": st.session_state.crawl_stats.get('links_discovered', 0),
                        "links_filtered": st.session_state.crawl_stats.get('links_filtered', 0),
                        "links_duplicate": st.session_state.crawl_stats.get('links_duplicate', 0),
                        "pages_skipped": st.session_state.crawl_stats.get('pages_skipped', 0),
                        "errors": st.session_state.crawl_stats.get('errors', 0),
                        "start_urls_count": st.session_state.crawl_stats.get('start_urls_count', 1)
                    },
                    "start_urls": st.session_state.get('start_urls', [st.session_state.target_url])[:5]
                }

                if len(st.session_state.results) > max_pages_to_save:
                    st.warning(f"Seules les {max_pages_to_save} premieres pages sur {len(st.session_state.results)} seront sauvegardees (limite Google Sheets)")

                db.save_audit(user_email, st.session_state.current_ws, st.session_state.target_url, s_name, payload)
                st.toast("Audit sauvegarde")

            # Construction du graphe
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
                    score_data = calculate_page_score(p)
                    if isinstance(score_data, tuple):
                        sc, grade, breakdown, recommendations = score_data
                    else:
                        sc = score_data
                        grade = 'N/A'
                        breakdown = {}
                        recommendations = []

                    if expert_on:
                        col = _score_color(sc)
                    else:
                        col = "#e2e8f0"

                    label = get_clean_label(p.get('title', ''), p['url'], domain)
                    if expert_on and isinstance(score_data, tuple):
                        label = f"{label}\\n[{grade}]"

                    tooltip_parts = []
                    if expert_on and isinstance(score_data, tuple):
                        tooltip_parts.append(f"Score AI-READABLE: {sc}/100 - Grade: {grade}")

                        missing = []
                        if not p.get('description'):
                            missing.append("Meta description manquante")
                        if not p.get('h1'):
                            missing.append("H1 manquant")
                        if not p.get('has_structured_data'):
                            missing.append("JSON-LD manquant")
                        if p.get('h2_count', 0) < 2:
                            missing.append("Peu de H2")

                        if missing:
                            tooltip_parts.append("\\n\\nElements manquants:\\n" + "\\n".join(f"- {m}" for m in missing))

                        if recommendations:
                            top_reco = recommendations[:2]
                            tooltip_parts.append("\\n\\nRecommandations:\\n" + "\\n".join(f"- {r}" for r in top_reco))

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

            render_interactive_graph(G, show_health=expert_on)

    # ========================== TAB 2 : METHODOLOGIE ==========================
    with tab2:
        render_methodologie()
