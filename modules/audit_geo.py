# =============================================================================
# AUDIT GEO - HOTARU DESIGN SYSTEM (V3 - REFONTE VISUELLE TOTALE)
# Zero icone. Typographie stricte. Esthetique finance/terminal.
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
# CONSTANTE API MISTRAL
# =============================================================================
# La cle API Mistral est geree via st.secrets["mistral"]["api_key"]
# Configuree dans ~/.streamlit/secrets.toml sous [mistral] api_key = "..."
MISTRAL_API_KEY_PATH = "mistral"  # Chemin dans st.secrets


# =============================================================================
# 0. DOUBLE VERIFICATION ACCESSIBILITE IA (FRONTEND + API)
# =============================================================================

def _parse_robots_txt(robots_content):
    """Analyse le robots.txt pour determiner si les crawlers IA sont bloques"""
    if not robots_content:
        return {"accessible": False, "details": "Fichier absent"}

    content_lower = robots_content.lower()
    ai_bots = ['gptbot', 'chatgpt-user', 'google-extended', 'claudebot', 'perplexitybot', 'applebot-extended']
    blocked_bots = []
    allowed_bots = []

    lines = content_lower.split('\n')
    current_agent = None
    for line in lines:
        line = line.strip()
        if line.startswith('user-agent:'):
            current_agent = line.split(':', 1)[1].strip()
        elif line.startswith('disallow:') and current_agent:
            path = line.split(':', 1)[1].strip()
            if path == '/':
                if current_agent == '*':
                    blocked_bots = ai_bots[:]
                    break
                for bot in ai_bots:
                    if bot in current_agent:
                        blocked_bots.append(bot)
        elif line.startswith('allow:') and current_agent:
            path = line.split(':', 1)[1].strip()
            if path == '/':
                for bot in ai_bots:
                    if bot in current_agent:
                        allowed_bots.append(bot)

    # Verifier aussi les balises "Disallow: /" globales (User-agent: *)
    is_globally_blocked = False
    current_agent = None
    for line in lines:
        line = line.strip()
        if line.startswith('user-agent:'):
            current_agent = line.split(':', 1)[1].strip()
        elif line.startswith('disallow:') and current_agent == '*':
            if line.split(':', 1)[1].strip() == '/':
                is_globally_blocked = True

    if is_globally_blocked and not allowed_bots:
        return {
            "accessible": False,
            "details": "Disallow: / global (tous les bots bloques)",
            "blocked_bots": ai_bots,
            "allowed_bots": []
        }

    if blocked_bots:
        return {
            "accessible": False,
            "details": f"Bots IA bloques: {', '.join(blocked_bots)}",
            "blocked_bots": blocked_bots,
            "allowed_bots": allowed_bots
        }

    return {
        "accessible": True,
        "details": "Aucun blocage detecte pour les crawlers IA",
        "blocked_bots": [],
        "allowed_bots": allowed_bots
    }


def _check_meta_robots(base_url):
    """Verifie les balises meta robots de la page d'accueil"""
    try:
        r = requests.get(base_url, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')

        meta_robots = soup.find('meta', attrs={'name': 'robots'})
        meta_content = meta_robots.get('content', '').lower() if meta_robots else ''

        noindex = 'noindex' in meta_content
        nofollow = 'nofollow' in meta_content

        # Verifier aussi les meta specifiques aux bots IA
        ai_meta_tags = {}
        for bot_name in ['googlebot', 'gptbot', 'claudebot']:
            tag = soup.find('meta', attrs={'name': bot_name})
            if tag:
                ai_meta_tags[bot_name] = tag.get('content', '')

        return {
            "noindex": noindex,
            "nofollow": nofollow,
            "meta_content": meta_content,
            "ai_meta_tags": ai_meta_tags,
            "indexable": not noindex
        }
    except Exception:
        return {
            "noindex": False,
            "nofollow": False,
            "meta_content": "",
            "ai_meta_tags": {},
            "indexable": True  # Par defaut, on suppose indexable si erreur
        }


def _detect_api_subdomain(base_url, crawl_results=None):
    """Detecte le sous-domaine API du site (via sniffer de liens et tentative directe)"""
    parsed = urlparse(base_url)
    domain = parsed.netloc.lower()

    # Retirer le www. pour obtenir le domaine nu
    base_domain = domain.replace('www.', '')

    # Candidats API classiques
    api_candidates = [
        f"api.{base_domain}",
        f"backend.{base_domain}",
        f"data.{base_domain}",
        f"rest.{base_domain}",
        f"app.{base_domain}",
    ]

    # Sniffer: chercher des references API dans les pages crawlees
    sniffed_apis = set()
    if crawl_results:
        for page in crawl_results:
            html = page.get('html_content', '')
            if html:
                # Chercher des patterns API dans le code source
                api_patterns = re.findall(
                    r'https?://([a-zA-Z0-9\-]+\.' + re.escape(base_domain) + r')[/"\'\s]',
                    html
                )
                for match in api_patterns:
                    subdomain = match.lower()
                    if subdomain != domain and subdomain != f"www.{base_domain}":
                        sniffed_apis.add(subdomain)

                # Chercher aussi les fetch/axios/XMLHttpRequest vers des sous-domaines
                fetch_patterns = re.findall(
                    r'(?:fetch|axios|api_url|apiUrl|API_BASE|baseURL|endpoint)[^"\']*["\']https?://([^/"\']+)',
                    html, re.IGNORECASE
                )
                for match in fetch_patterns:
                    if base_domain in match.lower():
                        sniffed_apis.add(match.lower())

    # Combiner: sniffed en priorite, puis candidats classiques
    all_candidates = list(sniffed_apis) + [c for c in api_candidates if c not in sniffed_apis]

    # Tester chaque candidat
    for candidate in all_candidates:
        try:
            test_url = f"https://{candidate}"
            r = requests.head(test_url, timeout=3, allow_redirects=True)
            if r.status_code < 500:
                return {
                    "detected": True,
                    "subdomain": candidate,
                    "url": test_url,
                    "source": "sniffer" if candidate in sniffed_apis else "deduction"
                }
        except Exception:
            continue

    return {"detected": False, "subdomain": None, "url": None, "source": None}


def check_ai_accessibility(base_url, crawl_results=None):
    """
    Double verification de l'accessibilite IA :
    1. Site Principal (Frontend) : robots.txt + balises meta
    2. API Backend (si detectee) : robots.txt de l'API
    Retourne un dictionnaire complet pour le rapport GEO.
    """
    result = {
        "domain": urlparse(base_url).netloc,
        "frontend": {},
        "api": {},
        "summary": {}
    }

    # === 1. VERIFICATION FRONTEND ===
    # Robots.txt du site principal
    try:
        robots_url = f"{base_url.rstrip('/')}/robots.txt"
        r = requests.get(robots_url, timeout=5)
        if r.status_code == 200:
            robots_content = r.text
            robots_found = True
        else:
            robots_content = ""
            robots_found = False
    except Exception:
        robots_content = ""
        robots_found = False

    robots_analysis = _parse_robots_txt(robots_content)
    meta_analysis = _check_meta_robots(base_url)

    # Determiner le statut global du frontend
    frontend_open = robots_analysis["accessible"] and meta_analysis["indexable"]

    result["frontend"] = {
        "robots_found": robots_found,
        "robots_analysis": robots_analysis,
        "meta_analysis": meta_analysis,
        "status": "OUVERT" if frontend_open else "FERME",
        "robots_content": robots_content[:2000] if robots_content else ""
    }

    # === 2. VERIFICATION API BACKEND ===
    api_info = _detect_api_subdomain(base_url, crawl_results)

    if api_info["detected"]:
        # Verifier le robots.txt de l'API
        try:
            api_robots_url = f"{api_info['url'].rstrip('/')}/robots.txt"
            r = requests.get(api_robots_url, timeout=5)
            if r.status_code == 200:
                api_robots_content = r.text
                api_robots_found = True
            else:
                api_robots_content = ""
                api_robots_found = False
        except Exception:
            api_robots_content = ""
            api_robots_found = False

        api_robots_analysis = _parse_robots_txt(api_robots_content)
        api_open = api_robots_analysis["accessible"]

        result["api"] = {
            "detected": True,
            "subdomain": api_info["subdomain"],
            "source": api_info["source"],
            "robots_found": api_robots_found,
            "robots_analysis": api_robots_analysis,
            "status": "OUVERT" if api_open else "FERME",
            "robots_content": api_robots_content[:2000] if api_robots_content else ""
        }
    else:
        result["api"] = {
            "detected": False,
            "subdomain": None,
            "source": None,
            "robots_found": False,
            "robots_analysis": {},
            "status": "NON DETECTEE"
        }

    # === RESUME ===
    result["summary"] = {
        "site_accessible": result["frontend"]["status"],
        "api_detected": result["api"]["detected"],
        "api_accessible": result["api"]["status"],
    }

    return result


# =============================================================================
# 0.5 RAPPORT GEO & DATA VIA MISTRAL
# =============================================================================

def generate_geo_report(domain, accessibility_data):
    """
    Utilise l'API Mistral pour generer la conclusion de l'audit GEO.
    Envoie le prompt systeme d'expert GEO avec les donnees d'accessibilite.
    """
    try:
        api_key = st.secrets[MISTRAL_API_KEY_PATH]["api_key"]
    except Exception:
        return "Cle API Mistral manquante. Configurez st.secrets['mistral']['api_key'] dans ~/.streamlit/secrets.toml"

    site_status = accessibility_data.get("frontend", {}).get("status", "INCONNU")
    api_detected = "OUI" if accessibility_data.get("api", {}).get("detected", False) else "NON"
    api_status = accessibility_data.get("api", {}).get("status", "NON DETECTEE")

    system_prompt = (
        "Agis comme un expert international en GEO (Generative Engine Optimization) "
        "et en strategie de Donnees. Analyse la situation suivante pour le client "
        f"[{domain}] :\n\n"
        f"Accessibilite Site Web : [{site_status} via robots.txt]\n"
        f"API Detectee : [{api_detected}]\n"
        f"Accessibilite API : [{api_status}]\n\n"
        "Redige un resume strategique court (3-4 phrases) pour le Directeur Marketing et le DSI. "
        "Adopte le ton suivant :\n\n"
        "Si tout est OUVERT : \"Excellent pour votre visibilite IA (GEO). Vos contenus seront "
        "facilement repris par les LLMs. Attention cependant : votre API est aussi en libre acces, "
        "ce qui facilite le clonage de vos donnees par des concurrents.\"\n\n"
        "Si Site FERME mais API OUVERTE : \"Situation paradoxale. Vous bloquez les IA sur votre "
        "vitrine, mais votre API laisse fuiter toutes vos donnees structurees. Vous perdez en "
        "visibilite tout en etant vulnerable.\"\n\n"
        "Si tout est FERME : \"Vous etes invisible pour les IA. C'est securise, mais vous "
        "disparaissez des reponses de ChatGPT/Gemini.\"\n\n"
        "Si Site OUVERT et API NON DETECTEE : \"Bonne configuration pour le SEO/GEO classique.\"\n\n"
        "Sois professionnel, concis et oriente business."
    )

    user_prompt = (
        f"Domaine audite : {domain}\n"
        f"Accessibilite Site Web : {site_status}\n"
        f"API Detectee : {api_detected}\n"
        f"Accessibilite API : {api_status}\n\n"
        "Genere le rapport strategique GEO & Data."
    )

    try:
        report = _call_mistral(api_key, system_prompt, user_prompt, max_tokens=800)
        return report
    except Exception as e:
        return f"Erreur lors de la generation du rapport Mistral : {e}"


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


def _call_mistral(api_key, system_prompt, user_prompt, max_tokens=2500):
    """Appel generique a l'API Mistral"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens
    }
    response = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def generate_robots_optimization(file_content, site_url, found):
    """Genere le code robots.txt optimise + analyse comparative via Mistral"""
    try:
        api_key = st.secrets["mistral"]["api_key"]
    except Exception:
        return None, "Cle API Mistral manquante dans les secrets Streamlit."

    current = file_content if found else "Le fichier robots.txt n'existe pas ou est vide."

    code_prompt = f"""Tu es un expert SEO specialise en securite et AI-Readability.
Voici le robots.txt actuel du site {site_url} :

{current}

Genere une version "Forteresse AI-Ready" du robots.txt pour un site institutionnel.
Le fichier doit :
1. BLOQUER les dossiers sensibles : /wp-admin/, /wp-login.php, /xmlrpc.php, /wp-includes/, /wp-content/plugins/, /cgi-bin/, /admin/, les fichiers *.php inutiles
2. BLOQUER les ressources qui gaspillent le crawl budget : /feed/, /trackback/, /?s=, /wp-json/, /wp-content/uploads/*.pdf
3. AUTORISER EXPLICITEMENT chaque agent IA avec un bloc dedie :
   - User-agent: GPTBot (OpenAI)
   - User-agent: ChatGPT-User (OpenAI browse)
   - User-agent: Google-Extended (Gemini)
   - User-agent: ClaudeBot (Anthropic)
   - User-agent: PerplexityBot
   - User-agent: Bingbot
   - User-agent: Applebot-Extended
   Chacun avec Allow: / et les Disallow necessaires (/wp-admin, etc.)
4. Inclure la directive Sitemap en bas
5. Ajouter des commentaires clairs par section

Reponds UNIQUEMENT avec le contenu du fichier robots.txt. Aucune explication autour."""

    analysis_prompt = f"""Tu es un consultant SEO senior qui presente un audit a un client non-technique.

Voici le robots.txt ACTUEL du site {site_url} :

{current}

Redige une analyse comparative concise et professionnelle (ton d'audit financier) qui explique :

**Securite**
Analyse les failles de la version actuelle. Les dossiers sensibles (/wp-admin, /xmlrpc.php, etc.) sont-ils proteges ?
La version actuelle est-elle une "passoire" qui expose des points d'entree aux attaques ?

**Crawl Budget**
Le fichier actuel gaspille-t-il les ressources en laissant les bots crawler des pages inutiles (feeds, trackbacks, fichiers PHP internes) ?
Quel est l'impact sur la performance d'indexation ?

**Signal AI-Ready**
Les agents IA (GPTBot, ClaudeBot, Google-Extended, PerplexityBot) sont-ils explicitement autorises ?
Sans signal explicite, le site est-il invisible pour les moteurs de reponse IA ?
Pourquoi nommer chaque bot individuellement est critique en 2025-2026 ?

**Verdict**
Resume en une phrase l'ecart entre la version actuelle et la version optimisee.

Ecris en francais. Utilise des titres en Markdown (**Gras**). Ton professionnel, factuel, zero emoji."""

    try:
        optimized_code = _call_mistral(
            api_key,
            "Tu es un expert SEO. Tu generes uniquement du code robots.txt, sans explications.",
            code_prompt,
            max_tokens=1500
        )
        analysis = _call_mistral(
            api_key,
            "Tu es un consultant SEO senior. Tu rediges des analyses d'audit professionnelles en francais, ton factuel, zero emoji.",
            analysis_prompt,
            max_tokens=1500
        )
        return optimized_code, analysis
    except Exception as e:
        return None, f"Erreur API Mistral : {e}"


def generate_llms_optimization(file_content, site_url, found):
    """Genere le fichier llms.txt Gold Standard via Mistral"""
    try:
        api_key = st.secrets["mistral"]["api_key"]
    except Exception:
        return "Cle API Mistral manquante dans les secrets Streamlit."

    current = file_content if found else "Le fichier llms.txt n'existe pas."

    prompt = f"""Tu es un expert en AI-Readability et standards LLM. Tu dois generer un fichier llms.txt "Gold Standard".

Voici le fichier llms.txt actuel du site {site_url} :

{current}

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

    try:
        return _call_mistral(
            api_key,
            "Tu es un expert en optimisation de sites web pour les agents IA. Tu generes uniquement du code/config, jamais d'explications.",
            prompt,
            max_tokens=2000
        )
    except Exception as e:
        return f"Erreur API Mistral : {e}"


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
        return "#FFA500"
    else:
        return "#FF4B4B"


def _score_label(score):
    """Retourne le libelle selon l'echelle severe"""
    if score >= 95:
        return "OPTIMISE"
    elif score >= 50:
        return "NON OPTIMISE"
    else:
        return "CRITIQUE"


def _grade_color(grade):
    """Couleur de badge par grade"""
    if grade in ('A+', 'A'):
        return "#10b981"
    elif grade in ('B', 'C'):
        return "#FFA500"
    else:
        return "#FF4B4B"


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
# 3. JOURNAUX (3 VUES) - DESIGN TERMINAL / FINANCE
# =============================================================================

def render_journal_crawled(results):
    """Vue A : Journal des pages crawlees, classees par categories"""
    categories = categorize_urls(results)

    st.markdown(
        f'<p style="font-size:0.75rem;font-weight:600;color:#94a3b8;margin-bottom:20px;">'
        f'{len(results)} pages analysees  &mdash;  {len(categories)} categories detectees</p>',
        unsafe_allow_html=True
    )

    # En-tete de tableau
    st.markdown(
        '<div style="display:flex;align-items:center;padding:10px 0;border-bottom:2px solid #0f172a;margin-bottom:4px;">'
        '<span style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#0f172a;width:50px;">GRADE</span>'
        '<span style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#0f172a;flex:1;">PAGE</span>'
        '<span style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#0f172a;width:300px;text-align:right;">PATH</span>'
        '</div>',
        unsafe_allow_html=True
    )

    for cat_name, pages in categories.items():
        with st.expander(f"{cat_name}  ({len(pages)})", expanded=False):
            for p in pages:
                score_data = calculate_page_score(p)
                if isinstance(score_data, tuple):
                    sc, grade, _, _ = score_data
                else:
                    sc, grade = score_data, 'N/A'

                col = _grade_color(grade)
                title = p.get('title', 'Sans titre')
                url = p.get('url', '')
                path = urlparse(url).path or '/'

                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f1f5f9;">'
                    f'<span style="background:{col};color:#fff;padding:2px 8px;font-size:0.65rem;font-weight:800;'
                    f'min-width:32px;text-align:center;letter-spacing:0.05em;">{grade}</span>'
                    f'<a href="{url}" target="_blank" style="font-size:0.85rem;font-weight:600;color:#0f172a;'
                    f'text-decoration:none;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"'
                    f' onmouseover="this.style.borderBottom=\'1px solid #0f172a\'"'
                    f' onmouseout="this.style.borderBottom=\'none\'">{title}</a>'
                    f'<span style="font-size:0.7rem;color:#94a3b8;font-family:\'Courier New\',monospace;'
                    f'max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:right;">{path}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )


def render_journal_filtered(filtered_log):
    """Vue B : Journal des liens filtres"""
    if not filtered_log:
        st.markdown(
            '<p style="font-size:0.85rem;color:#94a3b8;font-style:italic;">Aucun lien filtre lors de ce crawl.</p>',
            unsafe_allow_html=True
        )
        return

    st.markdown(
        f'<p style="font-size:0.75rem;font-weight:600;color:#94a3b8;margin-bottom:20px;">'
        f'{len(filtered_log)} liens exclus par les filtres anti-bruit</p>',
        unsafe_allow_html=True
    )

    # En-tete
    st.markdown(
        '<div style="display:flex;align-items:center;padding:10px 0;border-bottom:2px solid #0f172a;margin-bottom:4px;">'
        '<span style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#0f172a;width:120px;">MOTIF</span>'
        '<span style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#0f172a;flex:1;">URL</span>'
        '</div>',
        unsafe_allow_html=True
    )

    by_pattern = defaultdict(list)
    for url, pattern in filtered_log:
        by_pattern[pattern].append(url)

    for pattern, urls in sorted(by_pattern.items(), key=lambda x: -len(x[1])):
        with st.expander(f"{pattern}  ({len(urls)} liens)", expanded=False):
            for url in urls[:100]:
                st.markdown(
                    f'<div style="padding:5px 0;border-bottom:1px solid #f8fafc;">'
                    f'<span style="font-size:0.75rem;font-family:\'Courier New\',monospace;color:#64748b;">{url}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            if len(urls) > 100:
                st.markdown(
                    f'<p style="font-size:0.75rem;font-style:italic;color:#94a3b8;margin-top:8px;">'
                    f'... et {len(urls) - 100} autres</p>',
                    unsafe_allow_html=True
                )


def render_journal_duplicates(duplicate_log):
    """Vue C : Journal des doublons"""
    if not duplicate_log:
        st.markdown(
            '<p style="font-size:0.85rem;color:#94a3b8;font-style:italic;">Aucun doublon detecte lors de ce crawl.</p>',
            unsafe_allow_html=True
        )
        return

    counts = Counter(duplicate_log)
    sorted_dupes = sorted(counts.items(), key=lambda x: -x[1])

    st.markdown(
        f'<p style="font-size:0.75rem;font-weight:600;color:#94a3b8;margin-bottom:20px;">'
        f'{len(duplicate_log)} doublons detectes  &mdash;  {len(counts)} URLs uniques</p>',
        unsafe_allow_html=True
    )

    # En-tete
    st.markdown(
        '<div style="display:flex;align-items:center;padding:10px 0;border-bottom:2px solid #0f172a;margin-bottom:4px;">'
        '<span style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#0f172a;width:60px;">OCCUR.</span>'
        '<span style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#0f172a;flex:1;">PATH</span>'
        '</div>',
        unsafe_allow_html=True
    )

    for url, count in sorted_dupes[:200]:
        path = urlparse(url).path or '/'
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;padding:6px 0;border-bottom:1px solid #f8fafc;">'
            f'<span style="background:#0f172a;color:#fff;padding:2px 10px;font-size:0.65rem;font-weight:800;'
            f'min-width:40px;text-align:center;">{count}x</span>'
            f'<span style="font-size:0.8rem;font-family:\'Courier New\',monospace;color:#64748b;">{path}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    if len(sorted_dupes) > 200:
        st.markdown(
            f'<p style="font-size:0.75rem;font-style:italic;color:#94a3b8;margin-top:8px;">'
            f'... et {len(sorted_dupes) - 200} autres URLs</p>',
            unsafe_allow_html=True
        )


# =============================================================================
# 3.5. RAPPORT D'AUDIT GEO & DATA - ENCADRE VISIBLE
# =============================================================================

def render_ai_accessibility_panel(accessibility_data):
    """Affiche le panneau de double verification accessibilite IA"""
    if not accessibility_data:
        return

    frontend = accessibility_data.get("frontend", {})
    api = accessibility_data.get("api", {})

    # Statut Frontend
    fe_status = frontend.get("status", "INCONNU")
    fe_color = "#10b981" if fe_status == "OUVERT" else "#FF4B4B"

    # Statut API
    api_detected = api.get("detected", False)
    api_status = api.get("status", "NON DETECTEE")
    if api_status == "OUVERT":
        api_color = "#FFA500"  # Orange = ouvert mais risque
    elif api_status == "FERME":
        api_color = "#10b981"
    else:
        api_color = "#94a3b8"  # Gris = non detectee

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f'<div style="padding:24px;border:1px solid #e2e8f0;border-left:4px solid {fe_color};">'
            f'<div style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;'
            f'color:#94a3b8;margin-bottom:12px;">SITE PRINCIPAL (FRONTEND)</div>'
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
            f'<span style="display:inline-block;padding:4px 14px;font-size:0.65rem;font-weight:800;'
            f'letter-spacing:0.1em;background:{fe_color};color:#fff;">{fe_status}</span>'
            f'<span style="font-size:0.75rem;color:#64748b;">via robots.txt</span>'
            f'</div>'
            f'<div style="font-size:0.8rem;color:#64748b;line-height:1.5;">'
            f'{frontend.get("robots_analysis", {}).get("details", "Non analyse")}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Details meta robots
        meta = frontend.get("meta_analysis", {})
        if meta.get("noindex") or meta.get("nofollow") or meta.get("ai_meta_tags"):
            details = []
            if meta.get("noindex"):
                details.append("noindex detecte")
            if meta.get("nofollow"):
                details.append("nofollow detecte")
            for bot, content in meta.get("ai_meta_tags", {}).items():
                details.append(f"meta {bot}: {content}")
            if details:
                st.markdown(
                    f'<div style="padding:12px;background:#fafafa;border:1px solid #f1f5f9;margin-top:8px;">'
                    f'<div style="font-size:0.7rem;font-weight:700;color:#94a3b8;margin-bottom:6px;">BALISES META</div>'
                    f'<div style="font-size:0.75rem;color:#64748b;">{" | ".join(details)}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    with col2:
        if api_detected:
            st.markdown(
                f'<div style="padding:24px;border:1px solid #e2e8f0;border-left:4px solid {api_color};">'
                f'<div style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;'
                f'color:#94a3b8;margin-bottom:12px;">API BACKEND</div>'
                f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
                f'<span style="display:inline-block;padding:4px 14px;font-size:0.65rem;font-weight:800;'
                f'letter-spacing:0.1em;background:{api_color};color:#fff;">{api_status}</span>'
                f'<span style="font-size:0.75rem;color:#64748b;">via robots.txt API</span>'
                f'</div>'
                f'<div style="font-size:0.8rem;color:#64748b;line-height:1.5;">'
                f'Sous-domaine : <strong>{api.get("subdomain", "")}</strong><br>'
                f'Detection : {api.get("source", "")}<br>'
                f'{api.get("robots_analysis", {}).get("details", "")}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div style="padding:24px;border:1px solid #e2e8f0;border-left:4px solid {api_color};">'
                f'<div style="font-size:0.6rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;'
                f'color:#94a3b8;margin-bottom:12px;">API BACKEND</div>'
                f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
                f'<span style="display:inline-block;padding:4px 14px;font-size:0.65rem;font-weight:800;'
                f'letter-spacing:0.1em;background:#94a3b8;color:#fff;">NON DETECTEE</span>'
                f'</div>'
                f'<div style="font-size:0.8rem;color:#94a3b8;font-style:italic;">Aucun sous-domaine API identifie '
                f'(api.*, backend.*, data.*)</div>'
                f'</div>',
                unsafe_allow_html=True
            )


def render_geo_report(base_url, accessibility_data):
    """Affiche le rapport GEO & Data Mistral dans un encadre bien visible"""
    if not base_url or not accessibility_data:
        return

    domain = urlparse(base_url).netloc

    st.markdown(
        '<p class="section-title">RAPPORT D\'AUDIT GEO & DATA</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="font-size:0.8rem;color:#94a3b8;font-style:italic;margin-bottom:24px;">'
        'Double verification accessibilite IA (Frontend + API) et conclusion strategique Mistral</p>',
        unsafe_allow_html=True
    )

    # Panel d'accessibilite
    render_ai_accessibility_panel(accessibility_data)

    st.markdown("<br>", unsafe_allow_html=True)

    # Bouton pour generer le rapport Mistral
    if st.button("GENERER LE RAPPORT STRATEGIQUE MISTRAL", key="btn_geo_report", use_container_width=True):
        with st.spinner("Mistral analyse l'accessibilite IA et genere le rapport strategique..."):
            report = generate_geo_report(domain, accessibility_data)
            st.session_state["geo_ai_report"] = report

    # Affichage du rapport dans un encadre visible
    if "geo_ai_report" in st.session_state:
        st.markdown("<br>", unsafe_allow_html=True)

        # Resume des statuts en haut du rapport
        fe_status = accessibility_data.get("frontend", {}).get("status", "INCONNU")
        api_detected = accessibility_data.get("api", {}).get("detected", False)
        api_status = accessibility_data.get("api", {}).get("status", "NON DETECTEE")

        st.markdown(
            f'<div style="padding:32px;border:2px solid #0f172a;background:#fafafa;margin-top:8px;">'
            f'<div style="font-size:0.65rem;font-weight:800;letter-spacing:0.25em;text-transform:uppercase;'
            f'color:#0f172a;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid #e2e8f0;">'
            f'RAPPORT D\'AUDIT GEO & DATA</div>'
            f'<div style="display:flex;gap:24px;margin-bottom:20px;">'
            f'<span style="font-size:0.7rem;color:#64748b;">Site : <strong>{fe_status}</strong></span>'
            f'<span style="font-size:0.7rem;color:#64748b;">API : <strong>{"OUI" if api_detected else "NON"}</strong></span>'
            f'<span style="font-size:0.7rem;color:#64748b;">Acces API : <strong>{api_status}</strong></span>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown(st.session_state["geo_ai_report"])
        st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# 4. OPTIMISATION MISTRAL - DESIGN PROFESSIONNEL
# =============================================================================

def render_mistral_optimization(base_url):
    """Module d'optimisation IA avec comparatif existant vs proposition Mistral"""
    if not base_url:
        return

    st.markdown(
        '<p class="section-title">05 / OPTIMISATION MISTRAL AI</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="font-size:0.8rem;color:#94a3b8;font-style:italic;margin-bottom:24px;">'
        'Generation et analyse comparative via Mistral AI &mdash; robots.txt & llms.txt</p>',
        unsafe_allow_html=True
    )

    tab_robots, tab_llms = st.tabs(["ROBOTS.TXT", "LLMS.TXT"])

    # ==================== ROBOTS.TXT ====================
    with tab_robots:
        content, found = fetch_file_content(base_url, "robots.txt")

        # Status
        if found:
            st.markdown(
                '<span style="display:inline-block;padding:4px 14px;font-size:0.6rem;font-weight:800;'
                'letter-spacing:0.15em;text-transform:uppercase;background:#0f172a;color:#fff;border:1px solid #0f172a;">'
                'DETECTE</span>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<span style="display:inline-block;padding:4px 14px;font-size:0.6rem;font-weight:800;'
                'letter-spacing:0.15em;text-transform:uppercase;background:#fff;color:#FF4B4B;border:1px solid #FF4B4B;">'
                'ABSENT</span>',
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("ANALYSER ET OPTIMISER", key="btn_robots", use_container_width=True):
            with st.spinner("Mistral genere le code optimise et l'analyse comparative..."):
                optimized_code, analysis = generate_robots_optimization(content, base_url, found)
                if optimized_code:
                    st.session_state["mistral_robots_code"] = optimized_code
                st.session_state["mistral_robots_analysis"] = analysis

        st.markdown("<br>", unsafe_allow_html=True)

        # Zone 1 : Comparateur de code
        st.markdown(
            '<p style="font-size:0.6rem;font-weight:800;letter-spacing:0.25em;text-transform:uppercase;'
            'color:#94a3b8;margin-bottom:12px;">COMPARATEUR DE CODE</p>',
            unsafe_allow_html=True
        )

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown(
                '<p style="font-size:0.75rem;font-weight:700;color:#0f172a;margin-bottom:8px;">Code Actuel</p>',
                unsafe_allow_html=True
            )
            st.code(content if found else "# robots.txt inexistant", language="text")

        with col_right:
            st.markdown(
                '<p style="font-size:0.75rem;font-weight:700;color:#0f172a;margin-bottom:8px;">'
                'Proposition Optimisee <span style="font-weight:400;font-style:italic;color:#94a3b8;">(AI-Ready)</span></p>',
                unsafe_allow_html=True
            )
            if "mistral_robots_code" in st.session_state:
                st.code(st.session_state["mistral_robots_code"], language="text")
            else:
                st.markdown(
                    '<p style="font-size:0.8rem;color:#94a3b8;font-style:italic;padding:16px;border:1px solid #f1f5f9;">'
                    'Cliquez sur le bouton ci-dessus pour generer la proposition.</p>',
                    unsafe_allow_html=True
                )

        # Zone 2 : Analyse strategique
        if "mistral_robots_analysis" in st.session_state:
            st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
            st.markdown(
                '<p style="font-size:0.6rem;font-weight:800;letter-spacing:0.25em;text-transform:uppercase;'
                'color:#94a3b8;margin-bottom:16px;">ANALYSE STRATEGIQUE</p>',
                unsafe_allow_html=True
            )
            st.markdown(
                '<div style="padding:24px;border:1px solid #e2e8f0;background:#fafafa;">',
                unsafe_allow_html=True
            )
            st.markdown(st.session_state["mistral_robots_analysis"])
            st.markdown('</div>', unsafe_allow_html=True)

    # ==================== LLMS.TXT ====================
    with tab_llms:
        content, found = fetch_file_content(base_url, "llms.txt")

        if found:
            st.markdown(
                '<span style="display:inline-block;padding:4px 14px;font-size:0.6rem;font-weight:800;'
                'letter-spacing:0.15em;text-transform:uppercase;background:#0f172a;color:#fff;border:1px solid #0f172a;">'
                'DETECTE</span>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<span style="display:inline-block;padding:4px 14px;font-size:0.6rem;font-weight:800;'
                'letter-spacing:0.15em;text-transform:uppercase;background:#fff;color:#FF4B4B;border:1px solid #FF4B4B;">'
                'ABSENT</span>',
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("GENERER PROPOSITION OPTIMISEE", key="btn_llms", use_container_width=True):
            with st.spinner("Mistral genere le llms.txt Gold Standard..."):
                optimized = generate_llms_optimization(content, base_url, found)
                st.session_state["mistral_llms_code"] = optimized

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            '<p style="font-size:0.6rem;font-weight:800;letter-spacing:0.25em;text-transform:uppercase;'
            'color:#94a3b8;margin-bottom:12px;">COMPARATEUR DE CODE</p>',
            unsafe_allow_html=True
        )

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown(
                '<p style="font-size:0.75rem;font-weight:700;color:#0f172a;margin-bottom:8px;">Code Actuel</p>',
                unsafe_allow_html=True
            )
            st.code(content if found else "# llms.txt inexistant", language="text")

        with col_right:
            st.markdown(
                '<p style="font-size:0.75rem;font-weight:700;color:#0f172a;margin-bottom:8px;">'
                'Proposition Optimisee <span style="font-weight:400;font-style:italic;color:#94a3b8;">(Gold Standard)</span></p>',
                unsafe_allow_html=True
            )
            if "mistral_llms_code" in st.session_state:
                st.code(st.session_state["mistral_llms_code"], language="text")
            else:
                st.markdown(
                    '<p style="font-size:0.8rem;color:#94a3b8;font-style:italic;padding:16px;border:1px solid #f1f5f9;">'
                    'Cliquez sur le bouton ci-dessus pour generer la proposition.</p>',
                    unsafe_allow_html=True
                )


# =============================================================================
# 5. RENDU DU GRAPHE
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
                <div style="width: 12px; height: 12px; background: #FFA500; margin-right: 10px;"></div>
                <span style="font-size: 0.8rem; font-weight: 600;">50-94  Non optimise</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 12px; height: 12px; background: #FF4B4B; margin-right: 10px;"></div>
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
        fullscreenBtn.innerHTML = 'PLEIN ECRAN';
        fullscreenBtn.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;padding:10px 24px;background:#0f172a;color:white;border:none;font-family:Inter,sans-serif;font-size:0.65rem;font-weight:800;letter-spacing:0.15em;text-transform:uppercase;cursor:pointer;';
        fullscreenBtn.onclick = toggleFullscreen;
        document.body.appendChild(fullscreenBtn);
    </script>
    {legend_html}
    """

    components.html(html.replace("</body>", custom_code + "</body>"), height=900)


# =============================================================================
# 6. ONGLET METHODOLOGIE
# =============================================================================

def render_methodologie():
    """Methodologie Hotaru"""

    st.markdown("""
    <style>
        .methodo-container { max-width: 900px; margin: auto; padding: 20px; }
        .methodo-title { font-size: 3rem; font-weight: 900; letter-spacing: -0.04em; margin-bottom: 0.2rem; color: #000; border-bottom: 2px solid #000; padding-bottom: 8px; }
        .methodo-subtitle { font-size: 1.1rem; color: #94a3b8; margin-bottom: 4rem; font-weight: 400; text-transform: uppercase; letter-spacing: 0.1em; }
        .methodo-header { font-size: 1.1rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.15em; color: #000; margin-bottom: 2rem; border-bottom: 2px solid #000; padding-bottom: 8px; width: fit-content; }
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
            <div><span class="methodo-dot" style="background:#FFA500;"></span><span style="font-size:0.9rem; font-weight:600;">NON OPTIMISE</span></div>
            <div><span class="methodo-dot" style="background:#FF4B4B;"></span><span style="font-size:0.9rem; font-weight:600;">CRITICAL</span></div>
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
# 7. INTERFACE PRINCIPALE - DESIGN HOTARU STRICT
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

        # =================================================================
        # ZONE DE SCAN
        # =================================================================
        st.markdown(
            '<p class="section-title">01 / NOUVELLE ANALYSE</p>',
            unsafe_allow_html=True
        )

        st.markdown('<div class="zen-card">', unsafe_allow_html=True)

        c1, c2 = st.columns([3, 1])

        url_input = c1.text_area(
            "URLs a analyser (une par ligne)",
            placeholder="https://example.com/\nhttps://example.com/section1",
            height=100,
            label_visibility="collapsed"
        )

        default_ws = "" if selected_ws == "+ Creer Nouveau" else selected_ws
        ws_in = c2.text_input("Nom du Projet", value=default_ws, label_visibility="collapsed",
                              placeholder="Nom du projet")

        limit_in = st.select_slider(
            "Pages",
            options=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
            value=100
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("LANCER L'ANALYSE", use_container_width=True, type="primary"):
            if url_input:
                urls = [line.strip() for line in url_input.strip().split('\n') if line.strip()]

                if not urls:
                    st.markdown(
                        '<p style="color:#FF4B4B;font-weight:700;font-size:0.85rem;">Veuillez entrer au moins une URL.</p>',
                        unsafe_allow_html=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    return

                domains = [urlparse(url).netloc for url in urls]
                if len(set(domains)) > 1:
                    st.markdown(
                        f'<p style="color:#FF4B4B;font-weight:700;font-size:0.85rem;">'
                        f'Toutes les URLs doivent etre du meme domaine. Trouve : {", ".join(set(domains))}</p>',
                        unsafe_allow_html=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
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

                # Double verification accessibilite IA (Frontend + API)
                bar.progress(0.95, "Verification accessibilite IA (Frontend + API)...")
                ai_access = check_ai_accessibility(base_url, res)

                st.session_state.update({
                    "results": res,
                    "clusters": scr.get_pattern_summary(),
                    "target_url": base_url,
                    "start_urls": urls,
                    "current_ws": ws_in if ws_in else "Non classe",
                    "crawl_stats": stats.get('stats', {}),
                    "filtered_log": stats.get('filtered_log', []),
                    "duplicate_log": stats.get('duplicate_log', []),
                    "ai_accessibility": ai_access
                })
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # =================================================================
        # ARCHIVES
        # =================================================================
        if filtered_audits:
            st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
            st.markdown(
                '<p class="section-title">ARCHIVES</p>',
                unsafe_allow_html=True
            )

            audit_labels = {f"{a.get('nom_site') or 'Audit'} ({a.get('date')})": a for a in filtered_audits}

            col1, col2 = st.columns([3, 1])
            choice = col1.selectbox("Charger un audit", list(audit_labels.keys()), label_visibility="collapsed")

            if col2.button("VISUALISER", use_container_width=True, type="primary"):
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
                    "duplicate_log": data.get('duplicate_log', []),
                    "ai_accessibility": data.get('ai_accessibility', {})
                })
                st.rerun()

        # =================================================================
        # RESULTATS
        # =================================================================
        if "results" not in st.session_state:
            return

        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

        # ========== 02 / SCORE AI-READABLE ==========
        st.markdown(
            '<p class="section-title">02 / SCORE AI-READABLE</p>',
            unsafe_allow_html=True
        )

        g_score = st.session_state.get("geo_score", 0)
        score_color = _score_color(g_score)
        score_label = _score_label(g_score)

        st.markdown(
            f'<div style="display:flex;align-items:flex-end;gap:16px;margin-bottom:12px;">'
            f'<span style="font-size:5rem;font-weight:900;color:{score_color};line-height:1;letter-spacing:-0.04em;">{g_score}</span>'
            f'<span style="font-size:1.2rem;font-weight:700;color:#94a3b8;margin-bottom:10px;">/100</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            f'<span style="display:inline-block;padding:6px 20px;font-size:0.6rem;font-weight:800;'
            f'letter-spacing:0.2em;text-transform:uppercase;background:{score_color};color:#fff;'
            f'border:1px solid {score_color};">{score_label}</span>',
            unsafe_allow_html=True
        )

        st.markdown("<br><br>", unsafe_allow_html=True)

        # ========== INFRASTRUCTURE ==========
        st.markdown(
            '<p class="section-title">03 / INFRASTRUCTURE IA</p>',
            unsafe_allow_html=True
        )

        if st.session_state.get("geo_infra"):
            cols = st.columns(4)
            for i, (name, d) in enumerate(st.session_state.geo_infra.items()):
                with cols[i]:
                    if d['status']:
                        status_html = (
                            '<span style="font-size:0.7rem;font-weight:800;color:#10b981;'
                            'letter-spacing:0.1em;">PRESENT</span>'
                        )
                    else:
                        status_html = (
                            '<span style="font-size:0.7rem;font-weight:800;color:#FF4B4B;'
                            'letter-spacing:0.1em;">ABSENT</span>'
                        )

                    st.markdown(
                        f'<div style="padding:20px;border:1px solid #e2e8f0;border-left:3px solid '
                        f'{"#10b981" if d["status"] else "#FF4B4B"};">'
                        f'<div style="font-weight:800;font-size:0.85rem;margin-bottom:8px;">{name}</div>'
                        f'{status_html}'
                        f'<div style="font-size:0.75rem;color:#94a3b8;margin-top:8px;line-height:1.4;'
                        f'font-style:italic;">{d["meta"]["desc"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

        # ========== 04 / STATISTIQUES DU CRAWL ==========
        if "crawl_stats" in st.session_state and st.session_state.crawl_stats:
            st.markdown(
                '<p class="section-title">04 / STATISTIQUES DU CRAWL</p>',
                unsafe_allow_html=True
            )

            stats = st.session_state.crawl_stats

            # Points d'entree multiples
            if "start_urls" in st.session_state and len(st.session_state.start_urls) > 1:
                with st.expander(f"Points d'entree : {len(st.session_state.start_urls)}", expanded=False):
                    for i, url in enumerate(st.session_state.start_urls, 1):
                        st.markdown(
                            f'<div style="padding:4px 0;font-size:0.8rem;font-family:\'Courier New\',monospace;'
                            f'color:#64748b;">{i}. {url}</div>',
                            unsafe_allow_html=True
                        )

            # Metriques principales - style massif
            col1, col2, col3, col4 = st.columns(4)

            metrics = [
                (col1, stats.get("pages_crawled", 0), "Pages crawlees"),
                (col2, stats.get("links_discovered", 0), "Liens decouverts"),
                (col3, stats.get("links_duplicate", 0), "Doublons"),
                (col4, stats.get("errors", 0), "Erreurs"),
            ]

            for col, value, label in metrics:
                with col:
                    st.markdown(
                        f'<div style="text-align:center;padding:24px;border:1px solid #e2e8f0;">'
                        f'<div style="font-size:2.5rem;font-weight:900;line-height:1;color:#0f172a;">{value}</div>'
                        f'<div style="font-size:0.6rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;'
                        f'color:#94a3b8;margin-top:10px;">{label}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            # Metriques secondaires - discrets, italiques
            s_col1, s_col2, s_col3 = st.columns(3)
            with s_col1:
                st.markdown(
                    f'<p style="font-size:0.75rem;color:#94a3b8;font-style:italic;">'
                    f'Pages ignorees : <strong>{stats.get("pages_skipped", 0)}</strong></p>',
                    unsafe_allow_html=True
                )
            with s_col2:
                st.markdown(
                    f'<p style="font-size:0.75rem;color:#94a3b8;font-style:italic;">'
                    f'Liens filtres : <strong>{stats.get("links_filtered", 0)}</strong></p>',
                    unsafe_allow_html=True
                )
            with s_col3:
                st.markdown(
                    f'<p style="font-size:0.75rem;color:#94a3b8;font-style:italic;">'
                    f'URLs visitees : <strong>{len(st.session_state.results)}</strong></p>',
                    unsafe_allow_html=True
                )

        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

        # ========== 04.5 / RAPPORT D'AUDIT GEO & DATA ==========
        render_geo_report(
            st.session_state.get("target_url", ""),
            st.session_state.get("ai_accessibility", {})
        )

        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

        # ========== MISTRAL OPTIMIZATION ==========
        render_mistral_optimization(st.session_state.get("target_url", ""))

        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

        # ========== 06 / JOURNAUX ==========
        st.markdown(
            '<p class="section-title">06 / JOURNAUX</p>',
            unsafe_allow_html=True
        )

        j_tab1, j_tab2, j_tab3 = st.tabs([
            "PAGES CRAWLEES",
            "LIENS FILTRES",
            "DOUBLONS"
        ])

        with j_tab1:
            render_journal_crawled(st.session_state.results)

        with j_tab2:
            render_journal_filtered(st.session_state.get("filtered_log", []))

        with j_tab3:
            render_journal_duplicates(st.session_state.get("duplicate_log", []))

        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

        # ========== 07 / GRAPHE ==========
        st.markdown(
            '<p class="section-title">07 / GRAPHE DE MAILLAGE</p>',
            unsafe_allow_html=True
        )

        c_expert, c_save_name, c_save_btn = st.columns([1, 2, 1])
        expert_on = c_expert.toggle("Score AI-READABLE", value=False)

        domain = urlparse(st.session_state.target_url).netloc
        s_name = c_save_name.text_input("Nom sauvegarde", value=domain.split('.')[0], label_visibility="collapsed")

        # Sauvegarde
        if c_save_btn.button("SAUVEGARDER", use_container_width=True):
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
                "start_urls": st.session_state.get('start_urls', [st.session_state.target_url])[:5],
                "ai_accessibility": st.session_state.get('ai_accessibility', {})
            }

            if len(st.session_state.results) > max_pages_to_save:
                st.markdown(
                    f'<p style="color:#FFA500;font-weight:700;font-size:0.8rem;">'
                    f'Seules les {max_pages_to_save} premieres pages sur {len(st.session_state.results)} seront sauvegardees '
                    f'(limite Google Sheets)</p>',
                    unsafe_allow_html=True
                )

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
