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

    # Cartouche version
    st.markdown(
        '<div class="home-divider"></div>'
        '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:1rem 1.5rem; margin-bottom:1rem;">'
        '<div style="font-size:0.75rem; color:#64748b; text-transform:uppercase; letter-spacing:0.05em;">Version</div>'
        f'<div style="font-size:1.1rem; font-weight:700; color:#0f172a; margin:0.25rem 0;">V {VERSION} — {BUILD_DATE}</div>'
        f'<div style="font-size:0.85rem; color:#475569;">{html.escape(RELEASE_NOTE or "—", quote=True)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Contenu du README en Markdown
    readme_content = _read_readme()
    st.markdown(readme_content)

    st.markdown("</div>", unsafe_allow_html=True)
