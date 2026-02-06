"""
HOTARU v2 - Module LEAF
JSON-LD spécifique à la page avec prédictions IA et comparatif
"""

import json
import requests
import streamlit as st
from bs4 import BeautifulSoup

from engine.dynamic_handler import DynamicDataHandler
from engine.template_builder import TemplateBuilder


def _get_mistral_key():
    try:
        return st.secrets["mistral"]["api_key"]
    except Exception:
        return ""


def render_leaf_tab():
    """Onglet LEAF - JSON-LD spécifique à la page"""

    st.markdown("# LEAF - Données Spécifiques à la Page")
    st.markdown(
        "**Analysez une page web et générez son JSON-LD enrichi par IA avec comparatif visuel**"
    )
    st.markdown("---")

    if "master_data" not in st.session_state or not st.session_state.master_data:
        st.warning("Vous devez d'abord créer le JSON-LD MASTER dans l'onglet précédent")
        return

    # Init session state
    for key, default in [
        ("page_url", ""),
        ("page_content", None),
        ("existing_jsonld", None),
        ("dynamic_data", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # =========================================================================
    # ÉTAPE 1 : ANALYSE DE LA PAGE
    # =========================================================================

    st.markdown("### ÉTAPE 1: Analyse de la Page")

    col1, col2 = st.columns([4, 1])

    with col1:
        page_url = st.text_input(
            "URL de la page à analyser",
            placeholder="https://example.com/article/mon-article",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("ANALYSER LA PAGE", type="primary", use_container_width=True):
            if not page_url:
                st.error("Veuillez entrer une URL")
            else:
                with st.spinner("Scraping et analyse de la page..."):
                    try:
                        response = requests.get(
                            page_url,
                            timeout=10,
                            headers={"User-Agent": "Mozilla/5.0 (compatible; Hotaru/2.0)"},
                        )
                        response.raise_for_status()
                        soup = BeautifulSoup(response.text, "html.parser")

                        # Extract existing JSON-LD
                        existing_jsonld = None
                        jsonld_scripts = soup.find_all("script", type="application/ld+json")
                        if jsonld_scripts:
                            try:
                                existing_jsonld = json.loads(jsonld_scripts[0].string)
                            except Exception:
                                pass

                        title = soup.find("title")
                        meta_desc = soup.find("meta", attrs={"name": "description"})

                        st.session_state.page_url = page_url
                        st.session_state.page_content = {
                            "title": title.string if title else "",
                            "description": meta_desc["content"] if meta_desc else "",
                            "body": soup.get_text()[:2000],
                        }
                        st.session_state.existing_jsonld = existing_jsonld
                        st.success("Page analysée avec succès")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Erreur lors du scraping: {e}")

    st.markdown("---")

    # Existing JSON-LD display
    if st.session_state.existing_jsonld:
        st.markdown("### JSON-LD Actuel de la Page")
        with st.expander("Voir le JSON-LD existant"):
            st.code(
                json.dumps(st.session_state.existing_jsonld, indent=2, ensure_ascii=False),
                language="json",
            )

    # =========================================================================
    # ÉTAPE 2 : PRÉDICTIONS IA
    # =========================================================================

    if not st.session_state.page_content:
        return

    st.markdown("### ÉTAPE 2: Génération des Prédictions IA")

    sectors = {
        "A": "Article/BlogPosting",
        "B": "Product/Offer",
        "C": "Recipe",
        "D": "Event",
        "E": "Course",
        "F": "JobPosting",
        "G": "LocalBusiness",
        "H": "Service",
        "I": "SoftwareApplication",
        "J": "Book",
        "K": "Movie",
        "L": "MusicAlbum",
    }

    # Auto-detect sector
    auto_sector = "A"
    url_lower = st.session_state.page_url.lower()
    for pattern, sector in [
        ("/product", "B"),
        ("/produit", "B"),
        ("/recipe", "C"),
        ("/recette", "C"),
        ("/event", "D"),
        ("/evenement", "D"),
    ]:
        if pattern in url_lower:
            auto_sector = sector
            break

    col1, col2 = st.columns([3, 1])

    with col1:
        selected_sector = st.selectbox(
            "Type de page détecté",
            options=list(sectors.keys()),
            format_func=lambda x: sectors[x],
            index=list(sectors.keys()).index(auto_sector),
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("GÉNÉRER PRÉDICTIONS IA", type="primary", use_container_width=True):
            mistral_key = _get_mistral_key()
            if not mistral_key:
                st.error("Clé API Mistral introuvable dans secrets Streamlit")
            else:
                with st.spinner("Mistral AI analyse le contenu..."):
                    handler = DynamicDataHandler(api_key=mistral_key)
                    st.session_state.dynamic_data = handler.generate_predictions(
                        company_name=st.session_state.master_data.brand_name,
                        description=st.session_state.page_content["description"],
                        sector=selected_sector,
                        website=st.session_state.page_url,
                    )
                    st.rerun()

    st.markdown("---")

    # =========================================================================
    # ÉTAPE 3 : VALIDATION DES PRÉDICTIONS
    # =========================================================================

    if not st.session_state.dynamic_data:
        return

    st.markdown("### ÉTAPE 3: Validation des Prédictions")

    handler = DynamicDataHandler()
    grouped = handler.get_fields_by_decision(st.session_state.dynamic_data)

    col1, col2, col3 = st.columns(3)

    categories = [
        (col1, "keep", "VALIDÉ", "Confiance élevée > 70%"),
        (col2, "hesitant", "INCERTAIN", "Confiance moyenne 40-70%"),
        (col3, "reject", "REJETÉ", "Confiance faible < 40%"),
    ]

    for col, key, title, subtitle in categories:
        with col:
            fields = grouped[key]
            st.markdown(f"#### {title} ({len(fields)})")
            st.markdown(f"*{subtitle}*")
            for field in fields:
                with st.container():
                    st.markdown(f"**{field.key}**")
                    st.text(f"{field.value or 'N/A'}")
                    st.progress(field.confidence)
                    st.caption(field.reason)
                    st.markdown("---")

    st.markdown("---")

    # =========================================================================
    # ÉTAPE 4 : GÉNÉRATION FINALE
    # =========================================================================

    st.markdown("### ÉTAPE 4: Génération du JSON-LD Leaf Final")

    if st.button("GÉNÉRER LE JSON-LD LEAF", type="primary"):
        with st.spinner("Génération du JSON-LD Leaf..."):
            builder = TemplateBuilder()
            page_data = {
                "url": st.session_state.page_url,
                "title": st.session_state.page_content["title"],
                "meta_desc": st.session_state.page_content["description"],
            }
            jsonld_leaf = builder.generate_jsonld(
                master_data=st.session_state.master_data,
                dynamic_data=st.session_state.dynamic_data,
                page_data=page_data,
            )

            st.success("JSON-LD Leaf généré avec succès")

            # Comparatif
            if st.session_state.existing_jsonld:
                st.markdown("### COMPARATIF AVANT / APRÈS")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### AVANT (Existant)")
                    st.code(
                        json.dumps(st.session_state.existing_jsonld, indent=2, ensure_ascii=False),
                        language="json",
                        line_numbers=True,
                    )
                with col2:
                    st.markdown("#### APRÈS (Hotaru Enrichi)")
                    st.code(jsonld_leaf, language="json", line_numbers=True)
            else:
                st.markdown("### JSON-LD LEAF GÉNÉRÉ")
                st.code(jsonld_leaf, language="json", line_numbers=True)

            st.download_button(
                label="TÉLÉCHARGER LE JSON-LD LEAF",
                data=jsonld_leaf,
                file_name=f"leaf_{st.session_state.page_url.split('/')[-1]}.json",
                mime="application/ld+json",
                use_container_width=True,
            )
