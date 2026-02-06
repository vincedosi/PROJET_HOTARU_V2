"""
HOTARU v2 - Module MASTER DATA
Interface Zen pour l'enrichissement et l'édition des données d'entité
"""

import os
import streamlit as st
from engine.master_handler import MasterDataHandler, MasterData
from engine.template_builder import TemplateBuilder


def _get_mistral_key():
    try:
        return st.secrets["mistral"]["api_key"]
    except Exception:
        return ""


def render_master_tab():
    """Onglet MASTER - Interface Zen avec champs éditables"""

    if "master_data" not in st.session_state:
        st.session_state.master_data = None

    # Header
    st.markdown('<div class="zen-logo">蛍</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="zen-title">MASTER DATA</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="zen-subtitle">Données d\'Entité Permanentes / JSON-LD Foundation</p>',
        unsafe_allow_html=True,
    )

    # =========================================================================
    # ÉTAPE 1 : RECHERCHE & ENRICHISSEMENT
    # =========================================================================

    st.markdown('<div class="zen-card">', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-title">01 / Identification & Enrichissement</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        company_name = st.text_input(
            "Nom de l'organisation",
            placeholder="Ex: Airbus, BNP Paribas, Decathlon...",
            label_visibility="collapsed",
            key="company_search",
        )

    with col2:
        qid_manual = st.text_input(
            "QID Wikidata (optionnel)",
            placeholder="Ex: Q67",
            label_visibility="collapsed",
            key="qid_search",
        )

    with col3:
        siren_manual = st.text_input(
            "SIREN (optionnel)",
            placeholder="Ex: 351058151",
            label_visibility="collapsed",
            key="siren_search",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    with col_btn1:
        if st.button("RECHERCHER", use_container_width=True, key="search_btn"):
            if company_name or qid_manual or siren_manual:
                with st.spinner("Interrogation de Wikidata..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_enrich(
                        search_query=company_name or None,
                        qid=qid_manual or None,
                        siren=siren_manual or None,
                    )
                    st.rerun()
            else:
                st.error("Entrez au moins un critère")

    with col_btn2:
        if st.button(
            "ENRICHIR MISTRAL",
            use_container_width=True,
            key="enrich_btn",
            disabled=not st.session_state.master_data,
        ):
            mistral_key = _get_mistral_key()
            if mistral_key and st.session_state.master_data.qid:
                with st.spinner("Mistral enrichit les données..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_complete_with_mistral(
                        st.session_state.master_data, mistral_key
                    )
                    st.rerun()
            else:
                st.error("Clé Mistral ou QID manquant")

    st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # ÉTAPE 2 : ÉDITION DES DONNÉES
    # =========================================================================

    if not st.session_state.master_data:
        return

    master = st.session_state.master_data

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    # Status
    status_map = {
        "complete": ("status-complete", "COMPLET"),
        "partial": ("status-partial", "PARTIEL"),
        "failed": ("status-failed", "ÉCHEC"),
    }
    cls, txt = status_map.get(master.status, ("status-partial", "PARTIEL"))
    st.markdown(
        f'<span class="status-badge {cls}">{txt}</span>', unsafe_allow_html=True
    )

    if master.errors:
        with st.expander("Erreurs détectées"):
            for error in master.errors:
                st.caption(error)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Metrics
    col1, col2, col3 = st.columns(3)

    key_fields = [master.brand_name, master.qid, master.site_url]
    social_fields = [
        master.wikipedia_url,
        master.linkedin_url,
        master.twitter_url,
        master.facebook_url,
        master.instagram_url,
        master.youtube_url,
    ]
    contact_fields = [master.phone, master.email, master.street, master.city]

    for col, (count, label) in zip(
        [col1, col2, col3],
        [
            (len([f for f in key_fields if f]), "Champs Clés"),
            (len([f for f in social_fields if f]), "Réseaux Sociaux"),
            (len([f for f in contact_fields if f]), "Contact & Adresse"),
        ],
    ):
        with col:
            st.markdown('<div class="zen-metric">', unsafe_allow_html=True)
            st.markdown(
                f'<div class="zen-metric-value">{count}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="zen-metric-label">{label}</div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-title">02 / Édition des Champs</p>',
        unsafe_allow_html=True,
    )

    # IDENTITÉ
    st.markdown('<div class="zen-card">', unsafe_allow_html=True)
    st.markdown("**Identité**")

    col1, col2 = st.columns(2)
    with col1:
        master.brand_name = st.text_input(
            "Nom commercial", value=master.brand_name, key="edit_brand"
        )
        master.legal_name = st.text_input(
            "Raison sociale", value=master.legal_name, key="edit_legal"
        )
        org_types = [
            "Corporation",
            "LocalBusiness",
            "EducationalOrganization",
            "GovernmentOrganization",
            "NGO",
        ]
        idx = org_types.index(master.org_type) if master.org_type in org_types else 0
        master.org_type = st.selectbox("Type", org_types, index=idx, key="edit_type")

    with col2:
        master.description = st.text_area(
            "Description", value=master.description, height=100, key="edit_desc"
        )
        master.slogan = st.text_input(
            "Slogan", value=master.slogan, key="edit_slogan"
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # IDENTIFIANTS
    st.markdown('<div class="zen-card">', unsafe_allow_html=True)
    st.markdown("**Identifiants**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Wikidata QID", value=master.qid, disabled=True, key="view_qid")
        master.siren = st.text_input("SIREN", value=master.siren, key="edit_siren")
    with col2:
        master.siret = st.text_input("SIRET", value=master.siret, key="edit_siret")
        master.lei = st.text_input("LEI", value=master.lei, key="edit_lei")
    with col3:
        master.site_url = st.text_input(
            "Site web", value=master.site_url, key="edit_site"
        )
        master.ticker_symbol = st.text_input(
            "Ticker", value=master.ticker_symbol, key="edit_ticker"
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ADRESSE & CONTACT
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="zen-card">', unsafe_allow_html=True)
        st.markdown("**Adresse**")
        master.street = st.text_input("Rue", value=master.street, key="edit_street")
        col_city, col_zip = st.columns([2, 1])
        master.city = col_city.text_input("Ville", value=master.city, key="edit_city")
        master.zip_code = col_zip.text_input(
            "Code postal", value=master.zip_code, key="edit_zip"
        )
        master.region = st.text_input(
            "Région", value=master.region, key="edit_region"
        )
        master.country = st.text_input(
            "Pays", value=master.country, key="edit_country"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="zen-card">', unsafe_allow_html=True)
        st.markdown("**Contact**")
        master.phone = st.text_input(
            "Téléphone", value=master.phone, placeholder="+33 1 23 45 67 89", key="edit_phone"
        )
        master.email = st.text_input(
            "Email", value=master.email, placeholder="contact@exemple.fr", key="edit_email"
        )
        master.fax = st.text_input("Fax", value=master.fax, key="edit_fax")
        st.markdown("</div>", unsafe_allow_html=True)

    # RÉSEAUX SOCIAUX
    st.markdown('<div class="zen-card">', unsafe_allow_html=True)
    st.markdown("**Réseaux Sociaux**")

    col1, col2 = st.columns(2)
    with col1:
        master.wikipedia_url = st.text_input(
            "Wikipedia", value=master.wikipedia_url, key="edit_wiki"
        )
        master.linkedin_url = st.text_input(
            "LinkedIn", value=master.linkedin_url, key="edit_linkedin"
        )
        master.twitter_url = st.text_input(
            "Twitter/X", value=master.twitter_url, key="edit_twitter"
        )
        master.facebook_url = st.text_input(
            "Facebook", value=master.facebook_url, key="edit_facebook"
        )
    with col2:
        master.instagram_url = st.text_input(
            "Instagram", value=master.instagram_url, key="edit_instagram"
        )
        master.youtube_url = st.text_input(
            "YouTube", value=master.youtube_url, key="edit_youtube"
        )
        master.tiktok_url = st.text_input(
            "TikTok", value=master.tiktok_url, key="edit_tiktok"
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # VISUELS
    st.markdown('<div class="zen-card">', unsafe_allow_html=True)
    st.markdown("**Visuels**")

    col1, col2 = st.columns([2, 1])
    with col1:
        master.logo_url = st.text_input(
            "URL du logo", value=master.logo_url, key="edit_logo"
        )
    with col2:
        if master.logo_url:
            try:
                st.image(master.logo_url, width=150)
            except Exception:
                st.caption("Impossible de charger l'image")

    st.markdown("</div>", unsafe_allow_html=True)

    # CORPORATE
    with st.expander("Données corporate (optionnel)"):
        col1, col2, col3 = st.columns(3)
        with col1:
            master.founding_date = st.text_input(
                "Date de création", value=master.founding_date, placeholder="YYYY-MM-DD", key="edit_founding"
            )
            master.num_employees = st.text_input(
                "Nombre d'employés", value=master.num_employees, key="edit_employees"
            )
        with col2:
            master.founder_name = st.text_input(
                "Fondateur", value=master.founder_name, key="edit_founder"
            )
            master.parent_org = st.text_input(
                "Organisation mère", value=master.parent_org, key="edit_parent"
            )
        with col3:
            master.annual_revenue = st.text_input(
                "Chiffre d'affaires", value=master.annual_revenue, key="edit_revenue"
            )
            master.stock_exchange = st.text_input(
                "Bourse", value=master.stock_exchange, key="edit_exchange"
            )

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    # =====================================================================
    # ÉTAPE 3 : GÉNÉRATION JSON-LD
    # =====================================================================

    st.markdown(
        '<p class="section-title">03 / Génération du JSON-LD Master</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        if st.button(
            "GÉNÉRER LE JSON-LD",
            type="primary",
            use_container_width=True,
            key="generate_btn",
        ):
            with st.spinner("Génération en cours..."):
                builder = TemplateBuilder()
                jsonld_master = builder.generate_jsonld(
                    master_data=master, dynamic_data=None, page_data=None
                )
                st.session_state.jsonld_master = jsonld_master
                st.success("JSON-LD Master généré")
                st.rerun()

    if "jsonld_master" in st.session_state and st.session_state.jsonld_master:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="zen-card">', unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])

        with col1:
            st.code(
                st.session_state.jsonld_master, language="json", line_numbers=True
            )

        with col2:
            st.download_button(
                label="TÉLÉCHARGER",
                data=st.session_state.jsonld_master,
                file_name=f"master_{master.brand_name.lower().replace(' ', '_')}.json",
                mime="application/ld+json",
                use_container_width=True,
            )

            st.metric("Lignes", len(st.session_state.jsonld_master.split("\n")))
            st.metric("Taille", f"{len(st.session_state.jsonld_master)} chars")

            if st.button("NOUVEAU", use_container_width=True, key="reset_btn"):
                st.session_state.master_data = None
                st.session_state.pop("jsonld_master", None)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
