"""
HOTARU v3 - Module HOME
Landing page / Dashboard d'accueil - Brutalist Monochrome
"""

import html
import streamlit as st

from version import VERSION, BUILD_DATE

try:
    from version import RELEASE_NOTE
except (ImportError, AttributeError):
    RELEASE_NOTE = ""


def render_home():

    st.markdown('<div class="home-container">', unsafe_allow_html=True)

    # Cartouche version (valeurs dynamiques depuis version.py)
    note_escaped = html.escape(RELEASE_NOTE or "", quote=True)
    st.markdown(
        '<div class="home-divider"></div>'
        '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:1rem 1.5rem; margin-bottom:1.5rem;">'
        '<div style="font-size:0.75rem; color:#64748b; text-transform:uppercase; letter-spacing:0.05em;">Version</div>'
        f'<div style="font-size:1.1rem; font-weight:700; color:#0f172a; margin:0.25rem 0;">V {VERSION} — {BUILD_DATE}</div>'
        f'<div style="font-size:0.85rem; color:#475569;">{note_escaped}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Hero
    st.markdown('<div class="home-hero">THE AI-READABLE WEB</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="home-tagline">'
        "Hotaru audite la lisibilite de votre site web pour les moteurs de reponse IA. "
        "Optimisez vos donnees structurees, votre semantique HTML et votre visibilite LLM."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="home-divider"></div>', unsafe_allow_html=True)

    # Features
    st.markdown('<div class="home-section">Outils</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="home-feature">
            <div class="home-feature-tag">Module 01</div>
            <div class="home-feature-title">AUDIT GEO</div>
            <div class="home-feature-desc">
                Crawl intelligent, scoring multicritere, graphe interactif.
                Analysez jusqu'a 10 000 pages et identifiez les failles semantiques.
            </div>
        </div>
        <div class="home-feature">
            <div class="home-feature-tag">Module 02</div>
            <div class="home-feature-title">MASTER DATA</div>
            <div class="home-feature-desc">
                Enrichissement automatique via Wikidata + Mistral AI.
                Generez le JSON-LD de votre entite d'entreprise.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="home-feature">
            <div class="home-feature-tag">Module 03</div>
            <div class="home-feature-title">AUTHORITY SCORE</div>
            <div class="home-feature-desc">
                AI Authority Index sur 5 piliers.
                Mesurez la probabilite de citation par les LLMs.
            </div>
        </div>
        <div class="home-feature">
            <div class="home-feature-tag">Module 04</div>
            <div class="home-feature-title">LEAF BUILDER</div>
            <div class="home-feature-desc">
                JSON-LD par page avec predictions IA.
                Comparatif avant/apres et export instantane.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="home-divider"></div>', unsafe_allow_html=True)

    # Quick stats
    st.markdown('<div class="home-section">Votre Espace</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            '<div class="zen-metric">'
            '<div class="zen-metric-value">17</div>'
            '<div class="zen-metric-label">Secteurs couverts</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            '<div class="zen-metric">'
            '<div class="zen-metric-value">100</div>'
            '<div class="zen-metric-label">Score max GEO</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            '<div class="zen-metric">'
            '<div class="zen-metric-value">10K</div>'
            '<div class="zen-metric-label">Pages par audit</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
