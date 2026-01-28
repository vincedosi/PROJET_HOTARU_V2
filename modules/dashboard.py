"""
HOTARU - Dashboard Module
Overview page with statistics and recent activity.
"""

import streamlit as st
from datetime import datetime
from core.database import get_db


def render_dashboard():
    """Render the main dashboard page."""
    # Header
    st.markdown("""
        <h1 style="
            font-size: 1.75rem;
            font-weight: 600;
            color: #000000;
            margin-bottom: 0.5rem;
        ">
            Dashboard
        </h1>
        <p style="
            font-size: 0.9rem;
            color: #000000;
            opacity: 0.6;
            margin-bottom: 2rem;
        ">
            Vue d'ensemble de votre activité
        </p>
    """, unsafe_allow_html=True)

    # Spacer
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Stats cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_stat_card("Audits", get_audit_count(), "ce mois")

    with col2:
        render_stat_card("Pages analysées", get_pages_count(), "total")

    with col3:
        render_stat_card("Score moyen", get_average_score(), "GEO")

    with col4:
        render_stat_card("Dernière activité", get_last_activity(), "")

    # Spacer
    st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

    # Two columns layout
    col_left, col_right = st.columns([1.5, 1])

    with col_left:
        render_recent_audits()

    with col_right:
        render_quick_actions()

    # Spacer
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    # Activity chart placeholder
    render_activity_chart()


def render_stat_card(title: str, value: str, subtitle: str):
    """Render a statistics card."""
    st.markdown(f"""
        <div style="
            border: 1px solid #000000;
            padding: 1.5rem;
            background-color: #FFFFFF;
        ">
            <div style="
                font-size: 0.75rem;
                color: #000000;
                opacity: 0.6;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 0.5rem;
            ">
                {title}
            </div>
            <div style="
                font-size: 2rem;
                font-weight: 600;
                color: #000000;
                line-height: 1;
            ">
                {value}
            </div>
            <div style="
                font-size: 0.7rem;
                color: #000000;
                opacity: 0.5;
                margin-top: 0.25rem;
            ">
                {subtitle}
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_recent_audits():
    """Render the recent audits section."""
    st.markdown("""
        <h2 style="
            font-size: 1.1rem;
            font-weight: 600;
            color: #000000;
            margin-bottom: 1rem;
        ">
            Audits récents
        </h2>
    """, unsafe_allow_html=True)

    # Get recent audits from database
    audits = get_recent_audits()

    if not audits:
        st.markdown("""
            <div style="
                border: 1px solid #000000;
                padding: 2rem;
                text-align: center;
                color: #000000;
                opacity: 0.5;
            ">
                Aucun audit récent
            </div>
        """, unsafe_allow_html=True)
        return

    for audit in audits:
        render_audit_row(audit)


def render_audit_row(audit: dict):
    """Render a single audit row."""
    score_color = get_score_color(audit.get('score', 0))

    st.markdown(f"""
        <div style="
            border: 1px solid #000000;
            padding: 1rem;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div>
                <div style="
                    font-size: 0.9rem;
                    font-weight: 500;
                    color: #000000;
                ">
                    {audit.get('url', 'N/A')}
                </div>
                <div style="
                    font-size: 0.75rem;
                    color: #000000;
                    opacity: 0.5;
                ">
                    {audit.get('date', 'N/A')}
                </div>
            </div>
            <div style="
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background-color: {score_color};
            "></div>
        </div>
    """, unsafe_allow_html=True)


def render_quick_actions():
    """Render quick action buttons."""
    st.markdown("""
        <h2 style="
            font-size: 1.1rem;
            font-weight: 600;
            color: #000000;
            margin-bottom: 1rem;
        ">
            Actions rapides
        </h2>
    """, unsafe_allow_html=True)

    if st.button("🔍  Nouvel Audit GEO", key="quick_audit", use_container_width=True):
        st.session_state.current_page = 'audit_geo'
        st.rerun()

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    if st.button("📊  Voir les rapports", key="quick_reports", use_container_width=True):
        st.info("Fonctionnalité à venir")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    if st.button("⚙️  Paramètres", key="quick_settings", use_container_width=True):
        st.session_state.current_page = 'settings'
        st.rerun()


def render_activity_chart():
    """Render activity chart placeholder."""
    st.markdown("""
        <h2 style="
            font-size: 1.1rem;
            font-weight: 600;
            color: #000000;
            margin-bottom: 1rem;
        ">
            Activité
        </h2>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style="
            border: 1px solid #000000;
            padding: 3rem;
            text-align: center;
            color: #000000;
            opacity: 0.5;
        ">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📈</div>
            <div>Graphique d'activité (données insuffisantes)</div>
        </div>
    """, unsafe_allow_html=True)


# Helper functions

def get_audit_count() -> str:
    """Get the number of audits this month."""
    try:
        db = get_db()
        audits = db.read_sheet('audits')
        if audits is None or audits.empty:
            return "0"

        # Filter by current month
        current_month = datetime.now().strftime('%Y-%m')
        count = len(audits[audits['created_at'].str.startswith(current_month)])
        return str(count)
    except Exception:
        return "0"


def get_pages_count() -> str:
    """Get total pages analyzed."""
    try:
        db = get_db()
        audits = db.read_sheet('audits')
        if audits is None or audits.empty:
            return "0"

        # This would need actual page count tracking
        return str(len(audits) * 50)  # Estimate
    except Exception:
        return "0"


def get_average_score() -> str:
    """Get average GEO score."""
    try:
        db = get_db()
        audits = db.read_sheet('audits')
        if audits is None or audits.empty:
            return "—"

        # Would need actual score data
        return "—"
    except Exception:
        return "—"


def get_last_activity() -> str:
    """Get time since last activity."""
    try:
        db = get_db()
        audits = db.read_sheet('audits')
        if audits is None or audits.empty:
            return "—"

        # Get most recent audit
        return "Récent"
    except Exception:
        return "—"


def get_recent_audits() -> list:
    """Get list of recent audits."""
    try:
        db = get_db()
        audits = db.read_sheet('audits')
        if audits is None or audits.empty:
            return []

        # Return last 5 audits
        return audits.tail(5).to_dict('records')
    except Exception:
        return []


def get_score_color(score: float) -> str:
    """Get color based on score."""
    if score >= 70:
        return "#22C55E"  # Green
    elif score >= 40:
        return "#F97316"  # Orange
    else:
        return "#EF4444"  # Red
