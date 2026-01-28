"""
HOTARU - Audit GEO Module
Main audit interface with graph visualization.
"""

import streamlit as st
import json
from datetime import datetime
from typing import List, Dict, Optional
from streamlit_agraph import agraph, Node, Edge, Config
from core.scraping import SmartScraper, URLInfo
from core.database import get_db


def render_audit_geo():
    """Render the Audit GEO page."""
    # Initialize session state
    if 'audit_results' not in st.session_state:
        st.session_state.audit_results = None
    if 'selected_node' not in st.session_state:
        st.session_state.selected_node = None
    if 'audit_running' not in st.session_state:
        st.session_state.audit_running = False

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

    # Main layout with potential right panel
    if st.session_state.selected_node:
        col_main, col_panel = st.columns([2, 1])
    else:
        col_main = st.container()
        col_panel = None

    with col_main:
        render_url_input()

        # Progress indicator
        if st.session_state.audit_running:
            render_progress()

        # Results
        if st.session_state.audit_results:
            render_graph()
            render_stats()

    # Right panel for node details
    if col_panel and st.session_state.selected_node:
        with col_panel:
            render_node_panel()


def render_url_input():
    """Render the URL input field."""
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Create form for URL input
    col1, col2 = st.columns([4, 1])

    with col1:
        url = st.text_input(
            "URL du site",
            placeholder="exemple.com",
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

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)


def render_progress():
    """Render the progress indicator."""
    progress_container = st.empty()
    progress_text = st.session_state.get('audit_progress_text', 'Initialisation...')
    progress_value = st.session_state.get('audit_progress_value', 0)

    progress_container.progress(progress_value, text=progress_text)


def run_audit(url: str):
    """Run the audit process."""
    st.session_state.audit_running = True
    st.session_state.audit_results = None

    progress_bar = st.progress(0, text="Initialisation...")

    def update_progress(text: str, value: float):
        progress_bar.progress(value, text=text)

    try:
        # Initialize scraper
        scraper = SmartScraper(
            base_url=url,
            max_urls=500,
            sample_size=50
        )

        # Run analysis
        results, stats = scraper.run_analysis(progress_callback=update_progress)

        # Calculate scores
        scored_results = calculate_scores(results)

        # Store results
        st.session_state.audit_results = {
            'url': url,
            'pages': scored_results,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }

        # Save to database
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
            elif page.title:
                score += 10
                issues.append("Titre trop court ou trop long")
        else:
            issues.append("Titre manquant")

        # Meta description check (20 points)
        if page.meta_description:
            if 120 <= len(page.meta_description) <= 160:
                score += 20
            elif page.meta_description:
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
                issues.append("Contenu très insuffisant")
        else:
            issues.append("Pas de contenu détecté")

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


def render_graph():
    """Render the URL structure graph."""
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

    results = st.session_state.audit_results
    if not results or not results.get('pages'):
        return

    pages = results['pages']

    # Build nodes and edges
    nodes = []
    edges = []

    # Root node
    nodes.append(Node(
        id="root",
        label=results['url'],
        size=30,
        color="#FFFFFF",
        borderWidth=2,
        borderWidthSelected=3,
        font={'color': '#000000', 'size': 12}
    ))

    # Group pages by cluster
    clusters: Dict[int, List[Dict]] = {}
    for page in pages:
        cluster_id = page.get('cluster', 0)
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(page)

    # Cluster colors (subtle, mostly white)
    cluster_colors = ['#FFFFFF'] * 20

    # Add cluster nodes and page nodes
    for cluster_id, cluster_pages in clusters.items():
        # Cluster node
        cluster_node_id = f"cluster_{cluster_id}"
        nodes.append(Node(
            id=cluster_node_id,
            label=f"Groupe {cluster_id + 1}",
            size=20,
            color=cluster_colors[cluster_id % len(cluster_colors)],
            borderWidth=1,
            font={'color': '#000000', 'size': 10}
        ))

        edges.append(Edge(
            source="root",
            target=cluster_node_id,
            color="#000000",
            width=1
        ))

        # Page nodes
        for page in cluster_pages:
            score = page.get('score', 0)
            score_color = get_score_indicator_color(score)

            # Short label (last path segment)
            path_parts = page['path'].strip('/').split('/')
            short_label = path_parts[-1][:20] if path_parts[-1] else 'index'

            nodes.append(Node(
                id=page['url'],
                label=short_label,
                size=15,
                color="#FFFFFF",
                borderWidth=1,
                font={'color': '#000000', 'size': 9},
                title=f"{page['url']}\nScore: {score}/100"
            ))

            edges.append(Edge(
                source=cluster_node_id,
                target=page['url'],
                color="#000000",
                width=0.5
            ))

    # Graph configuration
    config = Config(
        width="100%",
        height=500,
        directed=False,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#FFD700",
        collapsible=False,
        node={
            'labelProperty': 'label',
            'renderLabel': True
        },
        link={
            'labelProperty': 'label',
            'renderLabel': False
        }
    )

    # Container with white background
    st.markdown("""
        <div style="
            border: 1px solid #000000;
            background-color: #FFFFFF;
            padding: 1rem;
        ">
    """, unsafe_allow_html=True)

    # Render graph
    selected = agraph(nodes=nodes, edges=edges, config=config)

    st.markdown("</div>", unsafe_allow_html=True)

    # Handle node selection
    if selected and selected != st.session_state.selected_node:
        if selected.startswith('http'):
            st.session_state.selected_node = selected
            st.rerun()


def render_stats():
    """Render audit statistics."""
    results = st.session_state.audit_results
    if not results:
        return

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    st.markdown("""
        <h2 style="
            font-size: 1.1rem;
            font-weight: 600;
            color: #000000;
            margin-bottom: 1rem;
        ">
            Résumé
        </h2>
    """, unsafe_allow_html=True)

    stats = results.get('stats', {})
    pages = results.get('pages', [])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_mini_stat("URLs trouvées", str(stats.get('total_urls_found', 0)))

    with col2:
        render_mini_stat("Clusters", str(stats.get('clusters', 0)))

    with col3:
        render_mini_stat("Pages analysées", str(len(pages)))

    with col4:
        avg_score = sum(p.get('score', 0) for p in pages) / len(pages) if pages else 0
        render_mini_stat("Score moyen", f"{avg_score:.0f}/100")

    # Score distribution
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    good = len([p for p in pages if p.get('score', 0) >= 70])
    medium = len([p for p in pages if 40 <= p.get('score', 0) < 70])
    bad = len([p for p in pages if p.get('score', 0) < 40])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: #22C55E;"></div>
                <span style="color: #000000;">Bon ({good})</span>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: #F97316;"></div>
                <span style="color: #000000;">Moyen ({medium})</span>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: #EF4444;"></div>
                <span style="color: #000000;">À améliorer ({bad})</span>
            </div>
        """, unsafe_allow_html=True)


def render_mini_stat(label: str, value: str):
    """Render a mini stat card."""
    st.markdown(f"""
        <div style="
            border: 1px solid #000000;
            padding: 1rem;
            text-align: center;
        ">
            <div style="
                font-size: 1.5rem;
                font-weight: 600;
                color: #000000;
            ">
                {value}
            </div>
            <div style="
                font-size: 0.75rem;
                color: #000000;
                opacity: 0.6;
            ">
                {label}
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_node_panel():
    """Render the right panel with node details."""
    st.markdown("""
        <div style="
            border: 1px solid #000000;
            padding: 1.5rem;
            height: 100%;
        ">
    """, unsafe_allow_html=True)

    # Close button
    if st.button("✕ Fermer", key="close_panel"):
        st.session_state.selected_node = None
        st.rerun()

    selected_url = st.session_state.selected_node
    results = st.session_state.audit_results

    if not results or not selected_url:
        return

    # Find page data
    page_data = None
    for page in results.get('pages', []):
        if page['url'] == selected_url:
            page_data = page
            break

    if not page_data:
        st.warning("Page non trouvée")
        return

    # Score indicator
    score = page_data.get('score', 0)
    score_color = get_score_indicator_color(score)

    st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 1rem;
            margin: 1rem 0;
        ">
            <div style="
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background-color: {score_color};
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 600;
            ">
                {score}
            </div>
            <div style="
                font-size: 0.8rem;
                color: #000000;
            ">
                Score GEO
            </div>
        </div>
    """, unsafe_allow_html=True)

    # URL
    st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <div style="font-size: 0.7rem; color: #000000; opacity: 0.5; margin-bottom: 0.25rem;">
                URL
            </div>
            <div style="font-size: 0.85rem; color: #000000; word-break: break-all;">
                {page_data['url']}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Title
    title = page_data.get('title') or 'Non défini'
    st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <div style="font-size: 0.7rem; color: #000000; opacity: 0.5; margin-bottom: 0.25rem;">
                Titre
            </div>
            <div style="font-size: 0.85rem; color: #000000;">
                {title}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # H1
    h1 = page_data.get('h1') or 'Non défini'
    st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <div style="font-size: 0.7rem; color: #000000; opacity: 0.5; margin-bottom: 0.25rem;">
                H1
            </div>
            <div style="font-size: 0.85rem; color: #000000;">
                {h1}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Word count
    word_count = page_data.get('word_count') or 0
    st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <div style="font-size: 0.7rem; color: #000000; opacity: 0.5; margin-bottom: 0.25rem;">
                Nombre de mots
            </div>
            <div style="font-size: 0.85rem; color: #000000;">
                {word_count}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Issues
    issues = page_data.get('issues', [])
    if issues:
        st.markdown("""
            <div style="margin-bottom: 0.5rem;">
                <div style="font-size: 0.7rem; color: #000000; opacity: 0.5; margin-bottom: 0.25rem;">
                    Points d'amélioration
                </div>
            </div>
        """, unsafe_allow_html=True)

        for issue in issues:
            st.markdown(f"""
                <div style="
                    font-size: 0.8rem;
                    color: #000000;
                    padding: 0.5rem;
                    border-left: 2px solid #EF4444;
                    margin-bottom: 0.5rem;
                    background-color: #FFFFFF;
                ">
                    {issue}
                </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def get_score_indicator_color(score: int) -> str:
    """Get the color for a score indicator."""
    if score >= 70:
        return "#22C55E"  # Green
    elif score >= 40:
        return "#F97316"  # Orange
    else:
        return "#EF4444"  # Red


def save_audit_to_db(url: str, pages: List[Dict], stats: Dict):
    """Save audit results to database."""
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

    except Exception as e:
        # Non-critical, don't show error to user
        pass
