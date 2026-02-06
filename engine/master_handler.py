# =============================================================================
# MASTER TAB - NOUVELLE UX PROFESSIONNELLE
# =============================================================================
# Remplace la fonction render_master_tab() dans app.py

def render_master_tab():
    """Onglet MASTER - Interface Pro Minimaliste"""
    
    # CSS Pro Design
    st.markdown("""
    <style>
        /* Reset & Base */
        .master-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        /* Header */
        .master-header {
            margin-bottom: 48px;
        }
        
        .master-title {
            font-family: 'Inter', -apple-system, sans-serif;
            font-size: 3rem;
            font-weight: 900;
            font-style: italic;
            letter-spacing: -0.03em;
            color: #000;
            margin: 0;
            line-height: 1;
        }
        
        .master-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 0.7rem;
            font-weight: 500;
            letter-spacing: 0.25em;
            text-transform: uppercase;
            color: #888;
            margin-top: 8px;
        }
        
        /* Section Numbers */
        .section-number {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            background: #000;
            color: #fff;
            font-size: 0.65rem;
            font-weight: 700;
            border-radius: 4px;
            margin-right: 12px;
        }
        
        .section-label {
            font-family: 'Inter', sans-serif;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #000;
        }
        
        .section-header {
            display: flex;
            align-items: center;
            margin-bottom: 24px;
            margin-top: 48px;
        }
        
        /* Cards */
        .pro-card {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 16px;
        }
        
        .pro-card-header {
            background: #1a1a1a;
            color: #fff;
            padding: 12px 20px;
            border-radius: 6px;
            margin: -24px -24px 24px -24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .pro-card-header-icon {
            font-size: 1rem;
        }
        
        .pro-card-header-text {
            font-family: 'Inter', sans-serif;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.15em;
            text-transform: uppercase;
        }
        
        /* Status Badge */
        .status-box {
            background: #f8f8f8;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 24px;
        }
        
        .status-label {
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #666;
            margin-bottom: 4px;
        }
        
        .status-value {
            font-size: 0.85rem;
            font-weight: 600;
            color: #000;
        }
        
        .status-partial { color: #f59e0b; }
        .status-complete { color: #10b981; }
        .status-failed { color: #ef4444; }
        
        /* Metrics */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }
        
        .metric-box {
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }
        
        .metric-value {
            font-family: 'Inter', sans-serif;
            font-size: 2.5rem;
            font-weight: 800;
            color: #000;
            line-height: 1;
            margin-bottom: 8px;
        }
        
        .metric-label {
            font-size: 0.6rem;
            font-weight: 700;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #888;
        }
        
        /* Errors Box */
        .errors-box {
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 6px;
            padding: 12px 16px;
            margin-top: 12px;
        }
        
        .errors-title {
            font-size: 0.7rem;
            font-weight: 700;
            color: #dc2626;
            margin-bottom: 4px;
        }
        
        .errors-text {
            font-size: 0.75rem;
            color: #991b1b;
            font-family: 'SF Mono', 'Monaco', monospace;
        }
        
        /* Input Fields */
        .field-label {
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #666;
            margin-bottom: 6px;
        }
        
        /* Buttons */
        .btn-search {
            background: #fff !important;
            color: #000 !important;
            border: 1px solid #000 !important;
            font-weight: 700 !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            font-size: 0.75rem !important;
        }
        
        .btn-primary {
            background: #000 !important;
            color: #fff !important;
            border: none !important;
            font-weight: 700 !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            font-size: 0.75rem !important;
        }
        
        .btn-generate {
            background: #000 !important;
            color: #fff !important;
            border: none !important;
            padding: 16px 48px !important;
            font-weight: 700 !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            font-size: 0.8rem !important;
            border-radius: 6px !important;
        }
        
        /* Preview Button */
        .preview-btn {
            background: #f5f5f5;
            border: 1px solid #e5e5e5;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 0.7rem;
            font-weight: 600;
            color: #333;
            cursor: pointer;
        }
        
        /* Social Icons */
        .social-icon {
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f5f5f5;
            border-radius: 6px;
            margin-right: 12px;
        }
        
        /* Collapsible */
        .collapse-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            background: #fafafa;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            cursor: pointer;
        }
        
        .collapse-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #333;
        }
        
        /* Divider */
        .section-divider {
            height: 1px;
            background: #e5e5e5;
            margin: 48px 0;
        }
        
        /* Footer */
        .app-footer {
            text-align: center;
            padding: 32px 0;
            border-top: 1px solid #e5e5e5;
            margin-top: 64px;
        }
        
        .footer-text {
            font-size: 0.7rem;
            font-weight: 500;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #999;
        }
        
        /* Hide Streamlit elements */
        .stTextInput > label,
        .stTextArea > label,
        .stSelectbox > label {
            font-size: 0.65rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
            color: #666 !important;
        }
        
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            border: 1px solid #e5e5e5 !important;
            border-radius: 6px !important;
            font-size: 0.9rem !important;
            padding: 12px 16px !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #000 !important;
            box-shadow: none !important;
        }
        
        .stSelectbox > div > div {
            border: 1px solid #e5e5e5 !important;
            border-radius: 6px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Container
    st.markdown('<div class="master-container">', unsafe_allow_html=True)
    
    # =========================================================================
    # HEADER
    # =========================================================================
    st.markdown('''
        <div class="master-header">
            <h1 class="master-title">MASTER DATA</h1>
            <p class="master-subtitle">Permanent Entity Data // JSON-LD Foundation</p>
        </div>
    ''', unsafe_allow_html=True)
    
    # Init session state
    if "master_data" not in st.session_state:
        st.session_state.master_data = None
    
    # =========================================================================
    # SECTION 01: IDENTIFICATION & ENRICHMENT
    # =========================================================================
    st.markdown('''
        <div class="section-header">
            <span class="section-number">01</span>
            <span class="section-label">Identification & Enrichment</span>
        </div>
    ''', unsafe_allow_html=True)
    
    # Search inputs
    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    
    with col1:
        entity_name = st.text_input(
            "ENTITY NAME",
            placeholder="Entity name",
            key="search_entity"
        )
    
    with col2:
        wikidata_qid = st.text_input(
            "WIKIDATA QID",
            placeholder="Q-Identifier",
            key="search_qid"
        )
    
    with col3:
        siret_input = st.text_input(
            "SIRET",
            placeholder="ID Number",
            key="search_siret"
        )
    
    # Buttons
    col_btn1, col_btn2, col_spacer = st.columns([1, 1.2, 2])
    
    with col_btn1:
        search_clicked = st.button("🔍  SEARCH", use_container_width=True, key="btn_search")
    
    with col_btn2:
        enrich_clicked = st.button("⚡ MISTRAL ENRICH", use_container_width=True, type="primary", key="btn_enrich")
    
    # Handle search
    if search_clicked:
        if entity_name or wikidata_qid or siret_input:
            with st.spinner("Searching Wikidata..."):
                handler = MasterDataHandler()
                st.session_state.master_data = handler.auto_enrich(
                    search_query=entity_name if entity_name else None,
                    qid=wikidata_qid if wikidata_qid else None,
                    siren=siret_input[:9] if siret_input else None  # SIREN = first 9 digits of SIRET
                )
                st.rerun()
        else:
            st.error("Please enter at least one search criteria")
    
    # Handle Mistral enrichment
    if enrich_clicked:
        if st.session_state.master_data:
            mistral_key = get_mistral_key()
            if mistral_key:
                with st.spinner("Mistral AI is enriching data..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_complete_with_mistral(
                        st.session_state.master_data,
                        mistral_key
                    )
                    st.rerun()
            else:
                st.error("Mistral API key not found in secrets.toml")
        else:
            st.warning("Please search for an entity first")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # =========================================================================
    # STATUS & METRICS
    # =========================================================================
    if st.session_state.master_data:
        master = st.session_state.master_data
        
        # Status row
        col_status, col_m1, col_m2, col_m3, col_m4 = st.columns([1.5, 1, 1, 1, 1])
        
        with col_status:
            status_class = {
                "complete": "status-complete",
                "partial": "status-partial", 
                "failed": "status-failed"
            }.get(master.status, "status-partial")
            
            status_icon = {
                "complete": "✓",
                "partial": "⚠",
                "failed": "✕"
            }.get(master.status, "⚠")
            
            st.markdown(f'''
                <div class="status-box">
                    <div class="status-label">{status_icon} Status: {master.status.upper()}</div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Errors
            if master.errors:
                st.markdown(f'''
                    <div class="errors-box">
                        <div class="errors-title">⚠ LOGS / ERRORS</div>
                        <div class="errors-text">{master.errors[0] if master.errors else ''}</div>
                    </div>
                ''', unsafe_allow_html=True)
        
        # Metrics
        key_fields = len([f for f in [master.brand_name, master.qid, master.site_url, master.description] if f])
        social_nets = len([f for f in [master.wikipedia_url, master.linkedin_url, master.twitter_url, 
                                        master.facebook_url, master.instagram_url, master.youtube_url] if f])
        contact_data = len([f for f in [master.phone, master.email, master.street, master.city] if f])
        
        with col_m1:
            st.metric("KEY FIELDS", f"{key_fields:02d}")
        with col_m2:
            st.metric("SOCIAL NETS", f"{social_nets:02d}")
        with col_m3:
            st.metric("CONTACT DATA", f"{contact_data:02d}")
        with col_m4:
            total = master.count_filled_fields()
            st.metric("TOTAL", f"{total:02d}")
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # =====================================================================
        # SECTION 02: FIELD MANAGEMENT
        # =====================================================================
        st.markdown('''
            <div class="section-header">
                <span class="section-number">02</span>
                <span class="section-label">Field Management</span>
            </div>
        ''', unsafe_allow_html=True)
        
        # ----- IDENTITY CARD -----
        st.markdown('''
            <div class="pro-card">
                <div class="pro-card-header">
                    <span class="pro-card-header-icon">🏢</span>
                    <span class="pro-card-header-text">Identity</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            master.brand_name = st.text_input("TRADE NAME", value=master.brand_name, key="f_brand")
            master.legal_name = st.text_input("LEGAL NAME", value=master.legal_name, key="f_legal")
            master.org_type = st.selectbox(
                "ORGANIZATION TYPE",
                ["Corporation", "LocalBusiness", "EducationalOrganization", "GovernmentOrganization", "NGO"],
                index=["Corporation", "LocalBusiness", "EducationalOrganization", "GovernmentOrganization", "NGO"].index(master.org_type) if master.org_type in ["Corporation", "LocalBusiness", "EducationalOrganization", "GovernmentOrganization", "NGO"] else 0,
                key="f_orgtype"
            )
        
        with col2:
            master.description = st.text_area("DESCRIPTION", value=master.description, height=100, key="f_desc")
            master.slogan = st.text_input("SLOGAN", value=master.slogan, key="f_slogan")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ----- IDENTIFIERS CARD -----
        st.markdown('''
            <div class="pro-card">
                <div class="pro-card-header">
                    <span class="pro-card-header-icon">🔖</span>
                    <span class="pro-card-header-text">Identifiers</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.text_input("WIKIDATA", value=master.qid, disabled=True, key="f_qid")
        with col2:
            master.siret = st.text_input("SIRET", value=master.siret, key="f_siret")
        with col3:
            master.site_url = st.text_input("WEBSITE", value=master.site_url, key="f_website")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ----- SOCIAL PRESENCE CARD -----
        st.markdown('''
            <div class="pro-card">
                <div class="pro-card-header">
                    <span class="pro-card-header-icon">🔗</span>
                    <span class="pro-card-header-text">Social Presence</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            master.linkedin_url = st.text_input("🔗 LINKEDIN", value=master.linkedin_url, key="f_linkedin")
            master.twitter_url = st.text_input("🐦 X / TWITTER", value=master.twitter_url, key="f_twitter")
            master.facebook_url = st.text_input("📘 FACEBOOK", value=master.facebook_url, key="f_facebook")
        
        with col2:
            master.youtube_url = st.text_input("▶️ YOUTUBE", value=master.youtube_url, key="f_youtube")
            master.tiktok_url = st.text_input("🎵 TIKTOK", value=master.tiktok_url, key="f_tiktok")
            master.instagram_url = st.text_input("📷 INSTAGRAM", value=master.instagram_url, key="f_instagram")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ----- VISUAL ASSETS CARD -----
        st.markdown('''
            <div class="pro-card">
                <div class="pro-card-header">
                    <span class="pro-card-header-icon">🖼️</span>
                    <span class="pro-card-header-text">Visual Assets</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            master.logo_url = st.text_input("LOGO URL", value=master.logo_url, key="f_logo")
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("PREVIEW", use_container_width=True, key="btn_preview"):
                if master.logo_url:
                    try:
                        st.image(master.logo_url, width=150)
                    except:
                        st.error("Cannot load image")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ----- OPTIONAL CORPORATE DATA -----
        with st.expander("📊 OPTIONAL CORPORATE DATA", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                master.founding_date = st.text_input("FOUNDING DATE", value=master.founding_date, placeholder="YYYY-MM-DD", key="f_founding")
                master.num_employees = st.text_input("EMPLOYEES", value=master.num_employees, key="f_employees")
            
            with col2:
                master.founder_name = st.text_input("FOUNDER", value=master.founder_name, key="f_founder")
                master.parent_org = st.text_input("PARENT ORG", value=master.parent_org, key="f_parent")
            
            with col3:
                master.annual_revenue = st.text_input("REVENUE", value=master.annual_revenue, key="f_revenue")
                master.ticker_symbol = st.text_input("TICKER", value=master.ticker_symbol, key="f_ticker")
                master.stock_exchange = st.text_input("EXCHANGE", value=master.stock_exchange, key="f_exchange")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Address
            st.markdown("**📍 ADDRESS**")
            col1, col2 = st.columns(2)
            
            with col1:
                master.street = st.text_input("STREET", value=master.street, key="f_street")
                master.city = st.text_input("CITY", value=master.city, key="f_city")
                master.zip_code = st.text_input("ZIP CODE", value=master.zip_code, key="f_zip")
            
            with col2:
                master.region = st.text_input("REGION", value=master.region, key="f_region")
                master.country = st.text_input("COUNTRY", value=master.country, key="f_country")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Contact
            st.markdown("**📞 CONTACT**")
            col1, col2 = st.columns(2)
            
            with col1:
                master.phone = st.text_input("PHONE", value=master.phone, placeholder="+33 1 23 45 67 89", key="f_phone")
            
            with col2:
                master.email = st.text_input("EMAIL", value=master.email, placeholder="contact@example.com", key="f_email")
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # =====================================================================
        # SECTION 03: COMPILATION
        # =====================================================================
        st.markdown('''
            <div class="section-header" style="justify-content: center; text-align: center;">
                <span class="section-number">03</span>
                <span class="section-label">Compilation</span>
            </div>
        ''', unsafe_allow_html=True)
        
        # Center the generate button
        col_spacer1, col_btn, col_spacer2 = st.columns([1, 2, 1])
        
        with col_btn:
            if st.button("{ }  GÉNÉRER LE JSON-LD", use_container_width=True, type="primary", key="btn_generate"):
                template_path = "template.json"
                if os.path.exists(template_path):
                    with st.spinner("Generating JSON-LD..."):
                        builder = TemplateBuilder(template_path)
                        jsonld_master = builder.generate_jsonld(
                            master_data=master,
                            dynamic_data=None,
                            page_data=None
                        )
                        st.session_state.jsonld_master = jsonld_master
                        st.success("✅ JSON-LD Master generated!")
                        st.rerun()
                else:
                    st.error("❌ Template not found")
        
        # Display generated JSON-LD
        if "jsonld_master" in st.session_state and st.session_state.jsonld_master:
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.code(st.session_state.jsonld_master, language="json", line_numbers=True)
            
            with col2:
                st.download_button(
                    label="💾 DOWNLOAD",
                    data=st.session_state.jsonld_master,
                    file_name=f"master_{master.brand_name.lower().replace(' ', '_')}.json",
                    mime="application/ld+json",
                    use_container_width=True
                )
                
                st.metric("Lines", len(st.session_state.jsonld_master.split('\n')))
                st.metric("Size", f"{len(st.session_state.jsonld_master)} chars")
                
                if st.button("🔄 NEW", use_container_width=True, key="btn_reset"):
                    st.session_state.master_data = None
                    if "jsonld_master" in st.session_state:
                        del st.session_state.jsonld_master
                    st.rerun()
    
    else:
        # Empty state
        st.markdown("""
            <div style="text-align: center; padding: 60px 20px; color: #999;">
                <p style="font-size: 3rem; margin-bottom: 16px;">🔍</p>
                <p style="font-size: 0.85rem; font-weight: 500;">Search for an entity to start building your Master Data</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close master-container
