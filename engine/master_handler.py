# =============================================================================
# MASTER TAB - VERSION UX MODERNE ET ORGANISÉE
# =============================================================================

def render_master_tab():
    """Onglet MASTER - Interface moderne et structurée"""
    
    # CSS personnalisé pour l'interface MASTER
    st.markdown("""
    <style>
        .master-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            margin-bottom: 20px;
        }
        .master-card h3 {
            color: #1a1a1a;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }
        .field-label {
            font-size: 0.85rem;
            color: #666;
            font-weight: 500;
            margin-bottom: 5px;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        .status-complete { background: #d4edda; color: #155724; }
        .status-partial { background: #fff3cd; color: #856404; }
        .status-failed { background: #f8d7da; color: #721c24; }
        .step-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .step-number {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #0066cc;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
        }
        .step-inactive {
            background: #ccc;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("# 🔮 MASTER - Données d'Entité Permanentes")
    st.markdown("**Créez le JSON-LD de base de votre organisation, identique sur toutes les pages**")
    st.divider()
    
    # Init session state
    if "master_data" not in st.session_state:
        st.session_state.master_data = None
    if "master_step" not in st.session_state:
        st.session_state.master_step = 1
    
    # =========================================================================
    # ÉTAPE 1 : RECHERCHE & ENRICHISSEMENT AUTO
    # =========================================================================
    
    st.markdown("""
    <div class="step-indicator">
        <div class="step-number">1</div>
        <div style="flex: 1;">
            <div style="font-weight: 600; margin-bottom: 3px;">Identification & Enrichissement</div>
            <div style="font-size: 0.85rem; color: #666;">Recherchez votre organisation et enrichissez automatiquement les données</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            company_name = st.text_input(
                "🔍 Nom de l'organisation",
                placeholder="Ex: Airbus, BNP Paribas, Decathlon...",
                help="Le système interroge automatiquement Wikidata pour récupérer les données publiques"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            enrich_btn = st.button("🚀 ENRICHIR", type="primary", use_container_width=True)
        
        # Options avancées (repliées par défaut)
        with st.expander("⚙️ Options avancées"):
            col1, col2 = st.columns(2)
            with col1:
                qid_manual = st.text_input("Wikidata QID", placeholder="Ex: Q67", help="Si vous connaissez le QID Wikidata")
            with col2:
                siren_manual = st.text_input("SIREN", placeholder="Ex: 351058151", help="Pour les entreprises françaises")
        
        # Lancement enrichissement
        if enrich_btn:
            if company_name or qid_manual or siren_manual:
                with st.spinner("🔄 Interrogation de Wikidata..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_enrich(
                        search_query=company_name if company_name else None,
                        qid=qid_manual if qid_manual else None,
                        siren=siren_manual if siren_manual else None
                    )
                    
                    # Auto-enrichissement Mistral si clé disponible
                    mistral_key = get_mistral_key()
                    if mistral_key and st.session_state.master_data.qid:
                        with st.spinner("🤖 Mistral enrichit les données..."):
                            st.session_state.master_data = handler.auto_complete_with_mistral(
                                st.session_state.master_data,
                                mistral_key
                            )
                    
                    st.session_state.master_step = 2
                    st.rerun()
            else:
                st.error("⚠️ Veuillez entrer au moins un critère de recherche")
    
    st.divider()
    
    # =========================================================================
    # ÉTAPE 2 : ÉDITION DES DONNÉES
    # =========================================================================
    
    if st.session_state.master_data:
        master = st.session_state.master_data
        
        # Status Badge
        if master.status == "complete":
            st.markdown('<span class="status-badge status-complete">✅ Enrichissement réussi</span>', unsafe_allow_html=True)
        elif master.status == "partial":
            st.markdown('<span class="status-badge status-partial">⚠️ Enrichissement partiel</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge status-failed">❌ Échec</span>', unsafe_allow_html=True)
        
        if master.errors:
            with st.expander("⚠️ Erreurs détectées"):
                for error in master.errors:
                    st.warning(error)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("""
        <div class="step-indicator">
            <div class="step-number">2</div>
            <div style="flex: 1;">
                <div style="font-weight: 600; margin-bottom: 3px;">Vérification & Édition</div>
                <div style="font-size: 0.85rem; color: #666;">Vérifiez et modifiez les données enrichies si nécessaire</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # =====================================================================
        # SECTION 1 : IDENTITÉ
        # =====================================================================
        
        with st.container():
            st.markdown('<div class="master-card"><h3>🏢 Identité</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                master.brand_name = st.text_input(
                    "Nom commercial *",
                    value=master.brand_name,
                    help="Nom de la marque tel qu'il apparaît publiquement"
                )
                
                master.legal_name = st.text_input(
                    "Raison sociale",
                    value=master.legal_name,
                    help="Nom juridique officiel de l'entreprise"
                )
                
                master.org_type = st.selectbox(
                    "Type d'organisation",
                    options=["Corporation", "LocalBusiness", "EducationalOrganization", "GovernmentOrganization", "NGO"],
                    index=0 if master.org_type == "Corporation" else 0
                )
            
            with col2:
                master.description = st.text_area(
                    "Description",
                    value=master.description,
                    height=100,
                    help="Description SEO optimisée (150-180 caractères recommandés)"
                )
                
                master.slogan = st.text_input(
                    "Slogan",
                    value=master.slogan,
                    help="Slogan ou tagline de la marque"
                )
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # =====================================================================
        # SECTION 2 : IDENTIFIANTS
        # =====================================================================
        
        with st.container():
            st.markdown('<div class="master-card"><h3>🆔 Identifiants</h3>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                master.qid = st.text_input("Wikidata QID", value=master.qid, disabled=True)
                master.siren = st.text_input("SIREN", value=master.siren)
            
            with col2:
                master.siret = st.text_input("SIRET", value=master.siret)
                master.lei = st.text_input("LEI", value=master.lei)
            
            with col3:
                master.site_url = st.text_input("Site web *", value=master.site_url)
                master.ticker_symbol = st.text_input("Ticker", value=master.ticker_symbol, help="Symbole boursier")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # =====================================================================
        # SECTION 3 : ADRESSE & CONTACT
        # =====================================================================
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="master-card"><h3>📍 Adresse</h3>', unsafe_allow_html=True)
            
            master.street = st.text_input("Rue", value=master.street)
            
            col_city, col_zip = st.columns([2, 1])
            with col_city:
                master.city = st.text_input("Ville", value=master.city)
            with col_zip:
                master.zip_code = st.text_input("Code postal", value=master.zip_code)
            
            master.region = st.text_input("Région", value=master.region)
            master.country = st.text_input("Pays", value=master.country)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="master-card"><h3>📞 Contact</h3>', unsafe_allow_html=True)
            
            master.phone = st.text_input("Téléphone", value=master.phone, placeholder="+33 1 23 45 67 89")
            master.email = st.text_input("Email", value=master.email, placeholder="contact@exemple.fr")
            master.fax = st.text_input("Fax", value=master.fax)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # =====================================================================
        # SECTION 4 : RÉSEAUX SOCIAUX
        # =====================================================================
        
        with st.container():
            st.markdown('<div class="master-card"><h3>🌐 Réseaux Sociaux & Web</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                master.wikipedia_url = st.text_input("Wikipedia", value=master.wikipedia_url)
                master.linkedin_url = st.text_input("LinkedIn", value=master.linkedin_url)
                master.twitter_url = st.text_input("Twitter/X", value=master.twitter_url)
                master.facebook_url = st.text_input("Facebook", value=master.facebook_url)
            
            with col2:
                master.instagram_url = st.text_input("Instagram", value=master.instagram_url)
                master.youtube_url = st.text_input("YouTube", value=master.youtube_url)
                master.tiktok_url = st.text_input("TikTok", value=master.tiktok_url)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # =====================================================================
        # SECTION 5 : VISUELS
        # =====================================================================
        
        with st.container():
            st.markdown('<div class="master-card"><h3>🎨 Visuels</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                master.logo_url = st.text_input("URL du logo", value=master.logo_url)
            
            with col2:
                if master.logo_url:
                    try:
                        st.image(master.logo_url, caption="Prévisualisation", width=200)
                    except:
                        st.caption("❌ Impossible de charger l'image")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # =====================================================================
        # SECTION 6 : DONNÉES CORPORATE
        # =====================================================================
        
        with st.expander("📊 Données corporate (optionnel)"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                master.founding_date = st.text_input("Date de création", value=master.founding_date, placeholder="YYYY-MM-DD")
                master.num_employees = st.text_input("Nombre d'employés", value=master.num_employees)
            
            with col2:
                master.founder_name = st.text_input("Fondateur", value=master.founder_name)
                master.parent_org = st.text_input("Organisation mère", value=master.parent_org)
            
            with col3:
                master.annual_revenue = st.text_input("Chiffre d'affaires", value=master.annual_revenue)
                master.stock_exchange = st.text_input("Bourse", value=master.stock_exchange)
        
        st.divider()
        
        # =====================================================================
        # ÉTAPE 3 : GÉNÉRATION JSON-LD
        # =====================================================================
        
        st.markdown("""
        <div class="step-indicator">
            <div class="step-number">3</div>
            <div style="flex: 1;">
                <div style="font-weight: 600; margin-bottom: 3px;">Génération du JSON-LD</div>
                <div style="font-size: 0.85rem; color: #666;">Générez le JSON-LD master à intégrer sur toutes vos pages</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("📥 GÉNÉRER LE JSON-LD MASTER", type="primary", use_container_width=True):
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
                        st.success("✅ JSON-LD Master généré avec succès")
                        st.session_state.master_step = 3
                        st.rerun()
                else:
                    st.error("❌ Template introuvable. Vérifiez que template.json existe.")
        
        # Affichage du JSON-LD si généré
        if "jsonld_master" in st.session_state and st.session_state.jsonld_master:
            st.markdown("<br>", unsafe_allow_html=True)
            
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
                
                # Bouton reset
                if st.button("🔄 NOUVELLE RECHERCHE", use_container_width=True):
                    st.session_state.master_data = None
                    st.session_state.master_step = 1
                    if "jsonld_master" in st.session_state:
                        del st.session_state.jsonld_master
                    st.rerun()
