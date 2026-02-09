"""
HOTARU - Module Off-Page Reputation (V3.2 - Zero-Ban Edition)
Scan optimisé avec cache intelligent et protection anti-détection maximale.
"""

import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import json
import time
import random
from typing import List, Dict
from datetime import datetime

# Import avec fallback
try:
    from googlesearch import search
    HAS_GOOGLESEARCH = True
except ImportError:
    HAS_GOOGLESEARCH = False

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
    """Graphe Pyvis optimisé"""
    nt = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#0f172a")
    nt.from_nx(G)
    
    opts = {
        "nodes": {
            "font": {"face": "Inter", "size": 14, "strokeWidth": 3, "strokeColor": "#fff", "color": "#0f172a"},
            "borderWidth": 2
        },
        "edges": {"color": "#cbd5e1", "width": 1.5, "smooth": {"type": "dynamic", "roundness": 0.2}},
        "interaction": {"hover": True, "navigationButtons": True, "zoomView": True},
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
    """Construction du graphe en étoile"""
    G = nx.DiGraph()
    
    # Nœud central
    G.add_node(
        brand, 
        label=brand.upper(), 
        size=45, 
        color="#0f172a",
        font={'color': '#ffffff', 'size': 20},
        title="MARQUE CIBLE"
    )
    
    # Nœuds satellites
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

def _safe_google_search(query: str, max_results: int = 3) -> List[Dict]:
    """
    Recherche Google avec protection anti-ban MAXIMALE
    
    TIMING CRITIQUE:
    - sleep_interval=4.0 : délai ENTRE chaque résultat (mode safe)
    - Pause aléatoire après chaque appel : 3-6 sec
    """
    results = []
    
    try:
        # Paramètres ultra-conservateurs
        search_gen = search(
            query,
            num_results=max_results,
            advanced=True,
            sleep_interval=4.0,  # ✅ 4 SECONDES (mode safe)
            timeout=15
        )
        
        for res in search_gen:
            results.append({
                "title": res.title or "Sans titre",
                "description": res.description or "",
                "url": res.url
            })
            
            # Sécurité supplémentaire
            if len(results) >= max_results:
                break
                
    except Exception as e:
        # Log silencieux, pas de crash
        pass
    
    return results

@st.cache_data(ttl=3600, show_spinner=False)  # ✅ Cache 1 heure
def _cached_scan(brand: str, scan_mode: str) -> Dict:
    """
    Scanner AVEC CACHE - évite les scans répétés
    
    Returns:
        Dict avec 'results', 'timestamp', 'mode'
    """
    # Configuration selon mode
    configs = {
        "fast": {
            "sources": 6,
            "results_per_source": 2,
            "base_delay": (2.0, 3.5),
            "between_sources": (3.0, 5.0)
        },
        "balanced": {
            "sources": 8,
            "results_per_source": 3,
            "base_delay": (2.5, 4.0),
            "between_sources": (4.0, 7.0)
        },
        "safe": {  # ✅ MODE PAR DÉFAUT
            "sources": 10,
            "results_per_source": 3,
            "base_delay": (3.0, 5.0),
            "between_sources": (5.0, 9.0)  # Pauses longues
        }
    }
    
    config = configs.get(scan_mode, configs["safe"])
    
    # Tri par priorité
    sorted_sources = sorted(
        SOURCE_CONFIG.items(),
        key=lambda x: x[1].get('priority', 99)
    )[:config["sources"]]
    
    results = []
    
    for domain, meta in sorted_sources:
        source_name = meta["label"]
        
        # Query Google
        query = f'"{brand}" site:{domain}'
        found = _safe_google_search(query, max_results=config["results_per_source"])
        
        # Traitement résultats
        for item in found:
            results.append({
                "source": source_name,
                "domain_key": domain,
                "title": item['title'],
                "desc": item['description'],
                "url": item['url']
            })
        
        # PAUSE CRITIQUE entre sources
        delay = random.uniform(*config["between_sources"])
        time.sleep(delay)
    
    return {
        "results": results,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": scan_mode
    }

def _scan_with_ui(brand: str, status_container, log_container, scan_mode: str = "safe"):
    """
    Wrapper UI pour le scan caché
    Affiche l'animation pendant que le cache travaille
    """
    logs = []
    
    # Configuration visuelle
    configs = {
        "fast": {"label": "⚡ RAPIDE", "eta": "~45s"},
        "balanced": {"label": "⚖️ ÉQUILIBRÉ", "eta": "~1m30s"},
        "safe": {"label": "🛡️ SÉCURISÉ", "eta": "~2m30s"}
    }
    
    config_ui = configs.get(scan_mode, configs["safe"])
    
    # Tri sources (même logique que _cached_scan)
    sorted_sources = sorted(
        SOURCE_CONFIG.items(),
        key=lambda x: x[1].get('priority', 99)
    )[:{"fast": 6, "balanced": 8, "safe": 10}.get(scan_mode, 10)]
    
    total = len(sorted_sources)
    progress_bar = status_container.progress(0, text=f"Initialisation // Mode {config_ui['label']} (ETA: {config_ui['eta']})...")
    
    # Simulation visuelle pendant le scan
    for i, (domain, meta) in enumerate(sorted_sources):
        source_name = meta["label"]
        
        # Mise à jour UI
        progress_bar.progress(i / total, text=f"Scan : {source_name}... [{i+1}/{total}]")
        
        # Log visuel (simulation)
        log_html = f"<span style='color:#64748b'>[●]</span> Interrogation de {source_name}..."
        logs.append(log_html)
        
        # Affichage terminal
        log_display = "<br>".join(logs[-8:])
        log_container.markdown(
            f"""
            <div style="background:#0f172a; color:#cbd5e1; padding:16px; border-radius:8px; 
                        font-family:'Courier New'; font-size:0.85rem; line-height:1.6; 
                        border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                <div style="border-bottom:1px solid #334155; padding-bottom:8px; margin-bottom:8px; 
                            color:#94a3b8; font-weight:700; letter-spacing:0.05em;">
                    > HOTARU_SCAN_PROTOCOL // V3.2_ZERO_BAN // {config_ui['label']}
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
        
        # Pause visuelle (rapide, juste pour l'effet)
        time.sleep(0.3)
    
    # Appel du scan caché (avec cache)
    scan_data = _cached_scan(brand, scan_mode)
    
    # Mise à jour finale des logs avec vrais résultats
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
                ✓ {len(scan_data['results'])} mentions extraites
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Fin
    progress_bar.progress(1.0, text="✓ Scan terminé avec succès")
    time.sleep(1.5)
    status_container.empty()
    
    return scan_data["results"]

def render_off_page_audit():
    """Interface principale avec cache intégré"""
    st.markdown('<p class="section-title">01 / AUDIT DE RÉPUTATION (OFF-PAGE)</p>', unsafe_allow_html=True)
    
    # Warning si module manquant
    if not HAS_GOOGLESEARCH:
        st.error("❌ Module `googlesearch-python` requis. Installez avec : `pip install googlesearch-python`")
        st.code("pip install googlesearch-python", language="bash")
        return
    
    # Info cache
    st.markdown(
        '<p style="font-size:0.75rem;color:#94a3b8;font-style:italic;margin-bottom:16px;">'
        '🛡️ Scan ultra-sécurisé avec cache intelligent (1h). Les scans répétés utilisent les données en cache.</p>', 
        unsafe_allow_html=True
    )
    
    # Input zone
    col1, col2, col3 = st.columns([3, 1, 1])
    
    brand_input = col1.text_input(
        "Marque", 
        value="", 
        placeholder="Ex: Tesla",
        label_visibility="collapsed"
    )
    
    scan_mode = col2.selectbox(
        "Mode",
        options=["safe", "balanced", "fast"],  # ✅ Safe en premier (défaut)
        format_func=lambda x: {"fast": "⚡ Rapide", "balanced": "⚖️ Équilibré", "safe": "🛡️ Sûr"}[x],
        label_visibility="collapsed",
        index=0  # ✅ Safe par défaut
    )
    
    # Session state
    if 'offpage_results' not in st.session_state:
        st.session_state['offpage_results'] = []
        st.session_state['offpage_cached'] = False
    
    # Action
    scan_button = col3.button("SCANNER", type="primary", use_container_width=True)
    
    if scan_button:
        if not brand_input:
            st.warning("⚠️ Nom de marque requis")
        else:
            status_box = st.empty()
            log_box = st.empty()
            
            # Vérification cache
            cache_key = f"{brand_input}_{scan_mode}"
            
            # Scan avec UI
            results = _scan_with_ui(brand_input, status_box, log_box, scan_mode)
            
            st.session_state['offpage_results'] = results
            st.session_state['offpage_brand'] = brand_input
            st.session_state['offpage_mode'] = scan_mode
            
            # Message de succès
            if results:
                st.success(f"✓ {len(results)} mentions trouvées • Données en cache pour 1h")
            else:
                st.info("Aucune mention trouvée. Essayez le mode 'Sûr' ou attendez quelques minutes avant de rescanner.")
    
    # RÉSULTATS
    results = st.session_state.get('offpage_results', [])
    brand_name = st.session_state.get('offpage_brand', brand_input)
    
    if results:
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Mentions", len(results))
        k2.metric("Sources", len(set(r['source'] for r in results)))
        k3.metric("Mode", {"fast": "⚡", "balanced": "⚖️", "safe": "🛡️"}.get(st.session_state.get('offpage_mode', 'safe'), '🛡️'))
        k4.metric("Cache", "✓ Actif", delta="1h")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabs
        tab_graph, tab_list, tab_export = st.tabs(["📊 GRAPHE", "📋 LISTE", "💾 EXPORT"])
        
        with tab_graph:
            if brand_name:
                G = build_reputation_graph(brand_name, results)
                render_interactive_graph(G)
        
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
            # Export JSON
            export_data = {
                "brand": brand_name,
                "scan_mode": st.session_state.get('offpage_mode', 'safe'),
                "total_mentions": len(results),
                "sources_count": len(set(r['source'] for r in results)),
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
                    • Mode scan : {st.session_state.get('offpage_mode', 'safe').upper()}
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Bouton reset cache (admin)
    with st.expander("⚙️ Options avancées"):
        if st.button("🗑️ Vider le cache", help="Force un nouveau scan même si des données sont en cache"):
            _cached_scan.clear()
            st.session_state['offpage_results'] = []
            st.success("Cache vidé. Le prochain scan sera complet.")