"""
HOTARU - Module Off-Page Reputation (V3.3 - Debug Edition)
Version avec logs détaillés pour diagnostiquer les blocages Google
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

def _safe_google_search_debug(query: str, max_results: int = 3, debug_container=None) -> List[Dict]:
    """
    VERSION DEBUG - Affiche tous les détails du processus
    
    Args:
        query: Requête Google
        max_results: Nombre max de résultats
        debug_container: Container Streamlit pour afficher les logs
    """
    results = []
    
    # Conteneur pour les logs si non fourni
    if debug_container is None:
        debug_container = st.expander("🔍 Logs de Debug", expanded=True)
    
    with debug_container:
        st.markdown(f"**🎯 Query lancée :** `{query}`")
        st.markdown(f"**⏱️ Timeout :** 20 secondes")
        st.markdown(f"**💤 Sleep interval :** 4.0 secondes")
        st.markdown("---")
        
        try:
            start_time = time.time()
            
            # Tentative de recherche
            st.markdown("🔄 **Initialisation de la recherche Google...**")
            
            search_gen = search(
                query,
                num_results=max_results,
                advanced=True,
                sleep_interval=4.0,
                timeout=20  # ✅ Timeout augmenté
            )
            
            st.markdown("✅ **Générateur créé. Extraction des résultats...**")
            
            # Extraction des résultats
            for idx, res in enumerate(search_gen):
                result_time = time.time() - start_time
                
                st.markdown(
                    f"""
                    <div style="background:#f0fdf4; border-left:3px solid #10b981; padding:8px; margin:8px 0; border-radius:4px;">
                        <strong>✓ Résultat {idx+1}</strong> (après {result_time:.1f}s)<br>
                        <span style="font-size:0.85rem; color:#059669;">📄 Titre: {res.title or 'N/A'}</span><br>
                        <span style="font-size:0.75rem; color:#64748b; font-family:monospace;">🔗 URL: {res.url}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                results.append({
                    "title": res.title or "Sans titre",
                    "description": res.description or "",
                    "url": res.url
                })
                
                if len(results) >= max_results:
                    st.markdown(f"🎯 **Limite atteinte** ({max_results} résultats)")
                    break
            
            total_time = time.time() - start_time
            
            # Résumé final
            if results:
                st.success(f"✅ **{len(results)} résultat(s) trouvé(s)** en {total_time:.1f}s")
            else:
                st.warning("⚠️ **Aucun résultat retourné** (peut être un blocage Google)")
                    
        except Exception as e:
            error_time = time.time() - start_time
            st.error(
                f"""
                ❌ **Erreur après {error_time:.1f}s**
                
                **Type:** `{type(e).__name__}`
                
                **Message:** {str(e)}
                
                **Causes possibles:**
                - Google détecte un bot et bloque
                - Timeout dépassé (réseau lent)
                - CAPTCHA invisible demandé
                - Rate limit atteint
                """
            )
    
    return results

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_scan_debug(brand: str, scan_mode: str, enable_debug: bool = False) -> Dict:
    """
    Scanner AVEC CACHE et mode debug optionnel
    
    Args:
        brand: Nom de la marque
        scan_mode: Mode de scan (safe/balanced/fast)
        enable_debug: Active les logs détaillés
    """
    # Configuration selon mode
    configs = {
        "fast": {
            "sources": 6,
            "results_per_source": 2,
            "between_sources": (3.0, 5.0)
        },
        "balanced": {
            "sources": 8,
            "results_per_source": 3,
            "between_sources": (4.0, 7.0)
        },
        "safe": {
            "sources": 10,
            "results_per_source": 3,
            "between_sources": (5.0, 9.0)
        }
    }
    
    config = configs.get(scan_mode, configs["safe"])
    
    # Tri par priorité
    sorted_sources = sorted(
        SOURCE_CONFIG.items(),
        key=lambda x: x[1].get('priority', 99)
    )[:config["sources"]]
    
    results = []
    
    # Conteneur de debug global
    if enable_debug:
        debug_master = st.container()
    
    for domain, meta in sorted_sources:
        source_name = meta["label"]
        
        # Query Google
        query = f'"{brand}" site:{domain}'
        
        if enable_debug:
            with debug_master:
                st.markdown(f"### 🔍 Scan de {source_name}")
            
            found = _safe_google_search_debug(
                query, 
                max_results=config["results_per_source"],
                debug_container=debug_master
            )
        else:
            # Mode silencieux (version originale sans logs)
            found = []
            try:
                search_gen = search(
                    query,
                    num_results=config["results_per_source"],
                    advanced=True,
                    sleep_interval=4.0,
                    timeout=20
                )
                
                for res in search_gen:
                    found.append({
                        "title": res.title or "Sans titre",
                        "description": res.description or "",
                        "url": res.url
                    })
                    
                    if len(found) >= config["results_per_source"]:
                        break
            except:
                pass
        
        # Traitement résultats
        for item in found:
            results.append({
                "source": source_name,
                "domain_key": domain,
                "title": item['title'],
                "desc": item['description'],
                "url": item['url']
            })
        
        # PAUSE entre sources
        delay = random.uniform(*config["between_sources"])
        if enable_debug:
            with debug_master:
                st.info(f"⏸️ Pause de {delay:.1f}s avant la prochaine source...")
        time.sleep(delay)
    
    return {
        "results": results,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": scan_mode
    }

def _scan_with_ui(brand: str, status_container, log_container, scan_mode: str = "safe", debug_mode: bool = False):
    """
    Wrapper UI pour le scan caché
    """
    logs = []
    
    # Configuration visuelle
    configs = {
        "fast": {"label": "⚡ RAPIDE", "eta": "~45s"},
        "balanced": {"label": "⚖️ ÉQUILIBRÉ", "eta": "~1m30s"},
        "safe": {"label": "🛡️ SÉCURISÉ", "eta": "~2m30s"}
    }
    
    config_ui = configs.get(scan_mode, configs["safe"])
    
    # Tri sources
    sorted_sources = sorted(
        SOURCE_CONFIG.items(),
        key=lambda x: x[1].get('priority', 99)
    )[:{"fast": 6, "balanced": 8, "safe": 10}.get(scan_mode, 10)]
    
    total = len(sorted_sources)
    progress_bar = status_container.progress(0, text=f"Initialisation // Mode {config_ui['label']} (ETA: {config_ui['eta']})...")
    
    if not debug_mode:
        # Animation normale
        for i, (domain, meta) in enumerate(sorted_sources):
            source_name = meta["label"]
            
            progress_bar.progress(i / total, text=f"Scan : {source_name}... [{i+1}/{total}]")
            
            log_html = f"<span style='color:#64748b'>[●]</span> Interrogation de {source_name}..."
            logs.append(log_html)
            
            log_display = "<br>".join(logs[-8:])
            log_container.markdown(
                f"""
                <div style="background:#0f172a; color:#cbd5e1; padding:16px; border-radius:8px; 
                            font-family:'Courier New'; font-size:0.85rem; line-height:1.6; 
                            border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                    <div style="border-bottom:1px solid #334155; padding-bottom:8px; margin-bottom:8px; 
                                color:#94a3b8; font-weight:700; letter-spacing:0.05em;">
                        > HOTARU_SCAN_PROTOCOL // V3.3_DEBUG // {config_ui['label']}
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
            
            time.sleep(0.3)
    
    # Appel du scan (avec ou sans debug)
    scan_data = _cached_scan_debug(brand, scan_mode, enable_debug=debug_mode)
    
    if not debug_mode:
        # Logs finaux
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
        
        progress_bar.progress(1.0, text="✓ Scan terminé avec succès")
        time.sleep(1.5)
        status_container.empty()
    
    return scan_data["results"]

def render_off_page_audit():
    """Interface principale avec mode debug"""
    st.markdown('<p class="section-title">01 / AUDIT DE RÉPUTATION (OFF-PAGE)</p>', unsafe_allow_html=True)
    
    if not HAS_GOOGLESEARCH:
        st.error("❌ Module `googlesearch-python` requis.")
        st.code("pip install googlesearch-python", language="bash")
        return
    
    # Info
    st.markdown(
        '<p style="font-size:0.75rem;color:#94a3b8;font-style:italic;margin-bottom:16px;">'
        '🛡️ Scan ultra-sécurisé avec cache intelligent (1h). Active le mode DEBUG pour diagnostiquer les problèmes.</p>', 
        unsafe_allow_html=True
    )
    
    # Input zone
    col1, col2, col3, col4 = st.columns([2.5, 1, 1, 0.5])
    
    brand_input = col1.text_input(
        "Marque", 
        value="", 
        placeholder="Ex: Tesla",
        label_visibility="collapsed"
    )
    
    scan_mode = col2.selectbox(
        "Mode",
        options=["safe", "balanced", "fast"],
        format_func=lambda x: {"fast": "⚡ Rapide", "balanced": "⚖️ Équilibré", "safe": "🛡️ Sûr"}[x],
        label_visibility="collapsed",
        index=0
    )
    
    # ✅ NOUVEAU : Toggle Debug
    debug_mode = col4.checkbox("🐛", help="Active les logs détaillés pour diagnostiquer les problèmes")
    
    # Session state
    if 'offpage_results' not in st.session_state:
        st.session_state['offpage_results'] = []
    
    # Action
    scan_button = col3.button("SCANNER", type="primary", use_container_width=True)
    
    if scan_button:
        if not brand_input:
            st.warning("⚠️ Nom de marque requis")
        else:
            if debug_mode:
                st.info("🐛 **Mode DEBUG activé** - Les logs détaillés s'afficheront ci-dessous")
            
            status_box = st.empty()
            log_box = st.empty()
            
            # Scan avec ou sans debug
            results = _scan_with_ui(brand_input, status_box, log_box, scan_mode, debug_mode)
            
            st.session_state['offpage_results'] = results
            st.session_state['offpage_brand'] = brand_input
            st.session_state['offpage_mode'] = scan_mode
            
            # Message de succès
            if results:
                st.success(f"✓ {len(results)} mentions trouvées • Données en cache pour 1h")
            else:
                st.warning(
                    "⚠️ **Aucune mention trouvée**\n\n"
                    "**Solutions :**\n"
                    "- Active le mode 🐛 DEBUG pour voir les détails\n"
                    "- Essaye une autre marque (ex: 'Nike', 'Apple')\n"
                    "- Attends 5-10 minutes (Google peut bloquer temporairement)\n"
                    "- Vérifie ta connexion internet"
                )
    
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
    
    # Options avancées
    with st.expander("⚙️ Options avancées"):
        col_a, col_b = st.columns(2)
        
        if col_a.button("🗑️ Vider le cache", help="Force un nouveau scan"):
            _cached_scan_debug.clear()
            st.session_state['offpage_results'] = []
            st.success("Cache vidé.")
        
        if col_b.button("📋 Tester une requête", help="Test rapide d'une source"):
            if brand_input:
                test_query = f'"{brand_input}" site:reddit.com'
                st.code(test_query, language="text")
                
                with st.spinner("Test en cours..."):
                    test_results = _safe_google_search_debug(test_query, max_results=2)
                
                if test_results:
                    st.success(f"✅ {len(test_results)} résultats trouvés")
                else:
                    st.error("❌ Aucun résultat (blocage probable)")
            else:
                st.warning("Entrez une marque d'abord")