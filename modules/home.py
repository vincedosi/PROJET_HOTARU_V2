"""
HOTARU v2 - Module HOME
Landing page / Dashboard d'accueil
"""

import streamlit as st


def render_home():
    st.markdown("""
    <style>
        .home-container { max-width: 900px; margin: auto; padding: 40px 20px; }
        .home-hero { font-size: 3.5rem; font-weight: 900; letter-spacing: -0.04em; line-height: 1.05; margin-bottom: 1rem; color: #000; }
        .home-tagline { font-size: 1.2rem; color: #64748b; margin-bottom: 3rem; line-height: 1.6; max-width: 600px; }
        .home-section { font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.25em; color: #94a3b8; margin-bottom: 1.5rem; }
        .home-feature { border: 1px solid #e2e8f0; padding: 32px; margin-bottom: -1px; transition: all 0.15s ease; }
        .home-feature:hover { border-color: #000; background: #fafafa; }
        .home-feature-title { font-weight: 700; font-size: 1.05rem; margin-bottom: 6px; color: #000; }
        .home-feature-desc { font-size: 0.9rem; color: #64748b; line-height: 1.5; }
        .home-feature-tag { font-size: 0.6rem; font-weight: 800; letter-spacing: 0.15em; text-transform: uppercase; color: #94a3b8; margin-bottom: 12px; }
        .home-divider { height: 1px; background: #e2e8f0; margin: 4rem 0; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="home-container">', unsafe_allow_html=True)

    # Hero
    st.markdown('<div class="home-hero">THE AI-READABLE WEB</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="home-tagline">'
        "Hotaru audite la lisibilité de votre site web pour les moteurs de réponse IA. "
        "Optimisez vos données structurées, votre sémantique HTML et votre visibilité LLM."
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
                Crawl intelligent, scoring multicritère, graphe interactif.
                Analysez jusqu'à 10 000 pages et identifiez les failles sémantiques.
            </div>
        </div>
        <div class="home-feature">
            <div class="home-feature-tag">Module 02</div>
            <div class="home-feature-title">MASTER DATA</div>
            <div class="home-feature-desc">
                Enrichissement automatique via Wikidata + Mistral AI.
                Générez le JSON-LD de votre entité d'entreprise.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="home-feature">
            <div class="home-feature-tag">Module 03</div>
            <div class="home-feature-title">LEAF BUILDER</div>
            <div class="home-feature-desc">
                JSON-LD par page avec prédictions IA.
                Comparatif avant/après et export instantané.
            </div>
        </div>
        <div class="home-feature">
            <div class="home-feature-tag">Module 04</div>
            <div class="home-feature-title">API (Coming Soon)</div>
            <div class="home-feature-desc">
                Accès programmatique aux données d'audit.
                Intégration CI/CD et monitoring continu.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="home-divider"></div>', unsafe_allow_html=True)

    # Quick stats
    st.markdown('<div class="home-section">Votre Espace</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style="text-align:center; padding:24px; border:1px solid #e2e8f0;">
            <div style="font-size:2.5rem; font-weight:900; line-height:1;">17</div>
            <div style="font-size:0.65rem; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:#94a3b8; margin-top:8px;">Secteurs couverts</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style="text-align:center; padding:24px; border:1px solid #e2e8f0;">
            <div style="font-size:2.5rem; font-weight:900; line-height:1;">100</div>
            <div style="font-size:0.65rem; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:#94a3b8; margin-top:8px;">Score max GEO</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div style="text-align:center; padding:24px; border:1px solid #e2e8f0;">
            <div style="font-size:2.5rem; font-weight:900; line-height:1;">10K</div>
            <div style="font-size:0.65rem; font-weight:700; letter-spacing:0.2em; text-transform:uppercase; color:#94a3b8; margin-top:8px;">Pages par audit</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
