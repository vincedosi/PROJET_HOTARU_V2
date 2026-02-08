"""
HOTARU - Blocs Méthodologie réutilisables (SaaS).
Chaque module (Audit, Authority, Master, Leaf) peut afficher son onglet Méthodologie.
"""

import streamlit as st

# Contenu méthodologie par module (titre + texte court)
METHODOLOGIE_CONTENT = {
    "authority": {
        "title": "AUTHORITY SCORE — MÉTHODOLOGIE",
        "subtitle": "AI Authority Index // 5 piliers",
        "sections": [
            ("01. INDICATEUR", "L'AI Authority Index mesure la probabilité qu'une entité soit citée par les LLMs (ChatGPT, Claude, Perplexity). Score sur 100, basé sur 5 piliers pondérés."),
            ("02. LES 5 PILIERS", "Knowledge Graph (30 %) — Présence Wikidata. Structured Data (25 %) — JSON-LD. Citation Authority (20 %) — Wikipédia, backlinks. Semantic Completeness (15 %) — Richesse sémantique. Content Freshness (10 %) — Fraîcheur des données."),
            ("03. INTERPRÉTATION", "80+ : Autorité forte. 60–79 : Autorité moyenne. 40–59 : Autorité faible. < 40 : Très faible visibilité pour les LLMs."),
        ],
    },
    "master": {
        "title": "MASTER DATA — MÉTHODOLOGIE",
        "subtitle": "Données d'entité permanentes // JSON-LD",
        "sections": [
            ("01. OBJECTIF", "Construire une fiche entité (Organization) unique et fiable, alimentant le JSON-LD de toutes les pages. Source de vérité pour les moteurs et les LLMs."),
            ("02. SOURCES", "Wikidata (QID) pour l'identité et les faits. SIRET pour les entreprises françaises. Mistral AI pour l'enrichissement des champs (description, secteurs)."),
            ("03. EXPORT", "Le JSON-LD généré respecte le schéma Organization. Réutilisable dans les balises script type=\"application/ld+json\" sur l'ensemble du site."),
        ],
    },
    "leaf": {
        "title": "LEAF BUILDER — MÉTHODOLOGIE",
        "subtitle": "JSON-LD spécifique à la page",
        "sections": [
            ("01. PRINCIPE", "Chaque page peut porter un JSON-LD adapté à son contenu (Article, FAQPage, Product, etc.). LEAF combine le Master (entité) et les données dynamiques de la page."),
            ("02. ANALYSE IA", "Mistral analyse le contenu (titre, meta, H1) et prédit le type de page et les champs recommandés. Comparatif avant/après pour valider les changements."),
            ("03. USAGE", "Exporter le JSON-LD et l'intégrer dans la page. Vérifier la cohérence avec le Master Data pour garder une entité unique."),
        ],
    },
}


def render_methodologie_for_module(module_key: str):
    """
    Affiche le contenu Méthodologie pour un module (authority, master, leaf).
    Audit garde sa méthode dédiée dans audit_geo (METHODOLOGIE HOTARU complète).
    """
    content = METHODOLOGIE_CONTENT.get(module_key)
    if not content:
        st.info("Méthodologie non définie pour ce module.")
        return

    st.markdown("""
    <style>
        .methodo-container { max-width: 900px; margin: auto; padding: 20px; }
        .methodo-title { font-size: 1.8rem; font-weight: 900; letter-spacing: -0.04em; margin-bottom: 0.2rem; color: rgb(168, 27, 35); border-bottom: 2px solid rgb(168, 27, 35); padding-bottom: 8px; }
        .methodo-subtitle { font-size: 0.95rem; color: rgba(0,0,0,0.5); margin-bottom: 2rem; font-weight: 400; text-transform: uppercase; letter-spacing: 0.1em; }
        .methodo-header { font-size: 1rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: rgb(168, 27, 35); margin-bottom: 1rem; border-bottom: 2px solid rgb(168, 27, 35); padding-bottom: 6px; width: fit-content; }
        .methodo-text { font-size: 0.95rem; color: #000; line-height: 1.6; margin-bottom: 1.5rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="methodo-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="methodo-title">{content["title"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="methodo-subtitle">{content["subtitle"]}</div>', unsafe_allow_html=True)

    for header, text in content["sections"]:
        st.markdown(f'<div class="methodo-header">{header}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="methodo-text">{text}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
