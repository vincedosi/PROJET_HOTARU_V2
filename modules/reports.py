"""
HOTARU - Reports Module
Export and view audit reports.
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, List, Optional


def render_reports():
    """Render the Reports page."""
    st.markdown("""
        <h1 style="font-size: 1.75rem; font-weight: 600; color: #000; margin-bottom: 0.5rem;">
            Rapports
        </h1>
        <p style="font-size: 0.9rem; color: #000; opacity: 0.6; margin-bottom: 1.5rem;">
            Historique et export de vos audits
        </p>
    """, unsafe_allow_html=True)

    # Check if there's a current audit
    if st.session_state.get('audit_results'):
        render_current_audit_report()
    else:
        render_no_audit_message()

    # History section
    st.markdown("---")
    render_history_section()


def render_current_audit_report():
    """Render the current audit report."""
    results = st.session_state.audit_results

    st.markdown("### 📊 Audit en cours")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"**Site:** {results.get('url', 'N/A')}")
        st.markdown(f"**Date:** {format_timestamp(results.get('timestamp', ''))}")

        pages = results.get('pages', [])
        stats = results.get('stats', {})

        st.markdown(f"**Pages analysees:** {len(pages)}")
        st.markdown(f"**Patterns detectes:** {stats.get('patterns_detected', 0)}")

    with col2:
        # Export buttons
        if st.button("📥 Exporter JSON", key="export_json", use_container_width=True):
            export_json(results)

        if st.button("📥 Exporter CSV", key="export_csv", use_container_width=True):
            export_csv(results)

    # Summary table
    st.markdown("#### Resume des pages")

    pages = results.get('pages', [])
    if pages:
        # Show top issues
        all_issues = []
        for page in pages:
            for issue in page.get('issues', []):
                all_issues.append(issue)

        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        if issue_counts:
            st.markdown("##### Problemes detectes")
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
                st.markdown(f"- **{issue}**: {count} pages")

        # Score distribution chart placeholder
        st.markdown("##### Distribution des scores")

        good = len([p for p in pages if p.get('score', 0) >= 70])
        medium = len([p for p in pages if 40 <= p.get('score', 0) < 70])
        bad = len([p for p in pages if p.get('score', 0) < 40])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🟢 Bon (70+)", good)
        with col2:
            st.metric("🟠 Moyen (40-69)", medium)
        with col3:
            st.metric("🔴 A ameliorer (<40)", bad)


def render_no_audit_message():
    """Render message when no audit is available."""
    st.info("""
        Aucun audit en cours.

        Allez dans **Audit GEO** pour analyser un site et generer un rapport.
    """)


def render_history_section():
    """Render the audit history section."""
    st.markdown("### 📚 Historique")

    # Get history from session state
    history = st.session_state.get('audit_history', [])

    if not history:
        st.markdown("*Aucun audit precedent*")
        st.markdown("Les audits seront sauvegardes ici pour reference future.")
    else:
        for i, audit in enumerate(history[-10:]):  # Show last 10
            with st.expander(f"{audit.get('url', 'N/A')} - {format_timestamp(audit.get('timestamp', ''))}"):
                st.markdown(f"**Pages:** {len(audit.get('pages', []))}")
                st.markdown(f"**Score moyen:** {calculate_avg_score(audit.get('pages', [])):.0f}/100")

                if st.button("Charger cet audit", key=f"load_{i}"):
                    st.session_state.audit_results = audit
                    st.session_state.current_page = 'audit_geo'
                    st.rerun()


def format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp for display."""
    if not timestamp:
        return "N/A"
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return timestamp


def calculate_avg_score(pages: List[Dict]) -> float:
    """Calculate average score from pages."""
    if not pages:
        return 0
    return sum(p.get('score', 0) for p in pages) / len(pages)


def export_json(results: Dict):
    """Export results as JSON."""
    json_str = json.dumps(results, indent=2, ensure_ascii=False)

    st.download_button(
        label="Telecharger JSON",
        data=json_str,
        file_name=f"hotaru_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )


def export_csv(results: Dict):
    """Export results as CSV."""
    pages = results.get('pages', [])

    if not pages:
        st.warning("Aucune page a exporter")
        return

    # Build CSV content
    headers = ['URL', 'Path', 'Score', 'Title', 'H1', 'Word Count', 'Depth', 'Issues']
    rows = [','.join(headers)]

    for page in pages:
        row = [
            f'"{page.get("url", "")}"',
            f'"{page.get("path", "")}"',
            str(page.get('score', 0)),
            f'"{(page.get("title") or "").replace(chr(34), chr(39))}"',
            f'"{(page.get("h1") or "").replace(chr(34), chr(39))}"',
            str(page.get('word_count', 0)),
            str(page.get('depth', 0)),
            f'"{"; ".join(page.get("issues", []))}"'
        ]
        rows.append(','.join(row))

    csv_content = '\n'.join(rows)

    st.download_button(
        label="Telecharger CSV",
        data=csv_content,
        file_name=f"hotaru_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
