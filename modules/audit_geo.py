"""
HOTARU - Audit GEO Module
Main audit interface with AI-powered graph visualization.

Features:
- Smart Sampling with URL pattern detection
- Progress bar and logs for Mistral AI
- Clickable nodes with URLs
- Organigramme-style graph
"""

import streamlit as st
import json
from datetime import datetime
from typing import List, Dict
from streamlit_agraph import agraph, Node, Edge, Config
from core.scraping import SmartScraper, URLInfo
from core.ai_clustering import categorize_urls_with_ai, generate_smart_graph_data


def render_audit_geo():
    """Render the Audit GEO page."""
    # Initialize session state
    init_session_state()

    # Header
    st.markdown("""
        <h1 style="font-size: 1.75rem; font-weight: 600; color: #000; margin-bottom: 0.5rem;">
            Audit GEO
        </h1>
        <p style="font-size: 0.9rem; color: #000; opacity: 0.6; margin-bottom: 1.5rem;">
            Analyse structurelle et SEO de votre site
        </p>
    """, unsafe_allow_html=True)

    # URL Input section
    render_url_input()

    # Results section
    if st.session_state.audit_results:
        render_results_section()


def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        'audit_results': None,
        'audit_running': False,
        'ai_optimized': False,
        'ai_graph_data': None,
        'mistral_api_key': '',
        'show_api_modal': False,
        'ai_loading': False,
        'ai_logs': [],
        'ai_progress': 0,
        'ai_progress_text': '',
        'patterns_summary': []
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_url_input():
    """Render URL input field with analyze button."""
    col1, col2 = st.columns([4, 1])

    with col1:
        url = st.text_input(
            "URL du site",
            placeholder="https://exemple.com",
            key="audit_url",
            label_visibility="collapsed"
        )

    with col2:
        if st.button(
            "Analyser",
            key="btn_analyze",
            use_container_width=True,
            disabled=st.session_state.audit_running
        ):
            if url:
                run_audit(url)
            else:
                st.warning("Veuillez entrer une URL")


def render_results_section():
    """Render the results section with action buttons, graph and stats."""

    # Action buttons row
    render_action_buttons()

    # API Key Modal
    if st.session_state.show_api_modal:
        render_api_key_modal()

    # AI Progress section (shows during AI processing)
    if st.session_state.ai_loading:
        render_ai_progress()
        return

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Graph section
    render_graph_section()

    # Statistics
    render_stats()


def render_action_buttons():
    """Render the action buttons row."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.session_state.ai_optimized:
            if st.button("↩️ Vue standard", key="btn_reset", use_container_width=True):
                st.session_state.ai_optimized = False
                st.session_state.ai_graph_data = None
                st.rerun()
        else:
            if st.button("✨ Optimiser avec IA", key="btn_ai", use_container_width=True):
                handle_ai_optimization()

    with col2:
        if st.button("🔄 Nouvel audit", key="btn_new", use_container_width=True):
            reset_audit()
            st.rerun()

    with col3:
        if st.session_state.mistral_api_key:
            st.markdown("""
                <div style="
                    padding: 0.5rem;
                    text-align: center;
                    font-size: 0.85rem;
                ">
                    <span style="color: #22C55E;">●</span> API OK
                </div>
            """, unsafe_allow_html=True)
        else:
            if st.button("🔑 Configurer API", key="btn_api", use_container_width=True):
                st.session_state.show_api_modal = True
                st.rerun()

    with col4:
        results = st.session_state.audit_results
        if results:
            pages = results.get('pages', [])
            avg_score = sum(p.get('score', 0) for p in pages) / len(pages) if pages else 0
            st.metric("Score moyen", f"{avg_score:.0f}/100")


def render_api_key_modal():
    """Render the API key configuration modal."""
    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### 🔑 Configuration Mistral AI")
        st.markdown("Entrez votre cle API Mistral pour activer l'optimisation IA.")

        api_key = st.text_input(
            "Cle API Mistral",
            type="password",
            placeholder="Entrez votre cle API...",
            key="api_key_input",
            value=st.session_state.mistral_api_key
        )

        st.markdown("[➜ Obtenir une cle gratuite sur console.mistral.ai](https://console.mistral.ai/)")

    with col2:
        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

        if st.button("Enregistrer", key="btn_save_api", use_container_width=True):
            if api_key:
                st.session_state.mistral_api_key = api_key
                st.session_state.show_api_modal = False
                st.success("Cle API enregistree!")
                st.rerun()
            else:
                st.error("Veuillez entrer une cle API")

        if st.button("Annuler", key="btn_cancel_api", use_container_width=True):
            st.session_state.show_api_modal = False
            st.rerun()

    st.markdown("---")


def render_ai_progress():
    """Render the AI progress section with bar and logs."""
    st.markdown("### 🤖 Optimisation IA en cours...")

    # Progress bar
    progress_value = st.session_state.ai_progress
    progress_text = st.session_state.ai_progress_text

    st.progress(progress_value, text=progress_text)

    # Logs container
    st.markdown("##### 📋 Journal d'execution")

    logs_container = st.container()
    with logs_container:
        st.markdown("""
            <div style="
                background: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 1rem;
                max-height: 200px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 0.8rem;
            ">
        """, unsafe_allow_html=True)

        for log in st.session_state.ai_logs:
            st.markdown(f"<div>{log}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Run the actual AI processing
    if st.session_state.ai_loading:
        process_ai_optimization()


def render_graph_section():
    """Render the graph visualization section."""
    # Graph title
    col_title, col_info = st.columns([3, 1])

    with col_title:
        if st.session_state.ai_optimized:
            st.markdown("### 🧠 Structure optimisee par IA")
        else:
            st.markdown("### Structure du site")

    with col_info:
        st.markdown(
            "*Cliquez sur un noeud pour ouvrir la page*",
            help="Les noeuds sont des liens cliquables vers les pages du site"
        )

    # Render appropriate graph
    if st.session_state.ai_optimized and st.session_state.ai_graph_data:
        render_ai_graph()
    else:
        render_basic_graph()


def render_ai_graph():
    """Render AI-optimized graph with clickable nodes."""
    graph_data = st.session_state.ai_graph_data
    if not graph_data:
        return

    nodes = []
    edges = []

    # Build nodes
    for n in graph_data['nodes']:
        node_url = n.get('url', '')
        node_type = n.get('type', 'page')

        # Determine styling based on type
        if node_type == 'root':
            border_color = "#000000"
            size = 45
        elif node_type == 'cluster':
            border_color = "#FFD700"
            size = 30
        elif node_type == 'group':
            border_color = n.get('borderColor', '#F97316')
            size = 20
        else:
            border_color = n.get('borderColor', '#22C55E')
            size = 15

        # Title tooltip
        title_text = f"{n['label']}"
        if node_url:
            title_text += f"\n🔗 Cliquer pour ouvrir"
        if n.get('score'):
            title_text += f"\nScore: {n.get('score', 0):.0f}/100"
        if n.get('page_count'):
            title_text += f"\n{n.get('page_count')} pages"

        nodes.append(Node(
            id=n['id'],
            label=n['label'],
            size=size,
            color="#FFFFFF",
            borderWidth=2,
            borderWidthSelected=3,
            font={'color': '#000000', 'size': 11},
            title=title_text
        ))

    # Build edges
    for e in graph_data['edges']:
        edges.append(Edge(
            source=e['source'],
            target=e['target'],
            color=e.get('color', '#000000'),
            width=e.get('width', 1)
        ))

    # Graph config
    config = Config(
        width="100%",
        height=600,
        directed=False,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#FFD700",
        collapsible=False,
        node={'labelProperty': 'label'},
        link={'labelProperty': 'label', 'renderLabel': False}
    )

    # Render graph in container
    st.markdown("""
        <div style="border: 1px solid #000; background: #fff; padding: 0.5rem;">
    """, unsafe_allow_html=True)

    selected = agraph(nodes=nodes, edges=edges, config=config)

    st.markdown("</div>", unsafe_allow_html=True)

    # Handle node click
    if selected:
        handle_node_click(selected, graph_data['nodes'])


def render_basic_graph():
    """Render basic graph without AI optimization."""
    results = st.session_state.audit_results
    if not results or not results.get('pages'):
        return

    pages = results['pages']
    nodes = []
    edges = []

    # Root node
    root_label = results['url'].replace("https://", "").replace("http://", "").replace("www.", "")
    if len(root_label) > 25:
        root_label = root_label[:22] + "..."

    nodes.append(Node(
        id="root",
        label=root_label,
        size=40,
        color="#FFFFFF",
        borderWidth=2,
        font={'color': '#000000', 'size': 12},
        title=f"Site: {results['url']}\n🔗 Cliquer pour ouvrir"
    ))

    # Group by cluster/pattern
    clusters: Dict[int, List[Dict]] = {}
    for page in pages:
        cluster_id = page.get('cluster', 0)
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(page)

    # Create cluster and page nodes
    for cluster_id, cluster_pages in clusters.items():
        cluster_node_id = f"cluster_{cluster_id}"

        # Get pattern name if available
        pattern_name = None
        for p in cluster_pages:
            if p.get('pattern_group') and p.get('pattern_group') != 'unique':
                # Extract readable name from pattern
                pattern_name = p.get('pattern_group', '').split('/')[-1].replace('[^/]+', '*')
                break

        label = pattern_name if pattern_name else f"Groupe {cluster_id + 1}"
        label = f"{label} ({len(cluster_pages)})"

        nodes.append(Node(
            id=cluster_node_id,
            label=label[:25],
            size=25,
            color="#FFFFFF",
            borderWidth=1,
            font={'color': '#000000', 'size': 10}
        ))

        edges.append(Edge(
            source="root",
            target=cluster_node_id,
            color="#000000",
            width=1.5
        ))

        # Add page nodes (limit display for large clusters)
        display_pages = cluster_pages[:10]

        for page in display_pages:
            path_parts = page['path'].strip('/').split('/')
            short_label = path_parts[-1][:18] if path_parts[-1] else 'index'

            score = page.get('score', 0)
            if score >= 70:
                border_color = "#22C55E"
            elif score >= 40:
                border_color = "#F97316"
            else:
                border_color = "#EF4444"

            is_specimen = page.get('is_specimen', True)
            node_label = short_label if is_specimen else f"[H] {short_label}"

            nodes.append(Node(
                id=page['url'],
                label=node_label[:20],
                size=14 if is_specimen else 12,
                color="#FFFFFF",
                borderWidth=1,
                font={'color': '#000000', 'size': 9},
                title=f"{page['url']}\nScore: {score}/100\n🔗 Cliquer pour ouvrir"
            ))

            edges.append(Edge(
                source=cluster_node_id,
                target=page['url'],
                color="#000000",
                width=0.5
            ))

        # Show "+N more" indicator if there are more pages
        if len(cluster_pages) > 10:
            more_count = len(cluster_pages) - 10
            nodes.append(Node(
                id=f"more_{cluster_id}",
                label=f"+{more_count} pages",
                size=12,
                color="#f0f0f0",
                font={'color': '#666666', 'size': 9}
            ))
            edges.append(Edge(
                source=cluster_node_id,
                target=f"more_{cluster_id}",
                color="#cccccc",
                width=0.5
            ))

    # Graph config
    config = Config(
        width="100%",
        height=550,
        directed=False,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#FFD700"
    )

    st.markdown("""
        <div style="border: 1px solid #000; background: #fff; padding: 0.5rem;">
    """, unsafe_allow_html=True)

    selected = agraph(nodes=nodes, edges=edges, config=config)

    st.markdown("</div>", unsafe_allow_html=True)

    # Handle click
    if selected and selected.startswith('http'):
        st.link_button(f"🔗 Ouvrir la page", selected)


def handle_node_click(selected_id: str, nodes: List[Dict]):
    """Handle node click - open URL."""
    for n in nodes:
        if n['id'] == selected_id and n.get('url'):
            url = n['url']

            # Show link button
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"Page selectionnee: **{n.get('label', 'Page')}**")
            with col2:
                st.link_button("🔗 Ouvrir", url)
            break


def render_stats():
    """Render statistics section."""
    results = st.session_state.audit_results
    if not results:
        return

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("### Statistiques")

    stats = results.get('stats', {})
    pages = results.get('pages', [])

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("URLs trouvees", stats.get('total_urls_found', 0))

    with col2:
        st.metric("Patterns detectes", stats.get('patterns_detected', 0))

    with col3:
        st.metric("Specimens analyses", stats.get('specimens_analyzed', 0))

    with col4:
        if st.session_state.ai_optimized and st.session_state.ai_graph_data:
            st.metric("Clusters IA", st.session_state.ai_graph_data.get('cluster_count', 0))
        else:
            st.metric("Groupes", stats.get('clusters', 0))

    # Score distribution
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

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

    # Pattern summary (if available)
    if st.session_state.patterns_summary:
        with st.expander("📊 Detail des patterns detectes"):
            for pattern in st.session_state.patterns_summary[:10]:
                st.markdown(
                    f"**{pattern['name']}**: {pattern['count']} pages "
                    f"({pattern['specimens']} specimens analyses)"
                )


def handle_ai_optimization():
    """Handle AI optimization button click."""
    if not st.session_state.mistral_api_key:
        st.session_state.show_api_modal = True
        st.rerun()
        return

    # Start AI optimization
    st.session_state.ai_loading = True
    st.session_state.ai_logs = []
    st.session_state.ai_progress = 0
    st.session_state.ai_progress_text = "Demarrage..."
    st.rerun()


def process_ai_optimization():
    """Process AI optimization with progress callbacks."""
    results = st.session_state.audit_results
    if not results:
        st.session_state.ai_loading = False
        return

    pages = results.get('pages', [])
    site_url = results.get('url', '')
    api_key = st.session_state.mistral_api_key

    def update_progress(text: str, value: float):
        st.session_state.ai_progress = value
        st.session_state.ai_progress_text = text

    def add_log(msg: str):
        st.session_state.ai_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")

    # Call Mistral API
    ai_result = categorize_urls_with_ai(
        pages,
        site_url,
        api_key,
        progress_callback=update_progress,
        log_callback=add_log
    )

    if ai_result:
        # Generate graph data
        graph_data = generate_smart_graph_data(
            ai_result,
            site_url,
            pages,
            st.session_state.patterns_summary
        )
        st.session_state.ai_graph_data = graph_data
        st.session_state.ai_optimized = True
        add_log("✅ Optimisation terminee avec succes!")
    else:
        add_log("❌ Echec de l'optimisation")

    st.session_state.ai_loading = False
    st.rerun()


def reset_audit():
    """Reset audit state."""
    st.session_state.audit_results = None
    st.session_state.ai_optimized = False
    st.session_state.ai_graph_data = None
    st.session_state.ai_loading = False
    st.session_state.ai_logs = []
    st.session_state.patterns_summary = []


def run_audit(url: str):
    """Run the audit process."""
    st.session_state.audit_running = True
    st.session_state.audit_results = None
    st.session_state.ai_optimized = False
    st.session_state.ai_graph_data = None
    st.session_state.patterns_summary = []

    progress_bar = st.progress(0, text="Initialisation...")

    def update_progress(text: str, value: float):
        progress_bar.progress(value, text=text)

    try:
        scraper = SmartScraper(
            base_url=url,
            max_urls=500,
            sample_size=50,
            specimens_per_pattern=3
        )

        results, stats = scraper.run_analysis(progress_callback=update_progress)
        scored_results = calculate_scores(results)

        # Save pattern summary
        st.session_state.patterns_summary = scraper.get_pattern_summary()

        st.session_state.audit_results = {
            'url': url,
            'pages': scored_results,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }

        st.session_state.audit_running = False
        progress_bar.empty()
        st.rerun()

    except Exception as e:
        st.error(f"Erreur: {str(e)}")
        st.session_state.audit_running = False


def calculate_scores(pages: List[URLInfo]) -> List[Dict]:
    """Calculate GEO scores for each page."""
    scored_pages = []

    for page in pages:
        score = 0
        issues = []

        # Title scoring
        if page.title:
            title_len = len(page.title)
            if 30 <= title_len <= 60:
                score += 20
            else:
                score += 10
                issues.append("Titre non optimise")
        else:
            issues.append("Titre manquant")

        # Meta description scoring
        if page.meta_description:
            meta_len = len(page.meta_description)
            if 120 <= meta_len <= 160:
                score += 20
            else:
                score += 10
        else:
            issues.append("Meta description manquante")

        # H1 scoring
        if page.h1:
            score += 20
        else:
            issues.append("H1 manquant")

        # Content scoring
        if page.word_count:
            if page.word_count >= 300:
                score += 20
            elif page.word_count >= 100:
                score += 10
            else:
                issues.append("Contenu insuffisant")
        else:
            issues.append("Contenu non analyse")

        # Depth scoring
        if page.depth <= 3:
            score += 20
        elif page.depth <= 5:
            score += 10

        scored_pages.append({
            'url': page.url,
            'path': page.path,
            'depth': page.depth,
            'cluster': page.cluster,
            'pattern_group': page.pattern_group,
            'is_specimen': page.is_specimen,
            'title': page.title,
            'meta_description': page.meta_description,
            'h1': page.h1,
            'word_count': page.word_count,
            'score': score,
            'issues': issues
        })

    return scored_pages
