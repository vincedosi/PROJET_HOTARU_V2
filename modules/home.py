"""
HOTARU v3 - Module HOME
Landing page / Dashboard d'accueil - Brutalist Monochrome
"""

import streamlit as st


def render_home():

    st.markdown('<div class="home-container">', unsafe_allow_html=True)

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

    # Note de version
    st.markdown(
        '<p class="home-tagline" style="font-size:0.8rem; color:rgba(0,0,0,0.5); margin-bottom:2rem;">'
        '<strong>Version 3.0.1</strong> (2026-02-08) &mdash; Harmonisation titres, workspace principal, palette noir & rouge.'
        '</p>',
        unsafe_allow_html=True,
    )

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
