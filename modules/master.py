"""
HOTARU v3 - Module MASTER DATA
Interface Brutaliste Monochrome pour l'enrichissement et l'edition des donnees d'entite
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
    """Onglet MASTER - Interface Brutaliste avec champs editables"""

    if "master_data" not in st.session_state:
        st.session_state.master_data = None

    # Header
    st.markdown('<h1 class="zen-title">MASTER DATA</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="zen-subtitle">PERMANENT ENTITY DATA // JSON-LD FOUNDATION</p>',
        unsafe_allow_html=True,
    )

    # =========================================================================
    # ETAPE 1 : RECHERCHE & ENRICHISSEMENT
    # =========================================================================

    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">'
        '<span class="step-badge">01</span>'
        '<span class="section-title" style="margin-bottom:0;">IDENTIFICATION & ENRICHISSEMENT</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-container">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        company_name = st.text_input(
            "ENTITY NAME",
            placeholder="ENTITY NAME",
            key="company_search",
        )

    with col2:
        qid_manual = st.text_input(
            "WIKIDATA QID",
            placeholder="Q-IDENTIFIER",
            key="qid_search",
        )

    with col3:
        siren_manual = st.text_input(
            "SIRET",
            placeholder="ID NUMBER",
            key="siren_search",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    with col_btn1:
        if st.button("SEARCH", use_container_width=True, key="search_btn"):
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
                st.error("Entrez au moins un critere")

    with col_btn2:
        if st.button(
            "MISTRAL ENRICH",
            use_container_width=True,
            key="enrich_btn",
            type="primary",
            disabled=not st.session_state.master_data,
        ):
            mistral_key = _get_mistral_key()
            if mistral_key and st.session_state.master_data.qid:
                with st.spinner("Mistral enrichit les donnees..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_complete_with_mistral(
                        st.session_state.master_data, mistral_key
                    )
                    st.rerun()
            else:
                st.error("Cle Mistral ou QID manquant")

    st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # ETAPE 2 : EDITION DES DONNEES
    # =========================================================================

    if not st.session_state.master_data:
        return

    master = st.session_state.master_data

    st.markdown("<br>", unsafe_allow_html=True)

    # Status + Metrics row
    col_status, col_m1, col_m2, col_m3 = st.columns([1.2, 1, 1, 1])

    with col_status:
        status_map = {
            "complete": ("status-complete", "COMPLET"),
            "partial": ("status-partial", "PARTIEL"),
            "failed": ("status-failed", "ECHEC"),
        }
        cls, txt = status_map.get(master.status, ("status-partial", "PARTIEL"))
        st.markdown(
            f'<span class="status-badge {cls}">STATUS: {txt}</span>',
            unsafe_allow_html=True,
        )

        if master.errors:
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown(
                '<div style="border:1px solid rgba(0,0,0,0.12);padding:12px;">'
                '<span class="label-caps">LOGS / ERRORS</span>',
                unsafe_allow_html=True,
            )
            for error in master.errors:
                st.markdown(
                    f'<div style="font-size:0.75rem;color:rgba(0,0,0,0.55);margin-top:4px;">{error}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)

    key_fields = [master.brand_name, master.qid, master.site_url]
    social_fields = [
        master.wikipedia_url, master.linkedin_url, master.twitter_url,
        master.facebook_url, master.instagram_url, master.youtube_url,
    ]
    contact_fields = [master.phone, master.email, master.street, master.city]

    for col, (count, label) in zip(
        [col_m1, col_m2, col_m3],
        [
            (len([f for f in key_fields if f]), "KEY FIELDS"),
            (len([f for f in social_fields if f]), "SOCIAL NETS"),
            (len([f for f in contact_fields if f]), "CONTACT DATA"),
        ],
    ):
        with col:
            st.markdown(
                f'<div class="zen-metric">'
                f'<div class="zen-metric-value">{count:02d}</div>'
                f'<div class="zen-metric-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">'
        '<span class="step-badge">02</span>'
        '<span class="section-title" style="margin-bottom:0;">FIELD MANAGEMENT</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # IDENTITE
    st.markdown(
        '<div class="section-container" style="padding:0;margin-bottom:24px;">'
        '<div class="section-header">IDENTITY</div>'
        '<div style="padding:24px;">',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        master.brand_name = st.text_input(
            "TRADE NAME", value=master.brand_name, key="edit_brand"
        )
        master.legal_name = st.text_input(
            "LEGAL NAME", value=master.legal_name, key="edit_legal"
        )
        org_types = [
            "Corporation", "LocalBusiness", "EducationalOrganization",
            "GovernmentOrganization", "NGO",
        ]
        idx = org_types.index(master.org_type) if master.org_type in org_types else 0
        master.org_type = st.selectbox(
            "ORGANIZATION TYPE", org_types, index=idx, key="edit_type"
        )

    with col2:
        master.description = st.text_area(
            "DESCRIPTION", value=master.description, height=100, key="edit_desc"
        )
        master.slogan = st.text_input(
            "SLOGAN", value=master.slogan, key="edit_slogan"
        )

    st.markdown('</div></div>', unsafe_allow_html=True)

    # IDENTIFIANTS
    st.markdown(
        '<div class="section-container" style="padding:0;margin-bottom:24px;">'
        '<div class="section-header">IDENTIFIERS</div>'
        '<div style="padding:24px;">',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("WIKIDATA", value=master.qid, disabled=True, key="view_qid")
        master.siren = st.text_input("SIREN", value=master.siren, key="edit_siren")
    with col2:
        master.siret = st.text_input("SIRET", value=master.siret, key="edit_siret")
        master.lei = st.text_input("LEI", value=master.lei, key="edit_lei")
    with col3:
        master.site_url = st.text_input(
            "WEBSITE", value=master.site_url, key="edit_site"
        )
        master.ticker_symbol = st.text_input(
            "TICKER", value=master.ticker_symbol, key="edit_ticker"
        )

    st.markdown('</div></div>', unsafe_allow_html=True)

    # RESEAUX SOCIAUX
    st.markdown(
        '<div class="section-container" style="padding:0;margin-bottom:24px;">'
        '<div class="section-header">SOCIAL PRESENCE</div>'
        '<div style="padding:24px;">',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        master.linkedin_url = st.text_input(
            "LINKEDIN", value=master.linkedin_url, key="edit_linkedin"
        )
        master.twitter_url = st.text_input(
            "X / TWITTER", value=master.twitter_url, key="edit_twitter"
        )
        master.facebook_url = st.text_input(
            "FACEBOOK", value=master.facebook_url, key="edit_facebook"
        )
    with col2:
        master.youtube_url = st.text_input(
            "YOUTUBE", value=master.youtube_url, key="edit_youtube"
        )
        master.tiktok_url = st.text_input(
            "TIKTOK", value=master.tiktok_url, key="edit_tiktok"
        )
        master.instagram_url = st.text_input(
            "INSTAGRAM", value=master.instagram_url, key="edit_instagram"
        )

    st.markdown('</div></div>', unsafe_allow_html=True)

    # VISUELS
    st.markdown(
        '<div class="section-container" style="padding:0;margin-bottom:24px;">'
        '<div class="section-header">VISUAL ASSETS</div>'
        '<div style="padding:24px;">',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        master.logo_url = st.text_input(
            "LOGO URL", value=master.logo_url, key="edit_logo"
        )
    with col2:
        if master.logo_url:
            try:
                st.image(master.logo_url, width=150)
            except Exception:
                st.caption("Impossible de charger l'image")
        else:
            if st.button("PREVIEW", use_container_width=True, key="preview_logo"):
                pass

    st.markdown('</div></div>', unsafe_allow_html=True)

    # CORPORATE
    with st.expander("OPTIONAL CORPORATE DATA"):
        col1, col2, col3 = st.columns(3)
        with col1:
            master.founding_date = st.text_input(
                "DATE DE CREATION", value=master.founding_date,
                placeholder="YYYY-MM-DD", key="edit_founding"
            )
            master.num_employees = st.text_input(
                "NOMBRE D'EMPLOYES", value=master.num_employees, key="edit_employees"
            )
        with col2:
            master.founder_name = st.text_input(
                "FONDATEUR", value=master.founder_name, key="edit_founder"
            )
            master.parent_org = st.text_input(
                "ORGANISATION MERE", value=master.parent_org, key="edit_parent"
            )
        with col3:
            master.annual_revenue = st.text_input(
                "CHIFFRE D'AFFAIRES", value=master.annual_revenue, key="edit_revenue"
            )
            master.stock_exchange = st.text_input(
                "BOURSE", value=master.stock_exchange, key="edit_exchange"
            )

    # ADRESSE & CONTACT
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            '<div class="section-container" style="padding:0;margin-bottom:24px;">'
            '<div class="section-header">ADDRESS</div>'
            '<div style="padding:24px;">',
            unsafe_allow_html=True,
        )
        master.street = st.text_input("RUE", value=master.street, key="edit_street")
        col_city, col_zip = st.columns([2, 1])
        master.city = col_city.text_input("VILLE", value=master.city, key="edit_city")
        master.zip_code = col_zip.text_input(
            "CODE POSTAL", value=master.zip_code, key="edit_zip"
        )
        master.region = st.text_input(
            "REGION", value=master.region, key="edit_region"
        )
        master.country = st.text_input(
            "PAYS", value=master.country, key="edit_country"
        )
        st.markdown('</div></div>', unsafe_allow_html=True)

    with col2:
        st.markdown(
            '<div class="section-container" style="padding:0;margin-bottom:24px;">'
            '<div class="section-header">CONTACT</div>'
            '<div style="padding:24px;">',
            unsafe_allow_html=True,
        )
        master.phone = st.text_input(
            "TELEPHONE", value=master.phone,
            placeholder="+33 1 23 45 67 89", key="edit_phone"
        )
        master.email = st.text_input(
            "EMAIL", value=master.email,
            placeholder="contact@exemple.fr", key="edit_email"
        )
        master.fax = st.text_input("FAX", value=master.fax, key="edit_fax")
        master.wikipedia_url = st.text_input(
            "WIKIPEDIA", value=master.wikipedia_url, key="edit_wiki"
        )
        st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    # =====================================================================
    # ETAPE 3 : GENERATION JSON-LD
    # =====================================================================

    st.markdown(
        '<div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:20px;">'
        '<span class="step-badge">03</span>'
        '<span class="section-title" style="margin-bottom:0;">COMPILATION</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        if st.button(
            "GENERER LE JSON-LD",
            type="primary",
            use_container_width=True,
            key="generate_btn",
        ):
            with st.spinner("Generation en cours..."):
                builder = TemplateBuilder()
                jsonld_master = builder.generate_jsonld(
                    master_data=master, dynamic_data=None, page_data=None
                )
                st.session_state.jsonld_master = jsonld_master
                st.success("JSON-LD Master genere")
                st.rerun()

    if "jsonld_master" in st.session_state and st.session_state.jsonld_master:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-container">', unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])

        with col1:
            st.code(
                st.session_state.jsonld_master, language="json", line_numbers=True
            )

        with col2:
            st.download_button(
                label="TELECHARGER",
                data=st.session_state.jsonld_master,
                file_name=f"master_{master.brand_name.lower().replace(' ', '_')}.json",
                mime="application/ld+json",
                use_container_width=True,
            )

            st.metric("LIGNES", len(st.session_state.jsonld_master.split("\n")))
            st.metric("TAILLE", f"{len(st.session_state.jsonld_master)} chars")

            if st.button("NOUVEAU", use_container_width=True, key="reset_btn"):
                st.session_state.master_data = None
                st.session_state.pop("jsonld_master", None)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
