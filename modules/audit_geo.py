"""
HOTARU - Audit GEO Module
Main audit interface with hierarchical graph visualization.

Features:
- Clean organigramme-style graph (max 30 nodes)
- Progress bar during AI processing
- Aggressive clustering for large sites
"""

import streamlit as st
from datetime import datetime
from typing import List, Dict
from urllib.parse import urlparse
import re


def render_audit_geo():
    """Render the Audit GEO page."""
    init_session_state()

    # Header
    st.markdown("## 🔍 Audit GEO")
    st.caption("Analyse structurelle et SEO de votre site")

    # URL Input
    render_url_input()

    # Results
    if st.session_state.audit_results:
        render_results_section()


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        'audit_results': None,
        'audit_running': False,
        'ai_optimized': False,
        'ai_graph_data': None,
        'mistral_api_key': '',
        'ai_logs': [],
        'patterns_summary': [],
        'clustered_data': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_url_input():
    """Render URL input section."""
    col1, col2 = st.columns([4, 1])

    with col1:
        url = st.text_input(
            "URL du site",
            placeholder="https://exemple.com",
            key="audit_url_input",
            label_visibility="collapsed"
        )

    with col2:
        if st.button("Analyser", use_container_width=True, disabled=st.session_state.audit_running):
            if url:
                run_audit(url)
            else:
                st.warning("Entrez une URL")


def render_results_section():
    """Render results with action buttons and graph."""
    results = st.session_state.audit_results

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.session_state.ai_optimized:
            if st.button("↩️ Vue standard", use_container_width=True):
                st.session_state.ai_optimized = False
                st.session_state.ai_graph_data = None
                st.rerun()
        else:
            if st.button("✨ Optimiser avec IA", use_container_width=True):
                run_ai_optimization()

    with col2:
        if st.button("🔄 Nouvel audit", use_container_width=True):
            reset_audit()
            st.rerun()

    with col3:
        pages = results.get('pages', [])
        avg_score = sum(p.get('score', 0) for p in pages) / len(pages) if pages else 0
        st.metric("Score moyen", f"{avg_score:.0f}/100")

    st.markdown("---")

    # Graph section
    if st.session_state.ai_optimized and st.session_state.ai_graph_data:
        st.markdown("### 🧠 Structure optimisee par IA")
        render_hierarchical_graph(st.session_state.ai_graph_data)
    else:
        st.markdown("### 📊 Structure du site")
        render_hierarchical_graph(st.session_state.clustered_data)

    # Stats
    render_stats()


def render_hierarchical_graph(graph_data: Dict):
    """Render a clean hierarchical graph using streamlit-agraph."""
    if not graph_data:
        st.info("Aucune donnee de graphe disponible")
        return

    try:
        from streamlit_agraph import agraph, Node, Edge, Config

        nodes = []
        edges = []

        # Build nodes
        for n in graph_data.get('nodes', []):
            node_type = n.get('type', 'page')

            # Determine size and color based on type
            if node_type == 'root':
                size = 50
                border_color = "#000000"
                shape = "box"
            elif node_type == 'cluster':
                size = 35
                border_color = "#FFD700"
                shape = "box"
            else:
                size = 20
                score = n.get('score', 50)
                border_color = "#22C55E" if score >= 70 else "#F97316" if score >= 40 else "#EF4444"
                shape = "box"

            # Create tooltip
            title = n.get('label', '')
            if n.get('url'):
                title += f"\n🔗 {n.get('url')}"
            if n.get('count'):
                title += f"\n📄 {n.get('count')} pages"

            nodes.append(Node(
                id=n['id'],
                label=n.get('label', '')[:30],  # Truncate long labels
                size=size,
                color="#FFFFFF",
                borderWidth=2,
                borderWidthSelected=3,
                shape=shape,
                font={'color': '#000000', 'size': 12},
                title=title
            ))

        # Build edges
        for e in graph_data.get('edges', []):
            edges.append(Edge(
                source=e['source'],
                target=e['target'],
                color="#000000",
                width=1
            ))

        # Hierarchical config
        config = Config(
            width="100%",
            height=500,
            directed=True,
            physics=False,  # Disable physics for clean layout
            hierarchical=True,
            nodeHighlightBehavior=True,
            highlightColor="#FFD700",
            node={'labelProperty': 'label'},
            link={'renderLabel': False}
        )

        # Render
        st.markdown('<div style="border: 1px solid #000; background: #fff; padding: 1rem;">', unsafe_allow_html=True)
        selected = agraph(nodes=nodes, edges=edges, config=config)
        st.markdown('</div>', unsafe_allow_html=True)

        # Handle click
        if selected:
            for n in graph_data.get('nodes', []):
                if n['id'] == selected and n.get('url'):
                    st.link_button(f"🔗 Ouvrir: {n.get('label', 'Page')}", n['url'])
                    break

    except ImportError:
        st.error("Module streamlit-agraph non installe")
        render_text_tree(graph_data)


def render_text_tree(graph_data: Dict):
    """Fallback: render as text tree."""
    if not graph_data:
        return

    st.markdown("#### Structure (vue texte)")

    nodes_by_id = {n['id']: n for n in graph_data.get('nodes', [])}
    edges = graph_data.get('edges', [])

    # Find root
    root_id = None
    for n in graph_data.get('nodes', []):
        if n.get('type') == 'root':
            root_id = n['id']
            break

    if root_id:
        st.markdown(f"**{nodes_by_id[root_id].get('label', 'Site')}**")

        # Find children of root
        for edge in edges:
            if edge['source'] == root_id:
                child = nodes_by_id.get(edge['target'], {})
                count = child.get('count', '')
                count_str = f" ({count} pages)" if count else ""
                st.markdown(f"├── 📁 {child.get('label', 'Groupe')}{count_str}")


def run_audit(url: str):
    """Run the scraping audit with progress feedback."""
    st.session_state.audit_running = True
    st.session_state.audit_results = None
    st.session_state.ai_optimized = False
    st.session_state.clustered_data = None

    # Progress containers
    status_container = st.empty()
    progress_bar = st.progress(0)
    log_container = st.empty()

    logs = []

    def log(msg):
        logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")
        log_container.code('\n'.join(logs[-5:]), language=None)

    def update_progress(text, value):
        status_container.info(text)
        progress_bar.progress(value)

    try:
        from core.scraping import SmartScraper

        log("Demarrage de l'analyse...")
        update_progress("Recherche du sitemap...", 0.1)

        scraper = SmartScraper(
            base_url=url,
            max_urls=500,
            sample_size=50,
            specimens_per_pattern=3
        )

        results, stats = scraper.run_analysis(progress_callback=update_progress)

        log(f"URLs trouvees: {stats.get('total_urls_found', 0)}")
        log(f"Patterns detectes: {stats.get('patterns_detected', 0)}")

        update_progress("Calcul des scores...", 0.8)

        # Calculate scores
        scored_results = calculate_scores(results)

        # Generate clean clustered graph data
        update_progress("Generation du graphe...", 0.9)
        clustered_data = generate_clean_graph(url, scored_results, scraper.get_pattern_summary())

        st.session_state.audit_results = {
            'url': url,
            'pages': scored_results,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }
        st.session_state.clustered_data = clustered_data
        st.session_state.patterns_summary = scraper.get_pattern_summary()

        log("Analyse terminee!")
        update_progress("Termine!", 1.0)

        import time
        time.sleep(0.5)

        st.session_state.audit_running = False
        st.rerun()

    except Exception as e:
        st.error(f"Erreur: {str(e)}")
        log(f"ERREUR: {str(e)}")
        st.session_state.audit_running = False


def generate_clean_graph(site_url: str, pages: List[Dict], patterns: List[Dict]) -> Dict:
    """
    Generate a clean hierarchical graph with max ~25 nodes.

    Rule: If a pattern has >5 pages, collapse into a single cluster node.
    """
    nodes = []
    edges = []

    # Root node
    parsed = urlparse(site_url)
    root_label = parsed.netloc.replace('www.', '')
    if len(root_label) > 25:
        root_label = root_label[:22] + "..."

    nodes.append({
        'id': 'root',
        'label': root_label,
        'type': 'root',
        'url': site_url
    })

    # Group pages by their pattern
    pages_by_pattern: Dict[str, List[Dict]] = {}

    for page in pages:
        pattern = page.get('pattern_group', 'other')
        if not pattern or pattern == 'unique':
            pattern = 'other'

        if pattern not in pages_by_pattern:
            pages_by_pattern[pattern] = []
        pages_by_pattern[pattern].append(page)

    # Create cluster nodes (max 15 clusters)
    cluster_idx = 0
    for pattern, pattern_pages in sorted(pages_by_pattern.items(), key=lambda x: -len(x[1]))[:15]:
        cluster_id = f"cluster_{cluster_idx}"
        count = len(pattern_pages)

        # Determine cluster label from pattern or most common path segment
        cluster_label = extract_cluster_name(pattern, pattern_pages)

        nodes.append({
            'id': cluster_id,
            'label': f"📁 {cluster_label} ({count})",
            'type': 'cluster',
            'count': count,
            'pattern': pattern
        })

        edges.append({
            'source': 'root',
            'target': cluster_id
        })

        # If small cluster (<= 5 pages), show individual pages
        if count <= 5:
            for j, page in enumerate(pattern_pages):
                page_id = f"page_{cluster_idx}_{j}"
                page_label = extract_page_name(page.get('path', ''))

                nodes.append({
                    'id': page_id,
                    'label': page_label,
                    'type': 'page',
                    'url': page.get('url', ''),
                    'score': page.get('score', 50)
                })

                edges.append({
                    'source': cluster_id,
                    'target': page_id
                })

        cluster_idx += 1

    return {
        'nodes': nodes,
        'edges': edges,
        'cluster_count': cluster_idx
    }


def extract_cluster_name(pattern: str, pages: List[Dict]) -> str:
    """Extract a human-readable name for a cluster."""
    # Try to get name from pattern
    if pattern and pattern != 'other':
        # Extract first meaningful segment
        parts = pattern.replace('[^/]+', '*').replace('/?$', '').split('/')
        for part in parts:
            if part and not part.startswith('(') and part != '*':
                return part.replace('-', ' ').replace('_', ' ').title()[:20]

    # Fallback: analyze paths to find common segment
    if pages:
        path_segments = []
        for page in pages[:10]:
            path = page.get('path', '')
            parts = [p for p in path.strip('/').split('/') if p and not p.isdigit()]
            if parts:
                path_segments.append(parts[0])

        if path_segments:
            # Find most common segment
            from collections import Counter
            common = Counter(path_segments).most_common(1)
            if common:
                return common[0][0].replace('-', ' ').replace('_', ' ').title()[:20]

    return "Pages"


def extract_page_name(path: str) -> str:
    """Extract a clean page name from URL path."""
    if not path or path == '/':
        return "Accueil"

    # Get last segment
    parts = [p for p in path.strip('/').split('/') if p]
    if not parts:
        return "Page"

    name = parts[-1]

    # Clean up
    name = re.sub(r'\.html?$', '', name)
    name = re.sub(r'\?.*$', '', name)
    name = re.sub(r'[_-]+', ' ', name)
    name = name.title()

    # Truncate
    if len(name) > 25:
        name = name[:22] + "..."

    return name if name else "Page"


def run_ai_optimization():
    """Run AI optimization with visual feedback."""
    if not st.session_state.get('mistral_api_key'):
        st.warning("⚠️ Configurez votre cle API Mistral dans la sidebar")
        return

    results = st.session_state.audit_results
    if not results:
        return

    # Progress containers
    status_container = st.empty()
    progress_bar = st.progress(0)
    log_container = st.container()

    logs = []

    def log(msg):
        logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")

    def update_progress(text, value):
        status_container.info(f"🤖 {text}")
        progress_bar.progress(value)

    with log_container:
        st.markdown("##### 📋 Journal d'execution")
        log_display = st.empty()

    try:
        from core.ai_clustering import categorize_urls_with_ai, generate_smart_graph_data

        log("Demarrage de l'optimisation IA...")
        update_progress("Preparation des donnees...", 0.1)

        pages = results.get('pages', [])
        site_url = results.get('url', '')
        api_key = st.session_state.mistral_api_key

        def ai_log(msg):
            log(msg)
            log_display.code('\n'.join(logs[-8:]), language=None)

        def ai_progress(text, value):
            update_progress(text, value)

        ai_result = categorize_urls_with_ai(
            pages,
            site_url,
            api_key,
            progress_callback=ai_progress,
            log_callback=ai_log
        )

        if ai_result:
            log("Generation du graphe optimise...")
            update_progress("Finalisation...", 0.95)

            graph_data = generate_smart_graph_data(
                ai_result,
                site_url,
                pages,
                st.session_state.patterns_summary
            )

            st.session_state.ai_graph_data = graph_data
            st.session_state.ai_optimized = True

            log("Optimisation terminee!")
            update_progress("Termine!", 1.0)

            import time
            time.sleep(0.5)
            st.rerun()
        else:
            log("Echec de l'optimisation - verifiez votre cle API")
            st.error("Echec de l'optimisation IA")

    except Exception as e:
        log(f"ERREUR: {str(e)}")
        st.error(f"Erreur: {str(e)}")


def reset_audit():
    """Reset audit state."""
    st.session_state.audit_results = None
    st.session_state.ai_optimized = False
    st.session_state.ai_graph_data = None
    st.session_state.clustered_data = None
    st.session_state.patterns_summary = []


def calculate_scores(pages) -> List[Dict]:
    """Calculate SEO scores for pages."""
    from core.scraping import URLInfo

    scored_pages = []

    for page in pages:
        score = 0
        issues = []

        # Handle both URLInfo objects and dicts
        if hasattr(page, 'title'):
            title = page.title
            meta_desc = page.meta_description
            h1 = page.h1
            word_count = page.word_count
            depth = page.depth
            url = page.url
            path = page.path
            cluster = page.cluster
            pattern_group = getattr(page, 'pattern_group', None)
            is_specimen = getattr(page, 'is_specimen', True)
        else:
            title = page.get('title')
            meta_desc = page.get('meta_description')
            h1 = page.get('h1')
            word_count = page.get('word_count', 0)
            depth = page.get('depth', 0)
            url = page.get('url', '')
            path = page.get('path', '')
            cluster = page.get('cluster', 0)
            pattern_group = page.get('pattern_group')
            is_specimen = page.get('is_specimen', True)

        # Scoring
        if title:
            score += 20 if 30 <= len(title) <= 60 else 10
        else:
            issues.append("Titre manquant")

        if meta_desc:
            score += 20 if 120 <= len(meta_desc) <= 160 else 10
        else:
            issues.append("Meta description manquante")

        if h1:
            score += 20
        else:
            issues.append("H1 manquant")

        if word_count and word_count >= 300:
            score += 20
        elif word_count and word_count >= 100:
            score += 10
        else:
            issues.append("Contenu insuffisant")

        if depth <= 3:
            score += 20
        elif depth <= 5:
            score += 10

        scored_pages.append({
            'url': url,
            'path': path,
            'depth': depth,
            'cluster': cluster,
            'pattern_group': pattern_group,
            'is_specimen': is_specimen,
            'title': title,
            'meta_description': meta_desc,
            'h1': h1,
            'word_count': word_count,
            'score': score,
            'issues': issues
        })

    return scored_pages


def render_stats():
    """Render statistics."""
    results = st.session_state.audit_results
    if not results:
        return

    st.markdown("---")
    st.markdown("### 📈 Statistiques")

    stats = results.get('stats', {})
    pages = results.get('pages', [])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("URLs trouvees", stats.get('total_urls_found', 0))

    with col2:
        st.metric("Patterns", stats.get('patterns_detected', 0))

    with col3:
        st.metric("Specimens", stats.get('specimens_analyzed', 0))

    with col4:
        st.metric("Groupes", stats.get('clusters', 0))

    # Score distribution
    good = len([p for p in pages if p.get('score', 0) >= 70])
    medium = len([p for p in pages if 40 <= p.get('score', 0) < 70])
    bad = len([p for p in pages if p.get('score', 0) < 40])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"🟢 **Bon** ({good})")
    with col2:
        st.markdown(f"🟠 **Moyen** ({medium})")
    with col3:
        st.markdown(f"🔴 **A ameliorer** ({bad})")

    # Pattern details
    if st.session_state.patterns_summary:
        with st.expander("📊 Detail des patterns"):
            for p in st.session_state.patterns_summary[:10]:
                st.markdown(f"**{p['name']}**: {p['count']} pages")
