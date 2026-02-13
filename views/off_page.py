"""
HOTARU - Module Off-Page Reputation (V4.1 - Dashboard + Heat Map Edition)
Scanner de réputation avec visualisations claires et actionnables
"""

import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import json
import time
import random
import requests
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import re
import pandas as pd

# --- CONFIG SOURCES ---
SOURCE_CONFIG = {
    "reddit.com": {"label": "REDDIT", "color": "#FF4500", "priority": 1},
    "quora.com": {"label": "QUORA", "color": "#B92B27", "priority": 2},
    "wikipedia.org": {"label": "WIKIPEDIA", "color": "#000000", "priority": 1},
    "linkedin.com": {"label": "LINKEDIN", "color": "#0077B5", "priority": 2},
    "medium.com": {"label": "MEDIUM", "color": "#12100E", "priority": 3},
    "trustpilot.com": {"label": "TRUSTPILOT", "color": "#00B67A", "priority": 1},
    "youtube.com": {"label": "YOUTUBE", "color": "#FF0000", "priority": 1},
    "twitter.com": {"label": "X (TWITTER)", "color": "#1DA1F2", "priority": 2},
    "github.com": {"label": "GITHUB", "color": "#181717", "priority": 3},
    "stackoverflow.com": {"label": "STACKOVERFLOW", "color": "#F58025", "priority": 3}
}

# ==========================================
# SCRAPING & IA (CODE INCHANGÉ)
# ==========================================

class SmartScraper:
    """Scraper robuste pour extraction de l'ADN d'un site"""
    
    def __init__(self, start_urls: List[str], max_urls: int = 1, use_selenium: bool = False):
        self.start_urls = start_urls
        self.max_urls = max_urls
        self.use_selenium = use_selenium
        self.results = []
    
    def run_analysis(self):
        """Lance le scraping"""
        for url in self.start_urls[:self.max_urls]:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else ""
                
                h1 = soup.find('h1')
                h1_text = h1.get_text(strip=True) if h1 else ""
                
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                meta_text = meta_desc.get('content', '') if meta_desc else ""
                
                content_parts = []
                
                if h1_text:
                    content_parts.append(h1_text)
                
                for h2 in soup.find_all('h2')[:5]:
                    content_parts.append(h2.get_text(strip=True))
                
                for p in soup.find_all('p')[:10]:
                    text = p.get_text(strip=True)
                    if len(text) > 20:
                        content_parts.append(text)
                
                raw_text = " ".join(content_parts)[:1000]
                
                self.results.append({
                    'url': url,
                    'title': self._clean_text(title_text),
                    'h1': self._clean_text(h1_text),
                    'meta': self._clean_text(meta_text),
                    'raw_text': self._clean_text(raw_text),
                    'success': True
                })
                
            except Exception as e:
                self.results.append({
                    'url': url,
                    'error': str(e),
                    'success': False
                })
    
    def _clean_text(self, text: str) -> str:
        """Nettoie le texte extrait"""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

@st.cache_data(ttl=3600, show_spinner=False)
def get_internal_dna(url: str) -> Optional[Dict]:
    """Extrait l'ADN interne du site officiel"""
    try:
        scraper = SmartScraper(start_urls=[url], max_urls=1, use_selenium=False)
        scraper.run_analysis()
        
        if scraper.results and scraper.results[0].get('success'):
            result = scraper.results[0]
            return {
                'title': result['title'],
                'h1': result['h1'],
                'meta': result['meta'],
                'raw_text': result['raw_text']
            }
        return None
    except Exception as e:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def analyze_mirror_gap(internal_data: Dict, external_results: List[Dict], api_key: str) -> Optional[Dict]:
    """Analyse la dissonance cognitive entre promesse et perception"""
    try:
        external_summary = "\n".join([
            f"- {r['title']}: {r['desc'][:100]}"
            for r in external_results[:10]
        ])
        
        system_prompt = "Tu es un expert en sémiotique de marque. Tu compares l'émission (Site Web) et la réception (Google SERP)."
        
        user_prompt = f"""
SITE OFFICIEL (Ce que la marque DIT):
- Titre: {internal_data['title']}
- H1: {internal_data['h1']}
- Meta: {internal_data['meta']}
- Contexte: {internal_data['raw_text'][:500]}

GOOGLE SERP (Ce que le marché ENTEND):
{external_summary}

TÂCHE: Analyse la dissonance cognitive entre ces deux corpus.

Réponds UNIQUEMENT avec un JSON STRICT (pas de markdown, pas de backticks) au format:
{{
    "score": <int entre 0 et 100>,
    "analysis": "<analyse courte et cinglante, max 2 phrases>",
    "galaxy_nodes": {{
        "aligned": ["concept1", "concept2", "concept3", "concept4", "concept5"],
        "noise": ["concept1", "concept2", "concept3", "concept4", "concept5"],
        "invisible": ["concept1", "concept2", "concept3", "concept4", "concept5"]
    }}
}}

Règles:
- score: 100 = résonance parfaite, 0 = dissonance totale
- aligned: 5 mots-clés présents dans LES DEUX sources (Site ET Google)
- noise: 5 mots-clés présents UNIQUEMENT dans Google (bruit de marché)
- invisible: 5 mots-clés présents UNIQUEMENT sur le Site (occasion manquée)
"""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "mistral-large-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        content = content.strip()
        if content.startswith('```'):
            content = re.sub(r'^```json?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
        
        result = json.loads(content)
        
        if all(k in result for k in ['score', 'analysis', 'galaxy_nodes']):
            return result
        
        return None
        
    except Exception as e:
        st.error(f"Erreur Mistral: {e}")
        return None

# ==========================================
# SERPAPI (CODE INCHANGÉ)
# ==========================================

def _serpapi_search(query: str, max_results: int = 3, api_key: str = None) -> List[Dict]:
    """Recherche Google via SerpAPI"""
    if not api_key:
        return []
    
    try:
        params = {
            "q": query,
            "api_key": api_key,
            "num": max_results,
            "engine": "google",
            "hl": "fr",
            "gl": "fr"
        }
        
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=15
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        
        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append({
                "title": item.get("title", "Sans titre"),
                "description": item.get("snippet", ""),
                "url": item.get("link", "")
            })
        
        return results
        
    except Exception as e:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_scan(brand: str, scan_mode: str, api_key: str) -> Dict:
    """Scanner avec cache intelligent"""
    configs = {
        "fast": {"sources": 6, "results_per_source": 2, "delay": (0.5, 1.0)},
        "balanced": {"sources": 8, "results_per_source": 3, "delay": (0.8, 1.5)},
        "safe": {"sources": 10, "results_per_source": 3, "delay": (1.0, 2.0)}
    }
    
    config = configs.get(scan_mode, configs["balanced"])
    
    sorted_sources = sorted(
        SOURCE_CONFIG.items(),
        key=lambda x: x[1].get('priority', 99)
    )[:config["sources"]]
    
    results = []
    
    for domain, meta in sorted_sources:
        source_name = meta["label"]
        query = f'"{brand}" site:{domain}'
        found = _serpapi_search(query, max_results=config["results_per_source"], api_key=api_key)
        
        for item in found:
            results.append({
                "source": source_name,
                "domain_key": domain,
                "title": item['title'],
                "desc": item['description'],
                "url": item['url']
            })
        
        delay = random.uniform(*config["delay"])
        time.sleep(delay)
    
    return {
        "results": results,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": scan_mode
    }

def _scan_with_ui(brand: str, status_container, log_container, scan_mode: str, api_key: str):
    """Wrapper UI pour le scan"""
    logs = []
    
    configs = {
        "fast": {"label": "RAPIDE", "eta": "~15s"},
        "balanced": {"label": "ÉQUILIBRÉ", "eta": "~25s"},
        "safe": {"label": "COMPLET", "eta": "~35s"}
    }
    
    config_ui = configs.get(scan_mode, configs["balanced"])
    
    sorted_sources = sorted(
        SOURCE_CONFIG.items(),
        key=lambda x: x[1].get('priority', 99)
    )[:{"fast": 6, "balanced": 8, "safe": 10}.get(scan_mode, 8)]
    
    total = len(sorted_sources)
    progress_bar = status_container.progress(0, text=f"Initialisation // Mode {config_ui['label']} (ETA: {config_ui['eta']})...")
    
    for i, (domain, meta) in enumerate(sorted_sources):
        source_name = meta["label"]
        progress_bar.progress(i / total, text=f"Scan : {source_name}... [{i+1}/{total}]")
        
        log_html = f"<span style='color:#10b981'>[●]</span> Interrogation de {source_name}..."
        logs.append(log_html)
        
        log_display = "<br>".join(logs[-8:])
        log_container.markdown(
            f"""
            <div style="background:#0f172a; color:#cbd5e1; padding:16px; border-radius:8px; 
                        font-family:'Courier New'; font-size:0.85rem; line-height:1.6; 
                        border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                <div style="border-bottom:1px solid #334155; padding-bottom:8px; margin-bottom:8px; 
                            color:#94a3b8; font-weight:700; letter-spacing:0.05em;">
                    > HOTARU_SCAN_PROTOCOL // V4.1_DASHBOARD // {config_ui['label']}
                </div>
                {log_display}
                <div style="margin-top:8px; color:#10b981; font-weight:bold;">
                    <span style="animation: blink 1s infinite;">▮</span> Scan en cours...
                </div>
            </div>
            <style>
                @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
            </style>
            """,
            unsafe_allow_html=True
        )
        
        time.sleep(0.2)
    
    scan_data = _cached_scan(brand, scan_mode, api_key)
    
    logs = []
    results_by_source = {}
    for r in scan_data["results"]:
        results_by_source.setdefault(r['source'], 0)
        results_by_source[r['source']] += 1
    
    for domain, meta in sorted_sources:
        source_name = meta["label"]
        count = results_by_source.get(source_name, 0)
        
        if count > 0:
            log_html = f"<span style='color:#10b981'>[OK]</span> {count} mentions sur {source_name}"
        else:
            log_html = f"<span style='color:#64748b'>[-]</span> Aucune donnée sur {source_name}"
        logs.append(log_html)
    
    log_display = "<br>".join(logs)
    log_container.markdown(
        f"""
        <div style="background:#0f172a; color:#cbd5e1; padding:16px; border-radius:8px; 
                    font-family:'Courier New'; font-size:0.85rem; line-height:1.6; 
                    border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
            <div style="border-bottom:1px solid #334155; padding-bottom:8px; margin-bottom:8px; 
                        color:#94a3b8; font-weight:700; letter-spacing:0.05em;">
                > SCAN TERMINÉ // {scan_data['timestamp']}
            </div>
            {log_display}
            <div style="margin-top:12px; color:#10b981; font-weight:bold;">
                {len(scan_data['results'])} mentions extraites via SerpAPI
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    progress_bar.progress(1.0, text="Scan terminé avec succès")
    time.sleep(1.5)
    status_container.empty()
    
    return scan_data["results"]

# ==========================================
# NOUVELLES VISUALISATIONS
# ==========================================

def render_dashboard(brand: str, analysis: Dict, internal_data: Dict):
    """
    Dashboard 3 colonnes : Alignés / Bruit / Invisibles
    """
    nodes = analysis.get('galaxy_nodes', {})
    aligned = nodes.get('aligned', [])
    noise = nodes.get('noise', [])
    invisible = nodes.get('invisible', [])
    
    st.markdown(
        f"""
        <div style="text-align:center; padding:20px; background:#f8fafc; border-radius:12px; margin-bottom:24px;">
            <div style="font-size:1.2rem; font-weight:700; color:#0f172a; margin-bottom:12px;">
                AUDIT MIROIR : {brand.upper()}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns(3)
    
    # COLONNE 1 : ALIGNÉS
    with col1:
        st.markdown(
            """
            <div style="background:#ecfdf5; padding:16px; border-radius:8px; border:2px solid #10b981;">
                <div style="text-align:center; font-size:1.1rem; font-weight:800; color:#10b981; margin-bottom:12px;">
                    ALIGNÉS
                </div>
                <div style="text-align:center; font-size:0.75rem; color:#059669; margin-bottom:16px;">
                    Vous dites + Google dit (BIEN)
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        for concept in aligned:
            st.markdown(
                f"""
                <div style="background:#d1fae5; padding:10px; margin:8px 0; border-radius:6px; 
                            text-align:center; font-weight:600; color:#047857;">
                    {concept.upper()}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown(
            f"""
            <div style="text-align:center; margin-top:16px; font-size:0.9rem; color:#059669; font-weight:600;">
                {len(aligned)} concepts
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # COLONNE 2 : BRUIT
    with col2:
        st.markdown(
            """
            <div style="background:#fef2f2; padding:16px; border-radius:8px; border:2px solid #ef4444;">
                <div style="text-align:center; font-size:1.1rem; font-weight:800; color:#ef4444; margin-bottom:12px;">
                    BRUIT
                </div>
                <div style="text-align:center; font-size:0.75rem; color:#dc2626; margin-bottom:16px;">
                    Google dit MAIS vous ne dites pas (DANGER)
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        for concept in noise:
            st.markdown(
                f"""
                <div style="background:#fecaca; padding:10px; margin:8px 0; border-radius:6px; 
                            text-align:center; font-weight:600; color:#991b1b;">
                    {concept.upper()}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown(
            f"""
            <div style="text-align:center; margin-top:16px; font-size:0.9rem; color:#dc2626; font-weight:600;">
                {len(noise)} concepts
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # COLONNE 3 : INVISIBLES
    with col3:
        st.markdown(
            """
            <div style="background:#eff6ff; padding:16px; border-radius:8px; border:2px solid #3b82f6;">
                <div style="text-align:center; font-size:1.1rem; font-weight:800; color:#3b82f6; margin-bottom:12px;">
                    INVISIBLES
                </div>
                <div style="text-align:center; font-size:0.75rem; color:#2563eb; margin-bottom:16px;">
                    Vous dites MAIS Google ignore (GÂCHIS)
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        for concept in invisible:
            st.markdown(
                f"""
                <div style="background:#bfdbfe; padding:10px; margin:8px 0; border-radius:6px; 
                            text-align:center; font-weight:600; color:#1e40af;">
 {concept.upper()}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown(
            f"""
            <div style="text-align:center; margin-top:16px; font-size:0.9rem; color:#2563eb; font-weight:600;">
                {len(invisible)} concepts
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Légende
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="background:#f1f5f9; padding:16px; border-radius:8px; font-size:0.85rem;">
            <strong>Légende :</strong><br>
            <strong>ALIGNÉS</strong> : Concepts présents sur votre site ET dans Google = Communication efficace<br>
            <strong>BRUIT</strong> : Concepts absents de votre site MAIS dominants sur Google = Risque réputationnel<br>
            <strong>INVISIBLES</strong> : Concepts présents sur votre site MAIS invisibles dans Google = SEO à optimiser
        </div>
        """,
        unsafe_allow_html=True
    )

def render_heat_map(brand: str, analysis: Dict, external_results: List[Dict], internal_data: Dict):
    """
    Heat Map : Tableau de chaleur Promesse vs Réalité
    """
    nodes = analysis.get('galaxy_nodes', {})
    aligned = nodes.get('aligned', [])
    noise = nodes.get('noise', [])
    invisible = nodes.get('invisible', [])
    
    # Préparation des données
    data = []
    
    # Alignés
    for concept in aligned:
        data.append({
            'Concept': concept.upper(),
            'Site': '████',
            'Google': '████',
            'Statut': 'Aligné',
            'Catégorie': 'aligned'
        })
    
    # Bruit
    for concept in noise:
        data.append({
            'Concept': concept.upper(),
            'Site': '░',
            'Google': '████',
            'Statut': 'Bruit',
            'Catégorie': 'noise'
        })
    
    # Invisibles
    for concept in invisible:
        data.append({
            'Concept': concept.upper(),
            'Site': '███',
            'Google': '░',
            'Statut': 'Invisible',
            'Catégorie': 'invisible'
        })
    
    df = pd.DataFrame(data)
    
    st.markdown(
        """
        <div style="text-align:center; padding:16px; background:#f8fafc; border-radius:8px; margin-bottom:20px;">
            <div style="font-size:1.2rem; font-weight:700; color:#0f172a;">
                CARTE DE CHALEUR : Promesse vs Réalité
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Affichage du tableau stylisé
    for _, row in df.iterrows():
        if row['Catégorie'] == 'aligned':
            bg_color = "#ecfdf5"
            border_color = "#10b981"
        elif row['Catégorie'] == 'noise':
            bg_color = "#fef2f2"
            border_color = "#ef4444"
        else:
            bg_color = "#eff6ff"
            border_color = "#3b82f6"
        
        st.markdown(
            f"""
            <div style="background:{bg_color}; padding:12px; margin:8px 0; border-radius:6px; 
                        border-left:4px solid {border_color}; display:flex; justify-content:space-between; align-items:center;">
                <div style="flex:2; font-weight:700; font-size:0.9rem;">
                    {row['Concept']}
                </div>
                <div style="flex:1; text-align:center; font-family:monospace; font-size:0.85rem;">
                    {row['Site']}
                </div>
                <div style="flex:1; text-align:center; font-family:monospace; font-size:0.85rem;">
                    {row['Google']}
                </div>
                <div style="flex:1; text-align:right; font-weight:600; font-size:0.85rem;">
                    {row['Statut']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Légende
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="background:#f1f5f9; padding:16px; border-radius:8px; font-size:0.85rem;">
            <strong>Légende :</strong><br>
            <span style="font-family:monospace;">████</span> = Très présent (5+ mentions)<br>
            <span style="font-family:monospace;">███</span> = Présent (3-4 mentions)<br>
            <span style="font-family:monospace;">██</span> = Peu présent (1-2 mentions)<br>
            <span style="font-family:monospace;">░</span> = Absent
        </div>
        """,
        unsafe_allow_html=True
    )

def render_detailed_analysis(brand: str, analysis: Dict, external_results: List[Dict], internal_data: Dict):
    """
    Analyse détaillée par catégorie avec URLs
    """
    nodes = analysis.get('galaxy_nodes', {})
    aligned = nodes.get('aligned', [])
    noise = nodes.get('noise', [])
    invisible = nodes.get('invisible', [])
    
    st.markdown("## ANALYSE DÉTAILLÉE PAR CATÉGORIE")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # === SECTION ALIGNÉS ===
    st.markdown(
        """
        <div style="background:#ecfdf5; padding:16px; border-radius:8px; border-left:4px solid #10b981; margin-bottom:24px;">
            <div style="font-size:1.1rem; font-weight:800; color:#10b981; margin-bottom:8px;">
                CONCEPTS ALIGNÉS ({}) - C'est votre force !
            </div>
            <div style="font-size:0.85rem; color:#059669;">
                Ces concepts sont présents à la fois sur votre site ET dans les résultats Google
            </div>
        </div>
        """.format(len(aligned)),
        unsafe_allow_html=True
    )
    
    for concept in aligned:
        # Recherche dans les résultats Google
        matching_results = [r for r in external_results if concept.lower() in r['title'].lower() or concept.lower() in r['desc'].lower()]
        
        st.markdown(
            f"""
            <div style="background:#f0fdf4; padding:14px; margin:12px 0; border-radius:6px; border:1px solid #bbf7d0;">
                <div style="font-weight:700; font-size:0.95rem; color:#15803d; margin-bottom:8px;">
                    {concept.upper()}
                </div>
                <div style="font-size:0.8rem; color:#166534; margin-bottom:6px;">
                    <strong>Présent sur votre site :</strong> {internal_data.get('h1', 'N/A')[:80]}...
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if matching_results:
            st.markdown('<div style="margin-left:16px; font-size:0.8rem; color:#166534; margin-bottom:6px;"><strong>Présent sur Google :</strong></div>', unsafe_allow_html=True)
            for res in matching_results[:3]:
                # Extraction du domaine
                domain = res['url'].split('/')[2] if len(res['url'].split('/')) > 2 else res['url']
                st.markdown(
                    f"""
                    <div style="margin-left:16px; font-size:0.75rem; color:#059669; margin-bottom:4px;">
                        • <strong>{res['source']}</strong> : {res['title'][:60]}... <span style="color:#64748b;">({domain})</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # === SECTION BRUIT ===
    st.markdown(
        """
        <div style="background:#fef2f2; padding:16px; border-radius:8px; border-left:4px solid #ef4444; margin-bottom:24px;">
            <div style="font-size:1.1rem; font-weight:800; color:#ef4444; margin-bottom:8px;">
                CONCEPTS BRUIT ({}) - DANGER ! Non maîtrisés
            </div>
            <div style="font-size:0.85rem; color:#dc2626;">
                Ces concepts sont dominants sur Google MAIS absents de votre site
            </div>
        </div>
        """.format(len(noise)),
        unsafe_allow_html=True
    )
    
    for concept in noise:
        matching_results = [r for r in external_results if concept.lower() in r['title'].lower() or concept.lower() in r['desc'].lower()]
        
        st.markdown(
            f"""
            <div style="background:#fef2f2; padding:14px; margin:12px 0; border-radius:6px; border:1px solid #fecaca;">
                <div style="font-weight:700; font-size:0.95rem; color:#dc2626; margin-bottom:8px;">
 {concept.upper()}
                </div>
                <div style="font-size:0.8rem; color:#991b1b; margin-bottom:6px;">
 Absent de votre site
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        if matching_results:
            st.markdown(f'<div style="margin-left:16px; font-size:0.8rem; color:#991b1b; margin-bottom:6px;"><strong>Sur Google ({len(matching_results)} mentions) :</strong></div>', unsafe_allow_html=True)
            for res in matching_results[:3]:
                domain = res['url'].split('/')[2] if len(res['url'].split('/')) > 2 else res['url']
                st.markdown(
                    f"""
                    <div style="margin-left:16px; font-size:0.75rem; color:#dc2626; margin-bottom:4px;">
                        • <strong>{res['source']}</strong> : {res['title'][:60]}... <span style="color:#64748b;">({domain})</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # === SECTION INVISIBLES ===
    st.markdown(
        """
        <div style="background:#eff6ff; padding:16px; border-radius:8px; border-left:4px solid #3b82f6; margin-bottom:24px;">
            <div style="font-size:1.1rem; font-weight:800; color:#3b82f6; margin-bottom:8px;">
                CONCEPTS INVISIBLES ({}) - Opportunités SEO
            </div>
            <div style="font-size:0.85rem; color:#2563eb;">
                Ces concepts sont présents sur votre site MAIS invisibles dans Google
            </div>
        </div>
        """.format(len(invisible)),
        unsafe_allow_html=True
    )
    
    for concept in invisible:
        st.markdown(
            f"""
            <div style="background:#eff6ff; padding:14px; margin:12px 0; border-radius:6px; border:1px solid #bfdbfe;">
                <div style="font-weight:700; font-size:0.95rem; color:#2563eb; margin-bottom:8px;">
                    {concept.upper()}
                </div>
                <div style="font-size:0.8rem; color:#1e40af; margin-bottom:6px;">
                    <strong>Présent sur votre site :</strong> {internal_data.get('meta', 'N/A')[:80]}...
                </div>
                <div style="font-size:0.8rem; color:#1e3a8a;">
 Google ne le voit pas (0 mentions)
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ==========================================
# INTERFACE STREAMLIT
# ==========================================

def render_off_page_audit():
    """Interface principale avec Dashboard + Heat Map"""
    st.markdown('<p class="section-title">01 / AUDIT DE RÉPUTATION (OFF-PAGE)</p>', unsafe_allow_html=True)
    
    # Lecture des clés API
    serpapi_key = None
    mistral_key = None
    
    try:
        serpapi_key = st.secrets["SERPAPI_KEY"]
    except:
        pass
    
    try:
        mistral_key = st.secrets["mistral"]["api_key"]
    except:
        pass
    
    if not serpapi_key:
        st.error(" Clé SERPAPI_KEY manquante dans Secrets")
        return
    
    st.markdown(
        f'<p style="font-size:0.75rem;color:#10b981;font-weight:600;margin-bottom:16px;">'
        f'SerpAPI configurée ({serpapi_key[:8]}...)</p>', 
        unsafe_allow_html=True
    )
    
    # --- INPUTS ---
    col1, col2 = st.columns([2, 1])
    
    brand_input = col1.text_input(
        "Marque", 
        value="", 
        placeholder="Ex: Tesla, Nike, Apple...",
        label_visibility="collapsed"
    )
    
    official_site = col2.text_input(
        "Site Officiel (Optionnel)",
        value="",
        placeholder="https://www.exemple.com",
        label_visibility="collapsed",
        help="Active l'Audit Miroir si rempli"
    )
    
    col3, col4 = st.columns([1, 1])
    
    scan_mode = col3.selectbox(
        "Mode",
        options=["balanced", "safe", "fast"],
        format_func=lambda x: {
            "fast": "Rapide", 
            "balanced": "Équilibré", 
            "safe": "Complet"
        }[x],
        label_visibility="collapsed",
        index=0
    )
    
    # Initialisation session state
    if 'offpage_results' not in st.session_state:
        st.session_state['offpage_results'] = []
    if 'mirror_data' not in st.session_state:
        st.session_state['mirror_data'] = None
    
    # Bouton de scan
    scan_button = col4.button("SCANNER", type="primary", use_container_width=True)
    
    if scan_button:
        if not brand_input:
            st.warning(" Nom de marque requis")
        else:
            status_box = st.empty()
            log_box = st.empty()
            
            # Scan Google
            results = _scan_with_ui(brand_input, status_box, log_box, scan_mode, serpapi_key)
            
            st.session_state['offpage_results'] = results
            st.session_state['offpage_brand'] = brand_input
            st.session_state['offpage_mode'] = scan_mode
            
            # Audit Miroir si site officiel fourni
            if official_site and mistral_key:
                with st.spinner(" Scraping du site officiel..."):
                    internal_data = get_internal_dna(official_site)
                
                if internal_data:
                    with st.spinner("Analyse sémantique avec Mistral..."):
                        mirror_analysis = analyze_mirror_gap(internal_data, results, mistral_key)
                    
                    if mirror_analysis:
                        st.session_state['mirror_data'] = {
                            'internal': internal_data,
                            'analysis': mirror_analysis
                        }
                        st.success("Audit Miroir terminé !")
                    else:
                        st.warning(" Erreur lors de l'analyse Mistral")
                else:
                    st.warning(" Impossible de scraper le site officiel")
            elif official_site and not mistral_key:
                st.warning(" Clé Mistral manquante pour l'Audit Miroir")
            
            if results:
                st.success(f"{len(results)} mentions trouvées")
            else:
                st.info("Aucune mention trouvée.")
    
    # --- AFFICHAGE RÉSULTATS ---
    results = st.session_state.get('offpage_results', [])
    brand_name = st.session_state.get('offpage_brand', brand_input)
    mirror_data = st.session_state.get('mirror_data')
    
    if results:
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        
        # AFFICHAGE AUDIT MIROIR
        if mirror_data:
            analysis = mirror_data['analysis']
            internal = mirror_data['internal']
            
            # Score d'alignement
            score = analysis.get('score', 0)
            
            if score >= 80:
                color = "#10b981"
                status = "EXCELLENT"
            elif score >= 60:
                color = "#f59e0b"
                status = "MOYEN"
            else:
                color = "#ef4444"
                status = "FAIBLE"
            
            st.markdown(
                f"""
                <div style="text-align:center; padding:24px; background:linear-gradient(135deg, {color}22 0%, {color}11 100%); 
                            border-radius:12px; border:2px solid {color};">
                    <div style="font-size:4rem; font-weight:900; color:{color}; line-height:1;">
                        {score}<span style="font-size:2rem;">/100</span>
                    </div>
                    <div style="font-size:1.2rem; font-weight:700; color:{color}; margin-top:8px;">
                        SCORE D'ALIGNEMENT : {status}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Analyse de l'IA
            st.info(f"**Analyse :** {analysis.get('analysis', 'N/A')}")
            
            st.markdown("<br>", unsafe_allow_html=True)
        
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Mentions", len(results))
        k2.metric("Sources", len(set(r['source'] for r in results)))
        k3.metric("Mode", {"fast": "Rapide", "balanced": "Équilibré", "safe": "Complet"}.get(scan_mode, 'Équilibré'))
        k4.metric("Cache", "1h")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabs
        if mirror_data:
            tab_dashboard, tab_heatmap, tab_analysis, tab_export, tab_method = st.tabs([
                "DASHBOARD", 
                "HEAT MAP",
                "ANALYSE",
                "EXPORT",
                "MÉTHODOLOGIE"
            ])
            
            with tab_dashboard:
                render_dashboard(brand_name, mirror_data['analysis'], mirror_data['internal'])
            
            with tab_heatmap:
                render_heat_map(brand_name, mirror_data['analysis'], results, mirror_data['internal'])
            
            with tab_analysis:
                render_detailed_analysis(brand_name, mirror_data['analysis'], results, mirror_data['internal'])
            
            with tab_export:
                export_data = {
                    "brand": brand_name,
                    "scan_mode": scan_mode,
                    "alignment_score": mirror_data['analysis'].get('score'),
                    "analysis": mirror_data['analysis'].get('analysis'),
                    "total_mentions": len(results),
                    "mentions": results,
                    "galaxy_nodes": mirror_data['analysis'].get('galaxy_nodes')
                }
                
                json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
                
                st.download_button(
                    label="Télécharger JSON Complet",
                    data=json_data,
                    file_name=f"hotaru_mirror_audit_{brand_name.lower().replace(' ', '_')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with tab_method:
                st.markdown("""
                ### Boussole Méthodologique : Comprendre le Score d'Alignement
                
                Le **Score d'Alignement HOTARU** mesure la distance sémantique entre votre émission (Site Officiel) 
                et votre réception (SERP Google).
                
                #### Méthodologie : Le Score de Dissonance Cognitive
                
                **1. Extraction de l'ADN (Scraping Hybride)**  
                Nous isolons les balises H1, Title et Meta Description de votre page d'accueil via notre module SmartScraper. 
                C'est votre "Promesse Officielle".
                
                **2. Analyse du Bruit (Réception)**  
                Nous analysons les snippets des 10 premiers résultats Google (hors votre site) pour identifier 
                les thématiques dominantes.
                
                **3. Calcul du Gap (IA)**  
                Notre moteur neuronal (Mistral AI) compare ces deux corpus :
                
                * **100%** : Résonance parfaite. Le marché répète exactement votre message.
                * **80-99%** : Bon alignement avec quelques nuances.
                * **60-79%** : Alignement moyen, certains messages se perdent.
                * **< 60%** : Dissonance. Le marché vous associe à des sujets que vous ne maîtrisez pas 
                  (bugs, polémiques, concurrents).
                
                #### Interprétation des Visualisations
                
                ** DASHBOARD (3 colonnes)**  
                Vue d'ensemble immédiate de votre alignement :
                * **Alignés** : Votre cœur de communication efficace
                * **Bruit** : Risques réputationnels non maîtrisés
                * **Invisibles** : Potentiel SEO inexploité
                
                **HEAT MAP (Tableau de chaleur)**  
                Comparaison visuelle de la présence de chaque concept sur votre site vs Google.
                Plus les barres sont pleines, plus le concept est présent.
                
                ** ANALYSE DÉTAILLÉE**  
                Exploration approfondie concept par concept avec les sources Google exactes.
                """)
        
        else:
            # Mode classique sans Audit Miroir (liste + export + méthodologie toujours visible)
            tab_list, tab_export, tab_method = st.tabs(["LISTE", "EXPORT", "MÉTHODOLOGIE"])
            
            with tab_list:
                for m in results:
                    color = SOURCE_CONFIG.get(m['domain_key'], {}).get('color', '#333')
                    st.markdown(
                        f"""
                        <div style="border-left:3px solid {color}; padding:12px; margin-bottom:12px; 
                                    background:#fafafa; border-radius:4px;">
                            <div style="font-size:0.7rem; font-weight:800; color:{color}; 
                                        letter-spacing:0.1em; text-transform:uppercase;">
                                {m['source']}
                            </div>
                            <div style="font-weight:600; font-size:0.95rem; margin:6px 0;">
                                <a href="{m['url']}" target="_blank" style="color:#0f172a; text-decoration:none;">
                                    {m['title']}
                                </a>
                            </div>
                            <div style="font-size:0.75rem; color:#64748b; font-family:'Courier New';">
                                {m['url']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            
            with tab_export:
                export_data = {
                    "brand": brand_name,
                    "scan_mode": scan_mode,
                    "total_mentions": len(results),
                    "mentions": results
                }
                
                json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
                
                st.download_button(
                    label="Télécharger JSON",
                    data=json_data,
                    file_name=f"hotaru_scan_{brand_name.lower().replace(' ', '_')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with tab_method:
                st.markdown("""
                ### Boussole Méthodologique : Audit Externe (Réputation)

                L'**Audit Externe HOTARU** analyse la réception de votre marque sur Google : quels sites parlent de vous, avec quels angles.

                #### Mode Liste (sans Site Officiel)
                * **LISTE** : Toutes les mentions trouvées (snippets, titres, URLs).
                * **EXPORT** : Téléchargement JSON pour analyse externe.

                #### Mode Audit Miroir (avec Site Officiel)
                Si vous renseignez le **Site Officiel** et relancez le scan, vous débloquez :
                * **Score d'alignement** : distance sémantique entre votre message officiel (H1, Title, Meta) et ce que Google affiche.
                * **Dashboard** : concepts alignés / bruit / invisibles.
                * **Heat Map** : présence de chaque concept sur votre site vs SERP.
                * **Analyse détaillée** : concept par concept avec sources.

                #### Méthodologie du Score d'Alignement (Audit Miroir)
                1. **Extraction de l'ADN** : scraping H1, Title, Meta de votre page d'accueil.
                2. **Analyse du Bruit** : thématiques dominantes dans les 10 premiers résultats Google (hors votre site).
                3. **Calcul du Gap** : Mistral AI compare les deux corpus (100% = résonance parfaite, moins de 60% = dissonance).
                """)
    
    # Options avancées
    st.markdown("**Options avancées**")
    col_a, col_b = st.columns(2)
        
    if col_a.button("Vider le cache", use_container_width=True):
        _cached_scan.clear()
        get_internal_dna.clear()
        analyze_mirror_gap.clear()
        st.session_state['offpage_results'] = []
        st.session_state['mirror_data'] = None
        st.success("Cache vidé.")
    
    if col_b.button("Statistiques API", use_container_width=True):
        st.info(
            "**APIs utilisées :**\n\n"
            "• SerpAPI : 100 req/mois gratuit\n"
            "• Mistral AI : Selon votre plan\n"
            "• Scraping : Illimité"
        )