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
from core.ai_clustering import categorize_urls_with_ai, generate_smart_graph_data


def render_audit_geo():
    """Render the Audit GEO page."""
    # Initialize session state
    if 'audit_results' not in st.session_state:
        st.session_state.audit_results = None
    if 'audit_running' not in st.session_state:
        st.session_state.audit_running = False
    if 'ai_optimized' not in st.session_state:
        st.session_state.ai_optimized = False
    if 'ai_graph_data' not in st.session_state:
        st.session_state.ai_graph_data = None
    if 'mistral_api_key' not in st.session_state:
        st.session_state.mistral_api_key = ""
    if 'show_api_modal' not in st.session_state:
        st.session_state.show_api_modal = False
    if 'ai_loading' not in st.session_state:
        st.session_state.ai_loading = False

    # Header
    st.markdown("""
        <h1 style="font-size: 1.75rem; font-weight: 600; color: #000; margin-bottom: 0.5rem;">
            Audit GEO
        </h1>
        <p style="font-size: 0.9rem; color: #000; opacity: 0.6; margin-bottom: 1.5rem;">
            Analyse structurelle et SEO de votre site
        </p>
    """, unsafe_allow_html=True)

    # URL Input
    render_url_input()

    # Progress
    if st.session_state.audit_running:
        st.progress(st.session_state.get('progress_value', 0),
                   text=st.session_state.get('progress_text', 'Analyse en cours...'))

    # Results
    if st.session_state.audit_results:
        render_results_section()


def render_url_input():
    """Render URL input field."""
    col1, col2 = st.columns([4, 1])

    with col1:
        url = st.text_input(
            "URL",
            placeholder="https://exemple.com",
            key="audit_url",
            label_visibility="collapsed"
        )

    with col2:
        if st.button("Analyser", key="btn_analyze", use_container_width=True,
                    disabled=st.session_state.audit_running):
            if url:
                run_audit(url)


def render_results_section():
    """Render the results section with action buttons and graph."""

    # Action buttons row
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
        # API Key status indicator
        if st.session_state.mistral_api_key:
            st.markdown("🟢 Cle API OK")
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

    # API Key Modal
    if st.session_state.show_api_modal:
        render_api_key_modal()

    # Loading indicator for AI
    if st.session_state.ai_loading:
        st.markdown("""
            <div style="padding: 2rem; text-align: center; border: 1px solid #000; margin: 1rem 0;">
                <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">🤖 Mistral analyse vos pages...</div>
                <div style="font-size: 0.9rem; opacity: 0.6;">Creation des categories intelligentes</div>
            </div>
        """, unsafe_allow_html=True)
        st.spinner("Traitement en cours...")
        return

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Graph title with info
    col_title, col_info = st.columns([3, 1])
    with col_title:
        if st.session_state.ai_optimized:
            st.markdown("### 🧠 Structure optimisee par IA")
        else:
            st.markdown("### Structure du site")

    with col_info:
        st.markdown("*Cliquez sur un noeud pour ouvrir la page*",
                   help="Les noeuds sont des liens cliquables")

    # Render appropriate graph
    if st.session_state.ai_optimized and st.session_state.ai_graph_data:
        render_ai_graph()
    else:
        render_basic_graph()

    # Stats
    render_stats()


def render_api_key_modal():
    """Render the API key input modal."""
    st.markdown("---")
    st.markdown("### 🔑 Configuration Mistral AI")
    st.markdown("Entrez votre cle API Mistral pour activer l'optimisation IA.")
    st.markdown("[Obtenir une cle gratuite](https://console.mistral.ai/)")

    api_key = st.text_input(
        "Cle API Mistral",
        type="password",
        placeholder="Entrez votre cle API...",
        key="api_key_input",
        value=st.session_state.mistral_api_key
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Enregistrer", key="btn_save_api", use_container_width=True):
            if api_key:
                st.session_state.mistral_api_key = api_key
                st.session_state.show_api_modal = False
                st.success("Cle API enregistree!")
                st.rerun()
            else:
                st.error("Veuillez entrer une cle API")

    with col2:
        if st.button("Annuler", key="btn_cancel_api", use_container_width=True):
            st.session_state.show_api_modal = False
            st.rerun()

    st.markdown("---")


def handle_ai_optimization():
    """Handle AI optimization button click."""
    if not st.session_state.mistral_api_key:
        st.session_state.show_api_modal = True
        st.rerun()
        return

    # Run AI optimization
    run_ai_optimization()


def run_ai_optimization():
    """Run AI-powered URL categorization."""
    results = st.session_state.audit_results
    if not results:
        return

    st.session_state.ai_loading = True
    st.rerun()


def process_ai_optimization():
    """Process AI optimization (called after rerun)."""
    if not st.session_state.ai_loading:
        return

    results = st.session_state.audit_results
    pages = results.get('pages', [])
    site_url = results.get('url', '')
    api_key = st.session_state.mistral_api_key

    # Call Mistral API
    ai_result = categorize_urls_with_ai(pages, site_url, api_key)

    if ai_result:
        # Generate graph data
        graph_data = generate_smart_graph_data(ai_result, site_url, pages)
        st.session_state.ai_graph_data = graph_data
        st.session_state.ai_optimized = True
        st.success("Optimisation IA terminee!")
    else:
        st.error("Echec de l'optimisation. Verifiez votre cle API.")

    st.session_state.ai_loading = False


def reset_audit():
    """Reset audit state."""
    st.session_state.audit_results = None
    st.session_state.ai_optimized = False
    st.session_state.ai_graph_data = None
    st.session_state.ai_loading = False


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
        scraper = SmartScraper(base_url=url, max_urls=500, sample_size=50)
        results, stats = scraper.run_analysis(progress_callback=update_progress)
        scored_results = calculate_scores(results)

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

        if page.title:
            score += 20 if 30 <= len(page.title) <= 60 else 10
            if not (30 <= len(page.title) <= 60):
                issues.append("Titre non optimise")
        else:
            issues.append("Titre manquant")

        if page.meta_description:
            score += 20 if 120 <= len(page.meta_description) <= 160 else 10
        else:
            issues.append("Meta description manquante")

        if page.h1:
            score += 20
        else:
            issues.append("H1 manquant")

        if page.word_count:
            if page.word_count >= 300:
                score += 20
            elif page.word_count >= 100:
                score += 10
        else:
            issues.append("Contenu insuffisant")

        if page.depth <= 3:
            score += 20
        elif page.depth <= 5:
            score += 10

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
    """Render AI-optimized graph with clickable nodes."""
    graph_data = st.session_state.ai_graph_data
    if not graph_data:
        return

    nodes = []
    edges = []

    # Build nodes with URLs for clicking
    for n in graph_data['nodes']:
        node_url = n.get('url', '')

        # Determine border color by type and score
        if n['type'] == 'root':
            border_color = "#000000"
            size = 40
        elif n['type'] == 'cluster':
            border_color = "#FFD700"  # Yellow for clusters
            size = 28
        else:
            score = n.get('score', 50)
            if score >= 70:
                border_color = "#22C55E"
            elif score >= 40:
                border_color = "#F97316"
            else:
                border_color = "#EF4444"
            size = 15

        # Create node with URL in title for reference
        title_text = f"{n['label']}"
        if node_url:
            title_text += f"\n🔗 Cliquer pour ouvrir"

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

    for e in graph_data['edges']:
        edges.append(Edge(
            source=e['source'],
            target=e['target'],
            color="#000000",
            width=e.get('width', 1)
        ))

    # Graph config with better physics
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

    st.markdown("""
        <div style="border: 1px solid #000; background: #fff; padding: 0.5rem;">
    """, unsafe_allow_html=True)

    selected = agraph(nodes=nodes, edges=edges, config=config)

    st.markdown("</div>", unsafe_allow_html=True)

    # Handle node click - open URL
    if selected:
        for n in graph_data['nodes']:
            if n['id'] == selected and n.get('url'):
                st.markdown(f"""
                    <script>window.open('{n["url"]}', '_blank');</script>
                """, unsafe_allow_html=True)
                # Also show link button as fallback
                st.link_button(f"Ouvrir: {n['label']}", n['url'])
                break


def render_basic_graph():
    """Render basic graph."""
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
        size=35,
        color="#FFFFFF",
        borderWidth=2,
        font={'color': '#000000', 'size': 12},
        title=f"Site: {results['url']}"
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
            label=f"Groupe {cluster_id + 1} ({len(cluster_pages)})",
            size=22,
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

        for page in cluster_pages:
            path_parts = page['path'].strip('/').split('/')
            short_label = path_parts[-1][:18] if path_parts[-1] else 'index'

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
                size=14,
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

    # Handle click - open URL
    if selected and selected.startswith('http'):
        st.link_button(f"Ouvrir la page", selected)


def render_stats():
    """Render statistics."""
    results = st.session_state.audit_results
    if not results:
        return

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    stats = results.get('stats', {})
    pages = results.get('pages', [])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("URLs trouvees", stats.get('total_urls_found', 0))
    with col2:
        st.metric("Pages analysees", len(pages))
    with col3:
        if st.session_state.ai_optimized and st.session_state.ai_graph_data:
            st.metric("Clusters IA", st.session_state.ai_graph_data.get('cluster_count', 0))
        else:
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


# Process AI optimization if loading
if 'ai_loading' in st.session_state and st.session_state.ai_loading:
    process_ai_optimization()
