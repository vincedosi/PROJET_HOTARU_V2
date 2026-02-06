# =============================================================================
# MASTER TAB - VERSION UX ZEN MINIMALISTE
# =============================================================================

def render_master_tab():
    """Onglet MASTER - Interface Zen avec champs éditables"""
    
    # CSS Zen Minimaliste
    st.markdown("""
    <style>
        /* Layout principal */
        .master-container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        /* Cards élégantes */
        .zen-card {
            background: #ffffff;
            border: 1px solid #e5e5e5;
            padding: 32px;
            margin-bottom: 24px;
            transition: all 0.2s ease;
        }
        
        .dark .zen-card {
            background: #1a1a1a;
            border: 1px solid #333333;
        }
        
        .zen-card:hover {
            border-color: #000000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        
        /* Headers */
        .zen-title {
            font-size: 3rem;
            font-weight: 900;
            letter-spacing: -0.02em;
            text-transform: uppercase;
            line-height: 1;
            margin-bottom: 8px;
        }
        
        .zen-subtitle {
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #666;
            margin-bottom: 32px;
        }
        
        .section-title {
            font-size: 0.65rem;
            font-weight: 800;
            letter-spacing: 0.3em;
            text-transform: uppercase;
            color: #999;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        /* Status badges */
        .status-badge {
            display: inline-block;
            padding: 6px 16px;
            font-size: 0.65rem;
            font-weight: 800;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            border: 1px solid;
        }
        
        .status-complete {
            background: #000000;
            color: #ffffff;
            border-color: #000000;
        }
        
        .status-partial {
            background: #ffffff;
            color: #000000;
            border-color: #000000;
        }
        
        .status-failed {
            background: #f5f5f5;
            color: #666666;
            border-color: #cccccc;
        }
        
        /* Buttons */
        .zen-button {
            background: #000000;
            color: #ffffff;
            border: 1px solid #000000;
            padding: 14px 32px;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .zen-button:hover {
            background: #ffffff;
            color: #000000;
        }
        
        .zen-button-outline {
            background: #ffffff;
            color: #000000;
            border: 1px solid #000000;
        }
        
        .zen-button-outline:hover {
            background: #000000;
            color: #ffffff;
        }
        
        /* Inputs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            border: 1px solid #e5e5e5 !important;
            border-radius: 0 !important;
            font-size: 0.9rem !important;
            padding: 12px 16px !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #000000 !important;
            box-shadow: none !important;
        }
        
        /* Metrics */
        .zen-metric {
            text-align: center;
            padding: 24px;
            border: 1px solid #e5e5e5;
        }
        
        .zen-metric-value {
            font-size: 3rem;
            font-weight: 900;
            line-height: 1;
            margin-bottom: 8px;
        }
        
        .zen-metric-label {
            font-size: 0.65rem;
            font-weight: 700;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #999;
        }
        
        /* Grid */
        .zen-grid-2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
        }
        
        .zen-grid-3 {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px;
        }
        
        @media (max-width: 768px) {
            .zen-grid-2, .zen-grid-3 {
                grid-template-columns: 1fr;
            }
        }
        
        /* Divider */
        .zen-divider {
            height: 1px;
            background: #e5e5e5;
            margin: 48px 0;
        }
        
        /* Logo */
        .zen-logo {
            width: 48px;
            height: 48px;
            background: #000000;
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 1.2rem;
            margin-bottom: 32px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Container principal
    st.markdown('<div class="master-container">', unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="zen-logo">蛍</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="zen-title">MASTER DATA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="zen-subtitle">Données d\'Entité Permanentes / JSON-LD Foundation</p>', unsafe_allow_html=True)
    
    # Init session state
    if "master_data" not in st.session_state:
        st.session_state.master_data = None
    
    # =========================================================================
    # ÉTAPE 1 : RECHERCHE & ENRICHISSEMENT
    # =========================================================================
    
    st.markdown('<div class="zen-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-title">01 / Identification & Enrichissement</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        company_name = st.text_input(
            "Nom de l'organisation",
            placeholder="Ex: Airbus, BNP Paribas, Decathlon...",
            label_visibility="collapsed",
            key="company_search"
        )
    
    with col2:
        qid_manual = st.text_input(
            "QID Wikidata (optionnel)",
            placeholder="Ex: Q67",
            label_visibility="collapsed",
            key="qid_search"
        )
    
    with col3:
        siren_manual = st.text_input(
            "SIREN (optionnel)",
            placeholder="Ex: 351058151",
            label_visibility="collapsed",
            key="siren_search"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        if st.button("🔍 RECHERCHER", use_container_width=True, key="search_btn"):
            if company_name or qid_manual or siren_manual:
                with st.spinner("Interrogation de Wikidata..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_enrich(
                        search_query=company_name if company_name else None,
                        qid=qid_manual if qid_manual else None,
                        siren=siren_manual if siren_manual else None
                    )
                    st.rerun()
            else:
                st.error("⚠️ Entrez au moins un critère")
    
    with col_btn2:
        if st.button("🤖 ENRICHIR MISTRAL", use_container_width=True, key="enrich_btn", disabled=not st.session_state.master_data):
            mistral_key = get_mistral_key()
            if mistral_key and st.session_state.master_data.qid:
                with st.spinner("Mistral enrichit les données..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_complete_with_mistral(
                        st.session_state.master_data,
                        mistral_key
                    )
                    st.rerun()
            else:
                st.error("⚠️ Clé Mistral ou QID manquant")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # =========================================================================
    # ÉTAPE 2 : ÉDITION DES DONNÉES
    # =========================================================================
    
    if st.session_state.master_data:
        master = st.session_state.master_data
        
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        
        # Status
        status_class = {
            "complete": "status-complete",
            "partial": "status-partial",
            "failed": "status-failed"
        }.get(master.status, "status-partial")
        
        status_text = {
            "complete": "✓ Complet",
            "partial": "⚠ Partiel",
            "failed": "✕ Échec"
        }.get(master.status, "⚠ Partiel")
        
        st.markdown(f'<span class="status-badge {status_class}">{status_text}</span>', unsafe_allow_html=True)
        
        if master.errors:
            with st.expander("⚠️ Erreurs détectées"):
                for error in master.errors:
                    st.caption(error)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="zen-metric">', unsafe_allow_html=True)
            st.markdown(f'<div class="zen-metric-value">{len([f for f in [master.brand_name, master.qid, master.site_url] if f])}</div>', unsafe_allow_html=True)
            st.markdown('<div class="zen-metric-label">Champs Clés</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            social_count = len([f for f in [master.wikipedia_url, master.linkedin_url, master.twitter_url, master.facebook_url, master.instagram_url, master.youtube_url] if f])
            st.markdown('<div class="zen-metric">', unsafe_allow_html=True)
            st.markdown(f'<div class="zen-metric-value">{social_count}</div>', unsafe_allow_html=True)
            st.markdown('<div class="zen-metric-label">Réseaux Sociaux</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            contact_count = len([f for f in [master.phone, master.email, master.street, master.city] if f])
            st.markdown('<div class="zen-metric">', unsafe_allow_html=True)
            st.markdown(f'<div class="zen-metric-value">{contact_count}</div>', unsafe_allow_html=True)
            st.markdown('<div class="zen-metric-label">Contact & Adresse</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-title">02 / Édition des Champs</p>', unsafe_allow_html=True)
        
        # SECTION : IDENTITÉ
        st.markdown('<div class="zen-card">', unsafe_allow_html=True)
        st.markdown("**🏢 Identité**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            master.brand_name = st.text_input("Nom commercial", value=master.brand_name, key="edit_brand")
            master.legal_name = st.text_input("Raison sociale", value=master.legal_name, key="edit_legal")
            master.org_type = st.selectbox("Type", ["Corporation", "LocalBusiness", "EducationalOrganization", "GovernmentOrganization", "NGO"], 
                                          index=["Corporation", "LocalBusiness", "EducationalOrganization", "GovernmentOrganization", "NGO"].index(master.org_type) if master.org_type in ["Corporation", "LocalBusiness", "EducationalOrganization", "GovernmentOrganization", "NGO"] else 0,
                                          key="edit_type")
        
        with col2:
            master.description = st.text_area("Description", value=master.description, height=100, key="edit_desc")
            master.slogan = st.text_input("Slogan", value=master.slogan, key="edit_slogan")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # SECTION : IDENTIFIANTS
        st.markdown('<div class="zen-card">', unsafe_allow_html=True)
        st.markdown("**🆔 Identifiants**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.text_input("Wikidata QID", value=master.qid, disabled=True, key="view_qid")
            master.siren = st.text_input("SIREN", value=master.siren, key="edit_siren")
        
        with col2:
            master.siret = st.text_input("SIRET", value=master.siret, key="edit_siret")
            master.lei = st.text_input("LEI", value=master.lei, key="edit_lei")
        
        with col3:
            master.site_url = st.text_input("Site web", value=master.site_url, key="edit_site")
            master.ticker_symbol = st.text_input("Ticker", value=master.ticker_symbol, key="edit_ticker")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # SECTION : ADRESSE & CONTACT
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="zen-card">', unsafe_allow_html=True)
            st.markdown("**📍 Adresse**")
            
            master.street = st.text_input("Rue", value=master.street, key="edit_street")
            
            col_city, col_zip = st.columns([2, 1])
            with col_city:
                master.city = st.text_input("Ville", value=master.city, key="edit_city")
            with col_zip:
                master.zip_code = st.text_input("Code postal", value=master.zip_code, key="edit_zip")
            
            master.region = st.text_input("Région", value=master.region, key="edit_region")
            master.country = st.text_input("Pays", value=master.country, key="edit_country")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="zen-card">', unsafe_allow_html=True)
            st.markdown("**📞 Contact**")
            
            master.phone = st.text_input("Téléphone", value=master.phone, placeholder="+33 1 23 45 67 89", key="edit_phone")
            master.email = st.text_input("Email", value=master.email, placeholder="contact@exemple.fr", key="edit_email")
            master.fax = st.text_input("Fax", value=master.fax, key="edit_fax")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # SECTION : RÉSEAUX SOCIAUX
        st.markdown('<div class="zen-card">', unsafe_allow_html=True)
        st.markdown("**🌐 Réseaux Sociaux**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            master.wikipedia_url = st.text_input("Wikipedia", value=master.wikipedia_url, key="edit_wiki")
            master.linkedin_url = st.text_input("LinkedIn", value=master.linkedin_url, key="edit_linkedin")
            master.twitter_url = st.text_input("Twitter/X", value=master.twitter_url, key="edit_twitter")
            master.facebook_url = st.text_input("Facebook", value=master.facebook_url, key="edit_facebook")
        
        with col2:
            master.instagram_url = st.text_input("Instagram", value=master.instagram_url, key="edit_instagram")
            master.youtube_url = st.text_input("YouTube", value=master.youtube_url, key="edit_youtube")
            master.tiktok_url = st.text_input("TikTok", value=master.tiktok_url, key="edit_tiktok")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # SECTION : VISUELS
        st.markdown('<div class="zen-card">', unsafe_allow_html=True)
        st.markdown("**🎨 Visuels**")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            master.logo_url = st.text_input("URL du logo", value=master.logo_url, key="edit_logo")
        
        with col2:
            if master.logo_url:
                try:
                    st.image(master.logo_url, width=150)
                except:
                    st.caption("❌ Impossible de charger l'image")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # SECTION : CORPORATE (optionnel)
        with st.expander("📊 Données corporate (optionnel)"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                master.founding_date = st.text_input("Date de création", value=master.founding_date, placeholder="YYYY-MM-DD", key="edit_founding")
                master.num_employees = st.text_input("Nombre d'employés", value=master.num_employees, key="edit_employees")
            
            with col2:
                master.founder_name = st.text_input("Fondateur", value=master.founder_name, key="edit_founder")
                master.parent_org = st.text_input("Organisation mère", value=master.parent_org, key="edit_parent")
            
            with col3:
                master.annual_revenue = st.text_input("Chiffre d'affaires", value=master.annual_revenue, key="edit_revenue")
                master.stock_exchange = st.text_input("Bourse", value=master.stock_exchange, key="edit_exchange")
        
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        
        # =====================================================================
        # ÉTAPE 3 : GÉNÉRATION JSON-LD
        # =====================================================================
        
        st.markdown('<p class="section-title">03 / Génération du JSON-LD Master</p>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            if st.button("📥 GÉNÉRER LE JSON-LD", type="primary", use_container_width=True, key="generate_btn"):
                template_path = "template.json"
                if os.path.exists(template_path):
                    with st.spinner("⚙️ Génération en cours..."):
                        builder = TemplateBuilder(template_path)
                        jsonld_master = builder.generate_jsonld(
                            master_data=master,
                            dynamic_data=None,
                            page_data=None
                        )
                        
                        st.session_state.jsonld_master = jsonld_master
                        st.success("✅ JSON-LD Master généré")
                        st.rerun()
                else:
                    st.error("❌ Template introuvable")
        
        # Affichage du JSON-LD
        if "jsonld_master" in st.session_state and st.session_state.jsonld_master:
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown('<div class="zen-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.code(st.session_state.jsonld_master, language="json", line_numbers=True)
            
            with col2:
                st.download_button(
                    label="💾 TÉLÉCHARGER",
                    data=st.session_state.jsonld_master,
                    file_name=f"master_{master.brand_name.lower().replace(' ', '_')}.json",
                    mime="application/ld+json",
                    use_container_width=True
                )
                
                st.metric("Lignes", len(st.session_state.jsonld_master.split('\n')))
                st.metric("Taille", f"{len(st.session_state.jsonld_master)} chars")
                
                if st.button("🔄 NOUVEAU", use_container_width=True, key="reset_btn"):
                    st.session_state.master_data = None
                    if "jsonld_master" in st.session_state:
                        del st.session_state.jsonld_master
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Fermeture master-container
