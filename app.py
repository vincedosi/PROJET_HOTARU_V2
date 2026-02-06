# =============================================================================
# APP.PY
# =============================================================================

# Force refresh 2025-02-06
import streamlit as st
import os
import sys
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

# Add paths
sys.path.append(".")

from core.auth import AuthManager
from modules.home import render_home_guide
from modules.audit_geo import render_audit_geo
from engine.master_handler import MasterDataHandler, MasterData
from engine.dynamic_handler import DynamicDataHandler
from engine.template_builder import TemplateBuilder

# =============================================================================
# VERSION
# =============================================================================
VERSION = "2.4.0"
BUILD_DATE = "2025-02-04"
BUILD_ID = "AUTO-ENRICH"

# =============================================================================
# CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="Hotaru Strategic",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_styles():
    """Charge le CSS Hotaru"""
    css_path = "assets/style.css"
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def get_mistral_key():
    """Récupère la clé Mistral depuis secrets.toml"""
    try:
        return st.secrets["mistral"]["api_key"]
    except:
        return os.getenv("MISTRAL_API_KEY", "")

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

# =============================================================================
# LEAF TAB
# =============================================================================
def render_leaf_tab():
    """Onglet LEAF - JSON-LD spécifique à la page"""
    
    st.markdown("# LEAF - Données Spécifiques à la Page")
    st.markdown("**Analysez une page web et générez son JSON-LD enrichi par IA avec comparatif visuel**")
    st.markdown("---")
    
    # Check if master exists
    if "master_data" not in st.session_state or not st.session_state.master_data:
        st.warning("⚠️ Vous devez d'abord créer le JSON-LD MASTER dans l'onglet précédent")
        return
    
    # Init session state
    if "page_url" not in st.session_state:
        st.session_state.page_url = ""
    if "page_content" not in st.session_state:
        st.session_state.page_content = None
    if "existing_jsonld" not in st.session_state:
        st.session_state.existing_jsonld = None
    if "dynamic_data" not in st.session_state:
        st.session_state.dynamic_data = None
    
    # URL Input
    st.markdown("### ÉTAPE 1: Analyse de la Page")
    st.markdown("Entrez l'URL d'une page de votre site pour l'analyser et générer son JSON-LD enrichi")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        page_url = st.text_input(
            "URL de la page à analyser",
            placeholder="https://example.com/article/mon-article",
            help="Le système va scraper la page, extraire le JSON-LD existant, et générer une version enrichie"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("ANALYSER LA PAGE", type="primary", use_container_width=True):
            if page_url:
                with st.spinner("Scraping et analyse de la page..."):
                    try:
                        # Scrape page
                        response = requests.get(page_url, timeout=10, headers={
                            'User-Agent': 'Mozilla/5.0 (compatible; Hotaru/1.0)'
                        })
                        response.raise_for_status()
                        
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract existing JSON-LD
                        existing_jsonld = None
                        jsonld_scripts = soup.find_all('script', type='application/ld+json')
                        if jsonld_scripts:
                            try:
                                existing_jsonld = json.loads(jsonld_scripts[0].string)
                            except:
                                pass
                        
                        # Extract page content
                        title = soup.find('title')
                        title_text = title.string if title else ""
                        
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        description_text = meta_desc['content'] if meta_desc else ""
                        
                        # Extract main content
                        body_text = soup.get_text()
                        
                        st.session_state.page_url = page_url
                        st.session_state.page_content = {
                            'title': title_text,
                            'description': description_text,
                            'body': body_text[:2000]  # First 2000 chars
                        }
                        st.session_state.existing_jsonld = existing_jsonld
                        
                        st.success("Page analysée avec succès")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Erreur lors du scraping: {str(e)}")
            else:
                st.error("Veuillez entrer une URL")
    
    st.markdown("---")
    
    # Display existing JSON-LD if found
    if st.session_state.existing_jsonld:
        st.markdown("### JSON-LD Actuel de la Page")
        with st.expander("Voir le JSON-LD existant"):
            st.code(json.dumps(st.session_state.existing_jsonld, indent=2, ensure_ascii=False), 
                   language="json")
    
    # Generate predictions with Mistral
    if st.session_state.page_content:
        st.markdown("### ÉTAPE 2: Génération des Prédictions IA")
        st.markdown("Mistral AI va analyser le contenu de la page et prédire les champs JSON-LD appropriés")
        
        # Sector detection
        col1, col2 = st.columns([3, 1])
        
        with col1:
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
                "L": "MusicAlbum"
            }
            
            # Auto-detect from URL/content
            auto_sector = "A"  # Default to Article
            if "/product" in st.session_state.page_url or "/produit" in st.session_state.page_url:
                auto_sector = "B"
            elif "/recipe" in st.session_state.page_url or "/recette" in st.session_state.page_url:
                auto_sector = "C"
            elif "/event" in st.session_state.page_url or "/evenement" in st.session_state.page_url:
                auto_sector = "D"
            
            selected_sector = st.selectbox(
                "Type de page détecté",
                options=list(sectors.keys()),
                format_func=lambda x: sectors[x],
                index=list(sectors.keys()).index(auto_sector),
                help="Le système détecte automatiquement le type de page. Vous pouvez le modifier si nécessaire."
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("GÉNÉRER PRÉDICTIONS IA", type="primary", use_container_width=True):
                mistral_key = get_mistral_key()
                if not mistral_key:
                    st.error("Clé API Mistral introuvable dans secrets.toml")
                else:
                    with st.spinner("Mistral AI analyse le contenu..."):
                        handler = DynamicDataHandler(api_key=mistral_key)
                        st.session_state.dynamic_data = handler.generate_predictions(
                            company_name=st.session_state.master_data.brand_name,
                            description=st.session_state.page_content['description'],
                            sector=selected_sector,
                            website=st.session_state.page_url
                        )
                        st.rerun()
        
        st.markdown("---")
        
        # Display predictions in 3 columns
        if st.session_state.dynamic_data:
            st.markdown("### ÉTAPE 3: Validation des Prédictions")
            st.markdown("Les prédictions sont classées par niveau de confiance. Validez ou rejetez chaque champ.")
            
            handler = DynamicDataHandler()
            grouped = handler.get_fields_by_decision(st.session_state.dynamic_data)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"#### VALIDÉ ({len(grouped['keep'])})")
                st.markdown("*Confiance élevée > 70%*")
                for field in grouped['keep']:
                    with st.container():
                        st.markdown(f"**{field.key}**")
                        st.text(f"{field.value}")
                        st.progress(field.confidence)
                        st.caption(field.reason)
                        st.markdown("---")
            
            with col2:
                st.markdown(f"#### INCERTAIN ({len(grouped['hesitant'])})")
                st.markdown("*Confiance moyenne 40-70%*")
                for field in grouped['hesitant']:
                    with st.container():
                        st.markdown(f"**{field.key}**")
                        st.text(f"{field.value}")
                        st.progress(field.confidence)
                        st.caption(field.reason)
                        st.markdown("---")
            
            with col3:
                st.markdown(f"#### REJETÉ ({len(grouped['reject'])})")
                st.markdown("*Confiance faible < 40%*")
                for field in grouped['reject']:
                    with st.container():
                        st.markdown(f"**{field.key}**")
                        st.text(f"{field.value or 'N/A'}")
                        st.progress(field.confidence)
                        st.caption(field.reason)
                        st.markdown("---")
            
            st.markdown("---")
            
            # Generate final JSON-LD
            st.markdown("### ÉTAPE 4: Génération du JSON-LD Leaf Final")
            st.markdown("Fusion des données Master + prédictions validées pour créer le JSON-LD complet de la page")
            
            if st.button("GÉNÉRER LE JSON-LD LEAF", type="primary"):
                template_path = "template.json"
                if os.path.exists(template_path):
                    with st.spinner("Génération du JSON-LD Leaf..."):
                        builder = TemplateBuilder(template_path)
                        
                        # Page data
                        page_data = {
                            'url': st.session_state.page_url,
                            'title': st.session_state.page_content['title'],
                            'meta_desc': st.session_state.page_content['description']
                        }
                        
                        jsonld_leaf = builder.generate_jsonld(
                            master_data=st.session_state.master_data,
                            dynamic_data=st.session_state.dynamic_data,
                            page_data=page_data
                        )
                        
                        st.success("JSON-LD Leaf généré avec succès")
                        
                        # Comparison view
                        if st.session_state.existing_jsonld:
                            st.markdown("### COMPARATIF AVANT / APRÈS")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("#### AVANT (Existant)")
                                st.code(json.dumps(st.session_state.existing_jsonld, indent=2, ensure_ascii=False), 
                                       language="json", line_numbers=True)
                            
                            with col2:
                                st.markdown("#### APRÈS (Hotaru Enrichi)")
                                st.code(jsonld_leaf, language="json", line_numbers=True)
                        else:
                            st.markdown("### JSON-LD LEAF GÉNÉRÉ")
                            st.code(jsonld_leaf, language="json", line_numbers=True)
                        
                        # Download
                        st.download_button(
                            label="TÉLÉCHARGER LE JSON-LD LEAF",
                            data=jsonld_leaf,
                            file_name=f"leaf_{st.session_state.page_url.split('/')[-1]}.json",
                            mime="application/ld+json",
                            use_container_width=True
                        )

# =============================================================================
# MAIN
# =============================================================================
def main():
    load_styles()
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # LOGIN
    if not st.session_state.authenticated:
        _, col_login, _ = st.columns([1, 1.2, 1])
        with col_login:
            st.markdown("<div style='padding-top: 80px;'></div>", unsafe_allow_html=True)
            if os.path.exists("assets/logo.png"):
                st.image("assets/logo.png", use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                email = st.text_input("EMAIL", placeholder="admin@hotaru.com")
                password = st.text_input("PASSWORD", type="password")
                submit = st.form_submit_button("LOGIN", use_container_width=True)
                
                if submit:
                    auth = AuthManager()
                    if auth.login(email, password):
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
        return
    
    # INTERFACE PRINCIPALE
    c_logo, c_version, _, c_user = st.columns([2, 2, 3, 1])
    with c_logo:
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=140)
    with c_version:
        st.markdown(f"<div style='padding-top: 15px; color: #64748b; font-size: 0.85rem;'>Version {VERSION} | Build {BUILD_DATE}</div>", unsafe_allow_html=True)
    with c_user:
        if st.button("LOGOUT", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    
    # NAVIGATION
    tab_home, tab_audit, tab_master, tab_leaf, tab_api = st.tabs([
        "HOME", "AUDIT", "MASTER", "LEAF", "API"
    ])
    
    with tab_home:
        render_home_guide()
    
    with tab_audit:
        render_audit_geo()
    
    with tab_master:
        render_master_tab()
    
    with tab_leaf:
        render_leaf_tab()
    
    with tab_api:
        st.markdown("### API DOCUMENTATION")
        st.code("curl -X GET https://api.hotaru-strategic.com/v2/status", language="bash")
    
    # Footer avec version
    st.divider()
    st.caption(f"🔮 Hotaru Entity Forge V2 | Version {VERSION}-{BUILD_ID} | Build {BUILD_DATE}")

if __name__ == "__main__":
    main()
