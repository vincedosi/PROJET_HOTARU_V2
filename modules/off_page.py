"""
HOTARU - Module Off-Page Reputation (V3.5 - Production Ready)
Scanner de réputation off-page avec SerpAPI
Clé API configurée dans Streamlit Secrets
"""

import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import json
import time
import random
import requests
from typing import List, Dict
from datetime import datetime

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

def render_interactive_graph(G):
    """Moteur de rendu Pyvis pour le graphe de réputation"""
    nt = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#0f172a")
    nt.from_nx(G)
    
    opts = {
        "nodes": {
            "font": {
                "face": "Inter", 
                "size": 14, 
                "strokeWidth": 3, 
                "strokeColor": "#fff", 
                "color": "#0f172a"
            },
            "borderWidth": 2
        },
        "edges": {
            "color": "#cbd5e1", 
            "width": 1.5, 
            "smooth": {"type": "dynamic", "roundness": 0.2}
        },
        "interaction": {
            "hover": True, 
            "navigationButtons": True, 
            "zoomView": True
        },
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -100,
                "centralGravity": 0.05,
                "springLength": 150,
                "springConstant": 0.08,
                "avoidOverlap": 1
            },
            "solver": "forceAtlas2Based",
            "stabilization": {"enabled": True, "iterations": 200}
        }
    }
    nt.set_options(json.dumps(opts))
    
    path = "temp_offpage_graph.html"
    nt.save_graph(path)
    
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    
    custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        * { font-family: 'Inter', sans-serif !important; }
    </style>
    """
    components.html(html.replace("</body>", custom_css + "</body>"), height=750)

def build_reputation_graph(brand: str, mentions: List[Dict]):
    """Construction du graphe en étoile : marque au centre, sources autour"""
    G = nx.DiGraph()
    
    # Nœud central (la marque)
    G.add_node(
        brand, 
        label=brand.upper(), 
        size=45, 
        color="#0f172a",
        font={'color': '#ffffff', 'size': 20},
        title="MARQUE CIBLE"
    )
    
    # Nœuds satellites (les mentions)
    for m in mentions:
        color = SOURCE_CONFIG.get(m['domain_key'], {}).get('color', '#64748b')
        label = SOURCE_CONFIG.get(m['domain_key'], {}).get('label', 'AUTRE')
        
        G.add_node(
            m['url'],
            label=label,
            size=20,
            color=color,
            title=f"{m['title']}\n{m['url']}"
        )
        G.add_edge(brand, m['url'], color="#cbd5e1")
    
    return G

def _serpapi_search(query: str, max_results: int = 3, api_key: str = None) -> List[Dict]:
    """
    Recherche Google via SerpAPI (pas de blocage, 100% fiable)
    
    Args:
        query: Requête Google (ex: "Tesla" site:reddit.com)
        max_results: Nombre de résultats à récupérer
        api_key: Clé API SerpAPI
    
    Returns:
        Liste de dicts avec title, description, url
    """
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
        
        # Extraction des résultats organiques
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
    """
    Scanner avec cache intelligent (1h)
    Évite les requêtes répétées pour la même marque
    
    Args:
        brand: Nom de la marque à scanner
        scan_mode: Mode de scan (fast/balanced/safe)
        api_key: Clé SerpAPI
    
    Returns:
        Dict avec results, timestamp, mode
    """
    # Configuration selon le mode
    configs = {
        "fast": {
            "sources": 6,
            "results_per_source": 2,
            "delay": (0.5, 1.0)
        },
        "balanced": {
            "sources": 8,
            "results_per_source": 3,
            "delay": (0.8, 1.5)
        },
        "safe": {
            "sources": 10,
            "results_per_source": 3,
            "delay": (1.0, 2.0)
        }
    }
    
    config = configs.get(scan_mode, configs["balanced"])
    
    # Tri des sources par priorité
    sorted_sources = sorted(
        SOURCE_CONFIG.items(),
        key=lambda x: x[1].get('priority', 99)
    )[:config["sources"]]
    
    results = []
    
    # Scan source par source
    for domain, meta in sorted_sources:
        source_name = meta["label"]
        
        # Construction de la query Google
        query = f'"{brand}" site:{domain}'
        
        # Recherche via SerpAPI
        found = _serpapi_search(
            query, 
            max_results=config["results_per_source"], 
            api_key=api_key
        )
        
        # Ajout des résultats
        for item in found:
            results.append({
                "source": source_name,
                "domain_key": domain,
                "title": item['title'],
                "desc": item['description'],
                "url": item['url']
            })
        
        # Pause entre sources (courtoisie)
        delay = random.uniform(*config["delay"])
        time.sleep(delay)
    
    return {
        "results": results,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": scan_mode
    }

def _scan_with_ui(brand: str, status_container, log_container, scan_mode: str, api_key: str):
    """
    Wrapper UI : affiche l'animation pendant le scan
    
    Args:
        brand: Nom de la marque
        status_container: Container Streamlit pour la barre de progression
        log_container: Container pour les logs terminal
        scan_mode: Mode de scan
        api_key: Clé SerpAPI
    
    Returns:
        Liste des résultats
    """
    logs = []
    
    # Configuration visuelle selon le mode
    configs = {
        "fast": {"label": "⚡ RAPIDE", "eta": "~15s"},
        "balanced": {"label": "⚖️ ÉQUILIBRÉ", "eta": "~25s"},
        "safe": {"label": "🛡️ COMPLET", "eta": "~35s"}
    }
    
    config_ui = configs.get(scan_mode, configs["balanced"])
    
    # Liste des sources à scanner
    sorted_sources = sorted(
        SOURCE_CONFIG.items(),
        key=lambda x: x[1].get('priority', 99)
    )[:{"fast": 6, "balanced": 8, "safe": 10}.get(scan_mode, 8)]
    
    total = len(sorted_sources)
    progress_bar = status_container.progress(
        0, 
        text=f"Initialisation // Mode {config_ui['label']} (ETA: {config_ui['eta']})..."
    )
    
    # Animation visuelle pendant le scan
    for i, (domain, meta) in enumerate(sorted_sources):
        source_name = meta["label"]
        
        # Mise à jour de la barre
        progress_bar.progress(
            i / total, 
            text=f"Scan : {source_name}... [{i+1}/{total}]"
        )
        
        # Ajout du log
        log_html = f"<span style='color:#10b981'>[●]</span> Interrogation de {source_name}..."
        logs.append(log_html)
        
        # Affichage du terminal (dernières 8 lignes)
        log_display = "<br>".join(logs[-8:])
        log_container.markdown(
            f"""
            <div style="background:#0f172a; color:#cbd5e1; padding:16px; border-radius:8px; 
                        font-family:'Courier New'; font-size:0.85rem; line-height:1.6; 
                        border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                <div style="border-bottom:1px solid #334155; padding-bottom:8px; margin-bottom:8px; 
                            color:#94a3b8; font-weight:700; letter-spacing:0.05em;">
                    > HOTARU_SCAN_PROTOCOL // V3.5_SERPAPI // {config_ui['label']}
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
    
    # Lancement du scan réel (avec cache)
    scan_data = _cached_scan(brand, scan_mode, api_key)
    
    # Logs finaux avec résultats
    logs = []
    results_by_source = {}
    for r in scan_data["results"]:
        results_by_source.setdefault(r['source'], 0)
        results_by_source[r['source']] += 1
    
    for domain, meta in sorted_sources:
        source_name = meta["label"]
        count = results_by_source.get(source_name, 0)
        
        if count > 0:
            log_html = f"<span style='color:#10b981'>[✓]</span> {count} mentions sur {source_name}"
        else:
            log_html = f"<span style='color:#64748b'>[○]</span> Aucune donnée sur {source_name}"
        logs.append(log_html)
    
    # Affichage final
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
                ✓ {len(scan_data['results'])} mentions extraites via SerpAPI
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    progress_bar.progress(1.0, text="✓ Scan terminé avec succès")
    time.sleep(1.5)
    status_container.empty()
    
    return scan_data["results"]

def render_off_page_audit():
    """
    Interface principale du module Off-Page
    Récupère automatiquement la clé depuis Streamlit Secrets
    """
    st.markdown('<p class="section-title">01 / AUDIT DE RÉPUTATION (OFF-PAGE)</p>', unsafe_allow_html=True)
    
    # ✅ DIAGNOSTIC + LECTURE DE LA CLÉ
    api_key = None
    
    # Debug : afficher les clés disponibles
    with st.expander("🔍 Diagnostic Secrets (DEBUG)", expanded=False):
        st.write("**Clés disponibles dans st.secrets:**", list(st.secrets.keys()))
        st.write("**SERPAPI_KEY présente?**", "SERPAPI_KEY" in st.secrets)
        
        # Test toutes les variantes possibles
        possible_keys = [
            ("SERPAPI_KEY", lambda: st.secrets["SERPAPI_KEY"]),
            ("serpapi.SERPAPI_KEY", lambda: st.secrets["serpapi"]["SERPAPI_KEY"]),
            ("serpapi_key", lambda: st.secrets.get("serpapi_key")),
            ("SERP_API_KEY", lambda: st.secrets.get("SERP_API_KEY"))
        ]
        
        for key_name, getter in possible_keys:
            try:
                test_val = getter()
                if test_val:
                    st.success(f"✅ Trouvé via: `{key_name}` = {test_val[:10]}...")
                    if not api_key:  # Prendre la première qui marche
                        api_key = test_val
            except:
                st.info(f"❌ Pas trouvé via: `{key_name}`")
    
    # Lecture de la clé (méthode principale)
    if not api_key:
        try:
            api_key = st.secrets["SERPAPI_KEY"]
        except:
            try:
                api_key = st.secrets["serpapi"]["SERPAPI_KEY"]
            except:
                pass
    
    # Si toujours pas de clé
    if not api_key:
        st.error(
            """
            ❌ **Clé API SerpAPI introuvable**
            
            **Dans Settings → Secrets, assure-toi d'avoir exactement :**
```toml
            SERPAPI_KEY = "ta_clé_ici"
```
            
            **OU si tu as une section [serpapi] :**
```toml
            [serpapi]
            SERPAPI_KEY = "ta_clé_ici"
```
            
            📌 [Obtenir une clé gratuite (100 requêtes/mois)](https://serpapi.com/users/sign_up)
            """
        )
        return
    
    # Confirmation visuelle
    st.markdown(
        f'<p style="font-size:0.75rem;color:#10b981;font-weight:600;margin-bottom:16px;">'
        f'✓ Clé SerpAPI configurée ({api_key[:8]}...)</p>', 
        unsafe_allow_html=True
    )
    
    # --- INTERFACE DE SCAN ---
    col1, col2, col3 = st.columns([3, 1, 1])
    
    brand_input = col1.text_input(
        "Marque", 
        value="", 
        placeholder="Ex: Tesla, Nike, Apple...",
        label_visibility="collapsed"
    )
    
    scan_mode = col2.selectbox(
        "Mode",
        options=["balanced", "safe", "fast"],
        format_func=lambda x: {
            "fast": "⚡ Rapide", 
            "balanced": "⚖️ Équilibré", 
            "safe": "🛡️ Complet"
        }[x],
        label_visibility="collapsed",
        index=0
    )
    
    # Initialisation session state
    if 'offpage_results' not in st.session_state:
        st.session_state['offpage_results'] = []
    
    # Bouton de scan
    scan_button = col3.button("SCANNER", type="primary", use_container_width=True)
    
    if scan_button:
        if not brand_input:
            st.warning("⚠️ Nom de marque requis")
        else:
            # Conteneurs pour l'animation
            status_box = st.empty()
            log_box = st.empty()
            
            # Lancement du scan
            results = _scan_with_ui(brand_input, status_box, log_box, scan_mode, api_key)
            
            # Stockage des résultats
            st.session_state['offpage_results'] = results
            st.session_state['offpage_brand'] = brand_input
            st.session_state['offpage_mode'] = scan_mode
            
            # Feedback utilisateur
            if results:
                st.success(f"✓ {len(results)} mentions trouvées • Données en cache pour 1h")
            else:
                st.info("Aucune mention trouvée pour cette marque.")
    
    # --- AFFICHAGE DES RÉSULTATS ---
    results = st.session_state.get('offpage_results', [])
    brand_name = st.session_state.get('offpage_brand', brand_input)
    
    if results:
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Mentions", len(results))
        k2.metric("Sources", len(set(r['source'] for r in results)))
        k3.metric("API", "SerpAPI", delta="✓ Actif")
        k4.metric("Cache", "1h")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabs de visualisation
        tab_graph, tab_list, tab_export = st.tabs(["📊 GRAPHE", "📋 LISTE", "💾 EXPORT"])
        
        # TAB 1 : Graphe interactif
        with tab_graph:
            if brand_name:
                G = build_reputation_graph(brand_name, results)
                render_interactive_graph(G)
        
        # TAB 2 : Liste des mentions
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
        
        # TAB 3 : Export JSON
        with tab_export:
            export_data = {
                "brand": brand_name,
                "scan_mode": st.session_state.get('offpage_mode', 'balanced'),
                "total_mentions": len(results),
                "sources_count": len(set(r['source'] for r in results)),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mentions": results
            }
            
            json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="📥 Télécharger JSON",
                data=json_data,
                file_name=f"hotaru_offpage_{brand_name.lower().replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True
            )
            
            st.markdown(
                f"""
                <div style="margin-top:16px; padding:12px; background:#f1f5f9; border-radius:4px; font-size:0.8rem;">
                    <strong>📊 Statistiques d'export :</strong><br>
                    • Format : JSON structuré<br>
                    • Taille : {len(json_data)} caractères<br>
                    • Mode scan : {st.session_state.get('offpage_mode', 'balanced').upper()}<br>
                    • Date : {datetime.now().strftime("%d/%m/%Y %H:%M")}
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # --- OPTIONS AVANCÉES ---
    with st.expander("🔧 Options avancées"):
        col_a, col_b = st.columns(2)
        
        if col_a.button("🗑️ Vider le cache", use_container_width=True):
            _cached_scan.clear()
            st.session_state['offpage_results'] = []
            st.success("✓ Cache vidé. Prochain scan sera complet.")
        
        if col_b.button("📊 Statistiques API", use_container_width=True):
            st.info(
                "**SerpAPI - Plan Gratuit :**\n\n"
                "• 100 requêtes/mois\n"
                "• Pas de carte bancaire requise\n"
                "• Résultats instantanés\n"
                "• Pas de CAPTCHA"
            )