"""
HOTARU v3 - Module HOME
Landing page / Dashboard d'accueil - Affiche le README.md
"""

import html
import os
import streamlit as st

from version import VERSION, BUILD_DATE

try:
    from version import RELEASE_NOTE
except (ImportError, AttributeError):
    RELEASE_NOTE = ""
try:
    from version import RELEASE_HISTORY
except (ImportError, AttributeError):
    RELEASE_HISTORY = []


def _read_readme() -> str:
    """Charge le contenu du README.md (depuis la racine du projet)."""
    for base in (os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        path = os.path.join(base, "README.md")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
    return "README.md introuvable."


def render_home():
    st.markdown('<div class="home-container">', unsafe_allow_html=True)

    # Cartouche version actuelle
    st.markdown(
        '<div class="home-divider"></div>'
        '<div style="font-size:0.75rem; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.5rem;">Version actuelle</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:1rem 1.5rem; margin-bottom:0.5rem;">'
        f'<div style="font-size:1.1rem; font-weight:700; color:#0f172a;">V {VERSION} — {BUILD_DATE}</div>'
        f'<div style="font-size:0.85rem; color:#475569; margin-top:0.25rem;">{html.escape(RELEASE_NOTE or "—", quote=True)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Historique des notes de version (précédentes)
    if RELEASE_HISTORY:
        st.markdown(
            '<div style="font-size:0.75rem; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin:1rem 0 0.5rem 0;">Notes de version (précédentes)</div>',
            unsafe_allow_html=True,
        )
        for entry in RELEASE_HISTORY:
            v = entry.get("version", "")
            d = entry.get("date", "")
            n = entry.get("note", "—")
            st.markdown(
                f'<div style="background:#fff; border:1px solid #e2e8f0; border-radius:6px; padding:0.75rem 1rem; margin-bottom:0.5rem;">'
                f'<span style="font-weight:700; color:#0f172a;">V {v}</span>'
                f'<span style="font-size:0.8rem; color:#64748b; margin-left:0.5rem;">{html.escape(d, quote=True)}</span>'
                f'<div style="font-size:0.85rem; color:#475569; margin-top:0.25rem;">{html.escape(n, quote=True)}</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)

    # Contenu du README en Markdown
    readme_content = _read_readme()
    st.markdown(readme_content)

    st.markdown("</div>", unsafe_allow_html=True)
