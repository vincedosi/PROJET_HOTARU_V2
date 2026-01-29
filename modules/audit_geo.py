"""
HOTARU - Audit GEO Module
Main audit interface with AI-powered graph visualization.
"""

import streamlit as st
import json
from datetime import datetime
from typing import List, Dict
from streamlit_agraph import agraph, Node, Edge, Config
from core.scraping import SmartScraper, URLInfo
from core.database import get_db
from core.ai_clustering import categorize_urls_with_ai, apply_ai_categories, generate_smart_graph_data


def render_audit_geo():
    """Render the Audit GEO page."""
    # Initialize session state
    if 'audit_results' not in st.session_state:
        st.session_state.audit_results = None
    if 'selected_node' not in st.session_state:
        st.session_state.selected_node = None
    if 'audit_running' not in st.session_state:
        st.session_state.audit_running = False
    if 'ai_optimized' not in st.session_state:
        st.session_state.ai_optimized = False
    if 'ai_graph_data' not in st.session_state:
        st.session_state.ai_graph_data = None

    # Header
    st.markdown("""
        <h1 style="
            font-size: 1.75rem;
            font-weight: 600;
            color: #000000;
            margin-bottom: 0.5rem;
        ">
            Audit GEO
        </h1>
        <p style="
            font-size: 0.9rem;
            color: #000000;
            opacity: 0.6;
            margin-bottom: 2rem;
        ">
            Analyse structurelle et SEO de votre site
        </p>
    """, unsafe_allow_html=True)

    # URL Input Section
    render_url_input()

    # Progress indicator
    if st.session_state.audit_running:
        render_progress()

    # Results Section
    if st.session_state.audit_results:
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        # Action buttons row
        render_action_buttons()

        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

        # Graph section
        st.markdown("""
            <h2 style="
                font-size: 1.1rem;
                font-weight: 600;
                color: #000000;
                margin-bottom: 1rem;
            ">
                Structure du site
            </h2>
        """, unsafe_allow_html=True)

        # Choose which graph to render
        if st.session_state.ai_optimized and st.session_state.ai_graph_data:
            render_ai_graph()
        else:
            render_basic_graph()

        # Stats section
        render_stats()

        # Selected node panel
        if st.session_state.selected_node:
            render_node_panel()


def render_url_input():
    """Render the URL input field."""
    col1, col2 = st.columns([4, 1])

    with col1:
        url = st.text_input(
            "URL du site",
            placeholder="https://exemple.com",
            key="audit_url_input",
            label_visibility="collapsed"
        )

    with col2:
        start_audit = st.button(
            "Analyser",
            key="start_audit_btn",
            use_container_width=True,
            disabled=st.session_state.audit_running
        )

    if start_audit and url:
        run_audit(url)


def render_action_buttons():
    """Render the action buttons row."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # AI Optimize button
        ai_btn = st.button(
            "✨ Optimiser avec IA",
            key="ai_optimize_btn",
            use_container_width=True,
            disabled=st.session_state.ai_optimized
        )

        if ai_btn:
            run_ai_optimization()

    with col2:
        # Reset to basic view
        if st.session_state.ai_optimized:
            if st.button("↩️ Vue basique", key="reset_view_btn", use_container_width=True):
                st.session_state.ai_optimized = False
                st.session_state.ai_graph_data = None
                st.rerun()

    with col3:
        # Export button (placeholder)
        st.button("📥 Exporter", key="export_btn", use_container_width=True, disabled=True)

    with col4:
        # New audit button
        if st.button("🔄 Nouvel audit", key="new_audit_btn", use_container_width=True):
            st.session_state.audit_results = None
            st.session_state.ai_optimized = False
            st.session_state.ai_graph_data = None
            st.session_state.selected_node = None
            st.rerun()


def run_ai_optimization():
    """Run AI-powered URL categorization."""
    results = st.session_state.audit_results
    if not results:
        return

    with st.spinner("Analyse IA en cours..."):
        pages = results.get('pages', [])
        site_url = results.get('url', '')

        # Call AI categorization
        categories = categorize_urls_with_ai(pages, site_url)

        if categories:
            # Apply categories to pages
            updated_pages = apply_ai_categories(pages, categories)
            results['pages'] = updated_pages

            # Generate smart graph data
            graph_data = generate_smart_graph_data(updated_pages, site_url)
            st.session_state.ai_graph_data = graph_data
            st.session_state.ai_optimized = True

            st.success("Categorisation IA terminee!")
            st.rerun()
        else:
            st.error("Echec de l'optimisation IA. Verifiez votre cle API OpenAI.")


def render_progress():
    """Render the progress indicator."""
    progress_text = st.session_state.get('audit_progress_text', 'Initialisation...')
    progress_value = st.session_state.get('audit_progress_value', 0)
    st.progress(progress_value, text=progress_text)


def run_audit(url: str):
    """Run the audit process."""
    st.session_state.audit_running = True
    st.session_state.audit_results = None
    st.session_state.ai_optimized = False
    st.session_state.ai_graph_data = None

    progress_bar = st.progress(0, text="Initialisation...")

    def update_progress(text: str, value: float):
        progress_bar.progress(value, text=text)

    try:
        scraper = SmartScraper(
            base_url=url,
            max_urls=500,
            sample_size=50
        )

        results, stats = scraper.run_analysis(progress_callback=update_progress)
        scored_results = calculate_scores(results)

        st.session_state.audit_results = {
            'url': url,
            'pages': scored_results,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }

        save_audit_to_db(url, scored_results, stats)

        st.session_state.audit_running = False
        progress_bar.empty()
        st.rerun()

    except Exception as e:
        st.error(f"Erreur lors de l'audit: {str(e)}")
        st.session_state.audit_running = False


def calculate_scores(pages: List[URLInfo]) -> List[Dict]:
    """Calculate GEO scores for each page."""
    scored_pages = []

    for page in pages:
        score = 0
        issues = []

        # Title check (20 points)
        if page.title:
            if 30 <= len(page.title) <= 60:
                score += 20
            else:
                score += 10
                issues.append("Titre non optimise")
        else:
            issues.append("Titre manquant")

        # Meta description check (20 points)
        if page.meta_description:
            if 120 <= len(page.meta_description) <= 160:
                score += 20
            else:
                score += 10
                issues.append("Meta description non optimale")
        else:
            issues.append("Meta description manquante")

        # H1 check (20 points)
        if page.h1:
            score += 20
        else:
            issues.append("H1 manquant")

        # Content check (20 points)
        if page.word_count:
            if page.word_count >= 300:
                score += 20
            elif page.word_count >= 100:
                score += 10
                issues.append("Contenu insuffisant")
            else:
                issues.append("Contenu tres insuffisant")
        else:
            issues.append("Pas de contenu")

        # URL structure (20 points)
        if page.depth <= 3:
            score += 20
        elif page.depth <= 5:
            score += 10
            issues.append("URL trop profonde")
        else:
            issues.append("URL beaucoup trop profonde")

        scored_pages.append({
            'url': page.url,
            'path': page.path,
            'depth': page.depth,
            'cluster': page.cluster,
            'title': page.title,
            'meta_description': page.meta_description,
            'h1': page.h1,
            'word_count': page.word_count,
            'score': score,
            'issues': issues
        })

    return scored_pages


def render_ai_graph():
    """Render the AI-optimized graph."""
    graph_data = st.session_state.ai_graph_data
    if not graph_data:
        return

    nodes = []
    edges = []

    # Build nodes
    for n in graph_data['nodes']:
        color = "#FFFFFF"
        border_color = "#000000"

        if n['type'] == 'root':
            size = 35
            border_width = 3
        elif n['type'] == 'category':
            size = 25
            border_width = 2
            border_color = "#FFD700"
        else:
            size = 12
            border_width = 1
            score = n.get('score', 50)
            if score >= 70:
                border_color = "#22C55E"
            elif score >= 40:
                border_color = "#F97316"
            else:
                border_color = "#EF4444"

        nodes.append(Node(
            id=n['id'],
            label=n['label'],
            size=size,
            color=color,
            borderWidth=border_width,
            borderWidthSelected=border_width + 1,
            font={'color': '#000000', 'size': 10},
            title=n.get('description', n.get('title', n['label']))
        ))

    # Build edges
    for e in graph_data['edges']:
        edges.append(Edge(
            source=e['source'],
            target=e['target'],
            color="#000000",
            width=e.get('width', 1)
        ))

    config = Config(
        width="100%",
        height=600,
        directed=False,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#FFD700",
        collapsible=False
    )

    st.markdown("""
        <div style="border: 1px solid #000000; background-color: #FFFFFF; padding: 0.5rem;">
    """, unsafe_allow_html=True)

    selected = agraph(nodes=nodes, edges=edges, config=config)

    st.markdown("</div>", unsafe_allow_html=True)

    if selected and selected.startswith('page_'):
        for n in graph_data['nodes']:
            if n['id'] == selected and n.get('url'):
                st.session_state.selected_node = n['url']
                st.rerun()


def render_basic_graph():
    """Render the basic graph."""
    results = st.session_state.audit_results
    if not results or not results.get('pages'):
        return

    pages = results['pages']
    nodes = []
    edges = []

    # Root node
    nodes.append(Node(
        id="root",
        label=results['url'].replace("https://", "").replace("http://", ""),
        size=30,
        color="#FFFFFF",
        borderWidth=2,
        font={'color': '#000000', 'size': 12}
    ))

    # Group by cluster
    clusters: Dict[int, List[Dict]] = {}
    for page in pages:
        cluster_id = page.get('cluster', 0)
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(page)

    for cluster_id, cluster_pages in clusters.items():
        cluster_node_id = f"cluster_{cluster_id}"

        nodes.append(Node(
            id=cluster_node_id,
            label=f"Groupe {cluster_id + 1}",
            size=20,
            color="#FFFFFF",
            borderWidth=1,
            font={'color': '#000000', 'size': 10}
        ))

        edges.append(Edge(
            source="root",
            target=cluster_node_id,
            color="#000000",
            width=1
        ))

        for page in cluster_pages:
            path_parts = page['path'].strip('/').split('/')
            short_label = path_parts[-1][:20] if path_parts[-1] else 'index'

            score = page.get('score', 0)
            if score >= 70:
                border_color = "#22C55E"
            elif score >= 40:
                border_color = "#F97316"
            else:
                border_color = "#EF4444"

            nodes.append(Node(
                id=page['url'],
                label=short_label,
                size=15,
                color="#FFFFFF",
                borderWidth=1,
                font={'color': '#000000', 'size': 9},
                title=f"Score: {score}/100"
            ))

            edges.append(Edge(
                source=cluster_node_id,
                target=page['url'],
                color="#000000",
                width=0.5
            ))

    config = Config(
        width="100%",
        height=500,
        directed=False,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#FFD700"
    )

    st.markdown("""
        <div style="border: 1px solid #000000; background-color: #FFFFFF; padding: 0.5rem;">
    """, unsafe_allow_html=True)

    selected = agraph(nodes=nodes, edges=edges, config=config)

    st.markdown("</div>", unsafe_allow_html=True)

    if selected and selected.startswith('http'):
        st.session_state.selected_node = selected
        st.rerun()


def render_stats():
    """Render audit statistics."""
    results = st.session_state.audit_results
    if not results:
        return

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("<h2 style='font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem;'>Resume</h2>", unsafe_allow_html=True)

    stats = results.get('stats', {})
    pages = results.get('pages', [])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("URLs trouvees", stats.get('total_urls_found', 0))
    with col2:
        st.metric("Groupes", stats.get('clusters', 0))
    with col3:
        st.metric("Pages analysees", len(pages))
    with col4:
        avg_score = sum(p.get('score', 0) for p in pages) / len(pages) if pages else 0
        st.metric("Score moyen", f"{avg_score:.0f}/100")

    # Score distribution
    good = len([p for p in pages if p.get('score', 0) >= 70])
    medium = len([p for p in pages if 40 <= p.get('score', 0) < 70])
    bad = len([p for p in pages if p.get('score', 0) < 40])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"🟢 Bon ({good})")
    with col2:
        st.markdown(f"🟠 Moyen ({medium})")
    with col3:
        st.markdown(f"🔴 A ameliorer ({bad})")


def render_node_panel():
    """Render the node details panel."""
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    selected_url = st.session_state.selected_node
    results = st.session_state.audit_results

    if not results or not selected_url:
        return

    page_data = None
    for page in results.get('pages', []):
        if page['url'] == selected_url:
            page_data = page
            break

    if not page_data:
        return

    st.markdown("<h2 style='font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem;'>Details de la page</h2>", unsafe_allow_html=True)

    if st.button("Fermer", key="close_panel_btn"):
        st.session_state.selected_node = None
        st.rerun()

    score = page_data.get('score', 0)
    st.markdown(f"**Score:** {score}/100")
    st.markdown(f"**URL:** {page_data['url']}")

    if page_data.get('ai_category'):
        st.markdown(f"**Categorie IA:** {page_data['ai_category']}")

    st.markdown(f"**Titre:** {page_data.get('title') or 'Non defini'}")
    st.markdown(f"**H1:** {page_data.get('h1') or 'Non defini'}")
    st.markdown(f"**Mots:** {page_data.get('word_count') or 0}")

    issues = page_data.get('issues', [])
    if issues:
        st.markdown("**Points d'amelioration:**")
        for issue in issues:
            st.warning(issue)


def save_audit_to_db(url: str, pages: List[Dict], stats: Dict):
    """Save audit to database."""
    try:
        db = get_db()
        user_email = st.session_state.get('user_email', 'anonymous')

        audit_data = {
            'id': datetime.now().strftime('%Y%m%d%H%M%S'),
            'user_email': user_email,
            'url': url,
            'created_at': datetime.now().isoformat(),
            'status': 'completed',
            'results_json': json.dumps({
                'pages_count': len(pages),
                'avg_score': sum(p.get('score', 0) for p in pages) / len(pages) if pages else 0,
                'stats': stats
            })
        }

        db.append_row('audits', audit_data)
    except Exception:
        pass
