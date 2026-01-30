"""
HOTARU - Audit GEO Module
Interface principale avec graphe hiérarchique propre.

ÉTAPES DE RÉPARATION APPLIQUÉES:
1. Graphe hiérarchique (direction: UD - Up to Down)
2. Maximum 20-30 noeuds parents
3. Labels lisibles extraits des URLs
4. Progress bar et logs visibles
"""

import streamlit as st
from datetime import datetime
from typing import List, Dict
from urllib.parse import urlparse
from collections import Counter
import re


def render_audit_geo():
    """Page principale Audit GEO."""
    init_session_state()

    st.markdown("## 🔍 Audit GEO")
    st.caption("Analyse structurelle et SEO de votre site")

    # Input URL
    col1, col2 = st.columns([4, 1])
    with col1:
        url = st.text_input(
            "URL",
            placeholder="https://exemple.com",
            key="audit_url_input",
            label_visibility="collapsed"
        )
    with col2:
        analyze_btn = st.button("Analyser", use_container_width=True)

    if analyze_btn and url:
        run_audit(url)

    # Résultats
    if st.session_state.audit_results:
        render_results()


def init_session_state():
    """Initialise les variables de session."""
    defaults = {
        'audit_results': None,
        'audit_running': False,
        'ai_optimized': False,
        'ai_graph_data': None,
        'clustered_data': None,
        'patterns_summary': [],
        'mistral_api_key': ''
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_results():
    """Affiche les résultats avec boutons d'action."""
    results = st.session_state.audit_results

    # Boutons d'action
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.session_state.ai_optimized:
            if st.button("↩️ Vue standard", use_container_width=True):
                st.session_state.ai_optimized = False
                st.rerun()
        else:
            if st.button("✨ Optimiser IA", use_container_width=True):
                run_ai_optimization()

    with col2:
        if st.button("🔄 Nouvel audit", use_container_width=True):
            st.session_state.audit_results = None
            st.session_state.ai_optimized = False
            st.session_state.clustered_data = None
            st.rerun()

    with col3:
        pages = results.get('pages', [])
        if pages:
            avg = sum(p.get('score', 0) for p in pages) / len(pages)
            st.metric("Score", f"{avg:.0f}/100")

    st.markdown("---")

    # Titre du graphe
    if st.session_state.ai_optimized:
        st.markdown("### 🧠 Structure IA")
        graph_data = st.session_state.ai_graph_data
    else:
        st.markdown("### 📊 Structure du site")
        graph_data = st.session_state.clustered_data

    # Rendu du graphe
    render_graph(graph_data)

    # Stats
    render_stats()


def render_graph(data: Dict):
    """Rendu du graphe hiérarchique."""
    if not data or not data.get('nodes'):
        st.info("Lancez une analyse pour voir le graphe")
        return

    try:
        from streamlit_agraph import agraph, Node, Edge, Config

        nodes = []
        edges = []

        for n in data['nodes']:
            ntype = n.get('type', 'page')

            # Style selon le type
            if ntype == 'root':
                size, color = 45, "#000000"
            elif ntype == 'cluster':
                size, color = 32, "#FFD700"
            else:
                score = n.get('score', 50)
                size = 18
                color = "#22C55E" if score >= 70 else "#F97316" if score >= 40 else "#EF4444"

            # Tooltip
            title = n.get('label', '')
            if n.get('count'):
                title += f" ({n['count']} pages)"
            if n.get('url'):
                title += f"\n🔗 Cliquer pour ouvrir"

            nodes.append(Node(
                id=n['id'],
                label=n.get('label', '')[:28],
                size=size,
                color="#FFFFFF",
                borderWidth=2,
                borderWidthSelected=4,
                shape="box",
                font={'color': '#000000', 'size': 11},
                title=title
            ))

        for e in data.get('edges', []):
            edges.append(Edge(
                source=e['source'],
                target=e['target'],
                color="#333333",
                width=1
            ))

        # Config hiérarchique
        config = Config(
            width="100%",
            height=450,
            directed=True,
            physics=False,
            hierarchical=True,
            nodeHighlightBehavior=True,
            highlightColor="#FFD700"
        )

        # Container avec bordure
        st.markdown("""
            <div style="border: 1px solid #000; padding: 0.5rem; background: #fff;">
        """, unsafe_allow_html=True)

        selected = agraph(nodes=nodes, edges=edges, config=config)

        st.markdown("</div>", unsafe_allow_html=True)

        # Gestion du clic
        if selected:
            for n in data['nodes']:
                if n['id'] == selected and n.get('url'):
                    st.link_button(f"🔗 Ouvrir {n.get('label', '')}", n['url'])
                    break

    except Exception as e:
        st.warning(f"Graphe indisponible: {e}")
        # Fallback texte
        st.markdown("#### Structure (texte)")
        for n in data.get('nodes', [])[:20]:
            if n.get('type') == 'root':
                st.markdown(f"**🌐 {n.get('label')}**")
            elif n.get('type') == 'cluster':
                st.markdown(f"├── 📁 {n.get('label')}")


def run_audit(url: str):
    """Lance l'audit avec feedback visuel."""
    # Containers pour feedback
    status_box = st.empty()
    progress_bar = st.progress(0)
    log_box = st.empty()

    logs = []

    def log(msg):
        logs.append(f"{datetime.now().strftime('%H:%M:%S')} {msg}")
        log_box.code('\n'.join(logs[-6:]))

    def progress(msg, val):
        status_box.info(f"⏳ {msg}")
        progress_bar.progress(min(val, 1.0))

    try:
        from core.scraping import SmartScraper

        log("🚀 Démarrage de l'analyse...")
        progress("Recherche sitemap...", 0.1)

        scraper = SmartScraper(
            base_url=url,
            max_urls=500,
            sample_size=50,
            specimens_per_pattern=3
        )

        results, stats = scraper.run_analysis(progress_callback=progress)

        log(f"📊 {stats.get('total_urls_found', 0)} URLs trouvées")
        log(f"🔍 {stats.get('patterns_detected', 0)} patterns détectés")

        progress("Calcul des scores...", 0.85)
        scored = calculate_scores(results)

        progress("Génération du graphe...", 0.95)
        graph_data = build_clean_graph(url, scored, scraper.get_pattern_summary())

        st.session_state.audit_results = {
            'url': url,
            'pages': scored,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }
        st.session_state.clustered_data = graph_data
        st.session_state.patterns_summary = scraper.get_pattern_summary()

        log("✅ Analyse terminée!")
        progress("Terminé!", 1.0)

        import time
        time.sleep(0.5)
        st.rerun()

    except Exception as e:
        log(f"❌ ERREUR: {e}")
        st.error(f"Erreur: {e}")


def build_clean_graph(site_url: str, pages: List[Dict], patterns: List[Dict]) -> Dict:
    """
    Construit un graphe propre avec MAX 25 noeuds.

    RÈGLE: Si un pattern a >5 pages, on crée UN SEUL noeud cluster.
    """
    nodes = []
    edges = []

    # Noeud racine
    parsed = urlparse(site_url)
    root_label = parsed.netloc.replace('www.', '')[:25]

    nodes.append({
        'id': 'root',
        'label': root_label,
        'type': 'root',
        'url': site_url
    })

    # Grouper par pattern
    by_pattern: Dict[str, List] = {}
    for p in pages:
        key = p.get('pattern_group') or 'divers'
        if key == 'unique':
            key = 'divers'
        if key not in by_pattern:
            by_pattern[key] = []
        by_pattern[key].append(p)

    # Créer les clusters (max 12)
    sorted_patterns = sorted(by_pattern.items(), key=lambda x: -len(x[1]))[:12]

    for idx, (pattern, pattern_pages) in enumerate(sorted_patterns):
        cluster_id = f"c{idx}"
        count = len(pattern_pages)

        # Nom du cluster = segment URL le plus fréquent
        label = get_cluster_label(pattern, pattern_pages)

        nodes.append({
            'id': cluster_id,
            'label': f"📁 {label} ({count})",
            'type': 'cluster',
            'count': count
        })

        edges.append({'source': 'root', 'target': cluster_id})

        # Si petit cluster (<=5), montrer les pages
        if count <= 5:
            for j, page in enumerate(pattern_pages):
                pid = f"p{idx}_{j}"
                plabel = get_page_label(page.get('path', ''))

                nodes.append({
                    'id': pid,
                    'label': plabel,
                    'type': 'page',
                    'url': page.get('url', ''),
                    'score': page.get('score', 50)
                })
                edges.append({'source': cluster_id, 'target': pid})

    return {
        'nodes': nodes,
        'edges': edges,
        'cluster_count': len(sorted_patterns)
    }


def get_cluster_label(pattern: str, pages: List[Dict]) -> str:
    """Extrait un nom lisible pour un cluster."""
    # Essayer depuis le pattern
    if pattern and pattern not in ('divers', 'other'):
        clean = pattern.replace('[^/]+', '').replace('/?$', '').replace('(', '').replace(')', '')
        parts = [p for p in clean.split('/') if p and len(p) > 2]
        if parts:
            return parts[0].replace('-', ' ').replace('_', ' ').title()[:18]

    # Sinon analyser les paths
    if pages:
        segments = []
        for p in pages[:15]:
            path = p.get('path', '')
            parts = [x for x in path.strip('/').split('/') if x and not x.isdigit() and len(x) > 2]
            if parts:
                segments.append(parts[0])

        if segments:
            common = Counter(segments).most_common(1)
            if common:
                return common[0][0].replace('-', ' ').replace('_', ' ').title()[:18]

    return "Pages"


def get_page_label(path: str) -> str:
    """Extrait un nom lisible depuis un path."""
    if not path or path == '/':
        return "Accueil"

    parts = [p for p in path.strip('/').split('/') if p]
    if not parts:
        return "Page"

    name = parts[-1]
    name = re.sub(r'\.(html?|php|aspx?)$', '', name)
    name = re.sub(r'\?.*$', '', name)
    name = re.sub(r'[-_]+', ' ', name)
    name = name.title()

    return name[:22] if name else "Page"


def run_ai_optimization():
    """Lance l'optimisation IA avec feedback."""
    if not st.session_state.get('mistral_api_key'):
        st.warning("⚠️ Configurez votre clé API Mistral dans la sidebar")
        return

    results = st.session_state.audit_results
    if not results:
        return

    # Feedback containers
    status = st.empty()
    progress = st.progress(0)
    log_container = st.container()

    logs = []

    def log(msg):
        logs.append(f"{datetime.now().strftime('%H:%M:%S')} {msg}")

    with log_container:
        st.markdown("##### 📋 Journal IA")
        log_display = st.empty()

    try:
        from core.ai_clustering import categorize_urls_with_ai, generate_smart_graph_data

        def ai_log(msg):
            log(msg)
            log_display.code('\n'.join(logs[-8:]))

        def ai_progress(msg, val):
            status.info(f"🤖 {msg}")
            progress.progress(min(val, 1.0))

        log("🚀 Démarrage optimisation IA...")
        ai_progress("Préparation...", 0.1)

        pages = results.get('pages', [])
        site_url = results.get('url', '')

        ai_result = categorize_urls_with_ai(
            pages,
            site_url,
            st.session_state.mistral_api_key,
            progress_callback=ai_progress,
            log_callback=ai_log
        )

        if ai_result:
            log("📊 Génération graphe optimisé...")
            graph = generate_smart_graph_data(ai_result, site_url, pages, None)

            st.session_state.ai_graph_data = graph
            st.session_state.ai_optimized = True

            log("✅ Optimisation terminée!")
            ai_progress("Terminé!", 1.0)

            import time
            time.sleep(0.5)
            st.rerun()
        else:
            log("❌ Échec - vérifiez votre clé API")
            st.error("Échec de l'optimisation")

    except Exception as e:
        log(f"❌ ERREUR: {e}")
        st.error(f"Erreur: {e}")


def calculate_scores(pages) -> List[Dict]:
    """Calcule les scores SEO."""
    scored = []

    for page in pages:
        # Support URLInfo ou dict
        if hasattr(page, 'url'):
            data = {
                'url': page.url,
                'path': page.path,
                'depth': page.depth,
                'cluster': page.cluster,
                'pattern_group': getattr(page, 'pattern_group', None),
                'is_specimen': getattr(page, 'is_specimen', True),
                'title': page.title,
                'meta_description': page.meta_description,
                'h1': page.h1,
                'word_count': page.word_count
            }
        else:
            data = page.copy()

        score = 0
        issues = []

        title = data.get('title')
        if title:
            score += 20 if 30 <= len(title) <= 60 else 10
        else:
            issues.append("Titre manquant")

        meta = data.get('meta_description')
        if meta:
            score += 20 if 120 <= len(meta) <= 160 else 10
        else:
            issues.append("Meta manquante")

        if data.get('h1'):
            score += 20
        else:
            issues.append("H1 manquant")

        wc = data.get('word_count', 0)
        if wc >= 300:
            score += 20
        elif wc >= 100:
            score += 10
        else:
            issues.append("Contenu faible")

        depth = data.get('depth', 5)
        if depth <= 3:
            score += 20
        elif depth <= 5:
            score += 10

        data['score'] = score
        data['issues'] = issues
        scored.append(data)

    return scored


def render_stats():
    """Affiche les statistiques."""
    results = st.session_state.audit_results
    if not results:
        return

    st.markdown("---")
    st.markdown("### 📈 Statistiques")

    stats = results.get('stats', {})
    pages = results.get('pages', [])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("URLs", stats.get('total_urls_found', 0))
    with col2:
        st.metric("Patterns", stats.get('patterns_detected', 0))
    with col3:
        st.metric("Analysées", stats.get('specimens_analyzed', 0))
    with col4:
        st.metric("Groupes", stats.get('clusters', 0))

    # Distribution scores
    good = len([p for p in pages if p.get('score', 0) >= 70])
    med = len([p for p in pages if 40 <= p.get('score', 0) < 70])
    bad = len([p for p in pages if p.get('score', 0) < 40])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"🟢 **Bon** ({good})")
    with col2:
        st.markdown(f"🟠 **Moyen** ({med})")
    with col3:
        st.markdown(f"🔴 **Faible** ({bad})")

    # Détails patterns
    if st.session_state.patterns_summary:
        with st.expander("📊 Détail patterns"):
            for p in st.session_state.patterns_summary[:10]:
                st.markdown(f"**{p['name']}**: {p['count']} pages")
