# =============================================================================
# AUDIT GEO - HOTARU DESIGN SYSTEM (V3 - REFONTE VISUELLE TOTALE)
# Zero icone. Typographie stricte. Esthetique finance/terminal.
# =============================================================================

import streamlit as st
import json
import re
import html
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
from core.session_keys import get_current_user_email
from core.scraping import SmartScraper
from modules.off_page import render_off_page_audit

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

def check_geo_infrastructure(base_url, crawl_results=None):
    """Vérifie l'infrastructure GEO en utilisant les résultats du crawl si disponibles"""
    domain = base_url.rstrip('/')
    assets = {
        "robots.txt": {"url": f"{domain}/robots.txt", "desc": "Autorise GPTBot et les crawlers IA."},
        "sitemap.xml": {"url": f"{domain}/sitemap.xml", "desc": "Guide d'indexation pour les moteurs de reponse."},
        "llms.txt": {"url": f"{domain}/llms.txt", "desc": "Standard 2025 pour la consommation LLM."},
        "JSON-LD": {"url": domain, "desc": "Donnees structurees (Entites de marque)."}
    }
    results = {}
    score = 0
    
    # Vérifier robots.txt, sitemap.xml, llms.txt avec requests
    for name, data in list(assets.items())[:3]:
        try:
            r = requests.get(data['url'], timeout=3)
            found = (r.status_code == 200)
            results[name] = {"status": found, "meta": data}
            if found: 
                score += 25
        except: 
            results[name] = {"status": False, "meta": data}
    
    # Vérifier JSON-LD depuis les résultats du crawl (déjà fait avec Selenium si SPA)
    has_json = False
    if crawl_results:
        # Chercher dans les pages crawlées si au moins une a du JSON-LD
        for page in crawl_results:
            if page.get('json_ld') or page.get('has_structured_data'):
                has_json = True
                break
    
    # Fallback : vérifier avec requests (pour sites non-SPA)
    if not has_json and not crawl_results:
        try:
            r = requests.get(domain, timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            scripts = soup.find_all('script', type=True)
            has_json = any('ld+json' in (s.get('type') or '').lower() for s in scripts)
        except:
            has_json = False
    
    results["JSON-LD"] = {"status": has_json, "meta": assets["JSON-LD"]}
    if has_json: 
        score += 25
    
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
    """Libellé court pour les nœuds du graphe ; ne retourne jamais une chaîne vide."""
    try:
        raw = (title or "").strip()
        clean = re.split(r' [-|:|] ', raw)[0].strip() if raw else ""
        if len(clean) < 4:
            path = (url or "").rstrip("/")
            parts = path.split("/")
            last = parts[-1] if parts else ""
            clean = last.replace("-", " ").replace("_", " ").strip().title() or domain or "Page"
        if not clean:
            clean = domain or "Page"
        return (clean[:20] + "..") if len(clean) > 22 else clean
    except Exception:
        return (urlparse(url).path or "/").strip("/").replace("-", " ").title() or "Page"


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
    """Vue A : Journal des pages crawlees, classees par categories. Sans accordeon : sections plates pour afficher tous les noms."""
    categories = categorize_urls(results)

    st.markdown(
        f'<p style="font-size:0.75rem;font-weight:600;color:#94a3b8;margin-bottom:20px;">'
        f'{len(results)} pages analysees  &mdash;  {len(categories)} categories detectees</p>',
        unsafe_allow_html=True
    )

    # En-tete de tableau (GRADE PAGE = grade + titre page ; PATH = chemin)
    st.markdown(
        '<div class="journal-table-header" style="display:flex;align-items:center;padding:10px 0;border-bottom:2px solid #0f172a;margin-bottom:4px;">'
        '<span class="journal-col-grade-page" style="font-size:0.7rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#0f172a;flex:1;min-width:0;">GRADE PAGE</span>'
        '<span class="journal-col-path" style="font-size:0.7rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#0f172a;width:300px;text-align:right;flex-shrink:0;">PATH</span>'
        '</div>',
        unsafe_allow_html=True
    )

    for cat_name, pages in categories.items():
        # Titre de section (plus d'accordéon)
        st.markdown(
            f'<p style="font-size:0.65rem;font-weight:800;letter-spacing:0.15em;text-transform:uppercase;color:#94a3b8;margin:16px 0 8px 0;">{html.escape(cat_name)}  ({len(pages)})</p>',
            unsafe_allow_html=True
        )
        # Un seul bloc HTML par catégorie : toutes les lignes dedans (évite bugs d'affichage)
        rows_html = []
        for p in pages:
            score_data = calculate_page_score(p)
            if isinstance(score_data, tuple):
                sc, grade, _, _ = score_data
            else:
                sc, grade = score_data, 'N/A'

            col = _grade_color(grade)
            url = p.get('url', '') or ''
            path = urlparse(url).path or '/'
            raw_title = (p.get('title') or '').strip()
            title = raw_title if raw_title else (path.strip('/').replace('-', ' ').replace('_', ' ').title() if path != '/' else 'Sans titre')
            if not title or title == '/':
                title = 'Sans titre'
            title_safe = html.escape(title)
            path_safe = html.escape(path)
            url_safe = html.escape(url)

            rows_html.append(
                f'<div class="journal-table-row" style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f1f5f9;">'
                f'<span class="grade-badge-circle" style="background:{col};color:#fff;border:2px solid #fff;'
                f'width:28px;height:28px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;'
                f'font-size:0.65rem;font-weight:800;letter-spacing:0.05em;flex-shrink:0;">{grade}</span>'
                f'<span class="journal-page-title" style="font-size:0.85rem;font-weight:600;color:#0f172a;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
                f'<a href="{url_safe}" target="_blank" style="color:#0f172a;text-decoration:none;"'
                f' onmouseover="this.style.borderBottom=\'1px solid #0f172a\'"'
                f' onmouseout="this.style.borderBottom=\'none\'">{title_safe}</a></span>'
                f'<span style="font-size:0.7rem;color:#94a3b8;font-family:\'Courier New\',monospace;'
                f'width:300px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:right;">{path_safe}</span>'
                f'</div>'
            )
        st.markdown('<div class="journal-category-block">' + ''.join(rows_html) + '</div>', unsafe_allow_html=True)


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
            f'min-width:40px;text-align:center;"