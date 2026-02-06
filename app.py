# =============================================================================
# APP.PY
# =============================================================================


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
# MASTER TAB
# =============================================================================
def render_master_tab():
    """Onglet MASTER - Génération du JSON-LD d'entité"""
    
    st.markdown("# MASTER - Données d'Entité Permanentes")
    st.markdown("**Créez le JSON-LD de base de votre organisation, identique sur toutes les pages**")
    st.caption(f"🔧 Version: {VERSION} | Build: {BUILD_DATE}-{BUILD_ID}")
    st.markdown("---")
    
    # Init session state
    if "master_data" not in st.session_state:
        st.session_state.master_data = None
    
    # Input section
    st.markdown("### ÉTAPE 1: Identification de l'Entité")
    st.markdown("Entrez le nom de votre organisation pour auto-remplir les données depuis Wikidata et INSEE")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        company_name = st.text_input(
            "Nom de l'organisation",
            placeholder="Ex: Boursorama, Airbus, BNP Paribas...",
            help="Le système va interroger Wikidata et INSEE pour récupérer automatiquement toutes les données"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("ENRICHIR AUTOMATIQUEMENT", type="primary", use_container_width=True):
            if company_name:
                with st.spinner("Interrogation de Wikidata et INSEE..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_enrich(search_query=company_name)
                    st.rerun()
            else:
                st.error("Veuillez entrer un nom d'organisation")
    
    # Optional manual inputs
    with st.expander("Options avancées (optionnel)"):
        col1, col2 = st.columns(2)
        with col1:
            qid_manual = st.text_input("Wikidata QID (si connu)", placeholder="Ex: Q67")
        with col2:
            siren_manual = st.text_input("SIREN (si connu)", placeholder="Ex: 351058151")
        
        if st.button("ENRICHIR AVEC QID/SIREN"):
            if qid_manual or siren_manual:
                with st.spinner("Interrogation des APIs..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_enrich(
                        qid=qid_manual if qid_manual else None,
                        siren=siren_manual if siren_manual else None
                    )
                    st.rerun()
    
    st.markdown("---")
    
    # Display results
    if st.session_state.master_data:
        master = st.session_state.master_data
        
        st.markdown("### ÉTAPE 2: Données Récupérées")
        
        # Status
        if master.status == "complete":
            st.success("Enrichissement réussi - Toutes les données ont été récupérées")
        elif master.status == "partial":
            st.warning("Enrichissement partiel - Certaines données sont manquantes")
        else:
            st.error("Échec de l'enrichissement")
        
        if master.errors:
            with st.expander("Voir les erreurs"):
                for error in master.errors:
                    st.text(error)
        
        # BOUTON ENRICHISSEMENT AUTOMATIQUE
        st.markdown("---")
        st.markdown("### 🤖 Enrichissement Automatique Complet")
        st.markdown("**Mistral AI va compléter automatiquement: description, slogan, réseaux sociaux, contact, adresse**")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            mistral_key = st.text_input(
                "🔑 Clé API Mistral",
                type="password",
                value=get_mistral_key(),
                help="La clé est lue depuis secrets.toml ou peut être saisie manuellement"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 ENRICHIR TOUT", type="primary", use_container_width=True):
                if mistral_key:
                    with st.spinner("Mistral enrichit toutes les données..."):
                        handler = MasterDataHandler()
                        st.session_state.master_data = handler.auto_complete_with_mistral(
                            st.session_state.master_data,
                            mistral_key
                        )
                        st.rerun()
                else:
                    st.error("🔑 Clé Mistral requise")
        
        st.markdown("---")
        
        # Data display in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### IDENTITÉ")
            st.text(f"Nom commercial: {master.brand_name or 'N/A'}")
            st.text(f"Raison sociale: {master.legal_name or 'N/A'}")
            st.text(f"Type: {master.org_type or 'N/A'}")
            if master.description:
                st.text(f"Description: {master.description[:80]}...")
        
        with col2:
            st.markdown("#### IDENTIFIANTS")
            st.text(f"Wikidata QID: {master.qid or 'N/A'}")
            st.text(f"SIREN: {master.siren or 'N/A'}")
            st.text(f"SIRET: {master.siret or 'N/A'}")
            st.text(f"Site web: {master.site_url or 'N/A'}")
        
        with col3:
            st.markdown("#### LOCALISATION")
            st.text(f"Adresse: {master.street or 'N/A'}")
            st.text(f"Ville: {master.city or 'N/A'}")
            st.text(f"Code postal: {master.zip_code or 'N/A'}")
            st.text(f"Pays: {master.country or 'N/A'}")
        
        # Additional data
        with st.expander("Voir toutes les données enrichies"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**RÉSEAUX SOCIAUX**")
                st.text(f"Wikipedia: {master.wikipedia_url or 'N/A'}")
                st.text(f"LinkedIn: {master.linkedin_url or 'N/A'}")
                st.text(f"Twitter: {master.twitter_url or 'N/A'}")
                st.text(f"Facebook: {master.facebook_url or 'N/A'}")
                st.text(f"Instagram: {master.instagram_url or 'N/A'}")
                st.text(f"YouTube: {master.youtube_url or 'N/A'}")
                st.text(f"TikTok: {master.tiktok_url or 'N/A'}")
                
                st.markdown("**VISUELS**")
                st.text(f"Logo: {master.logo_url or 'N/A'}")
                if master.logo_url:
                    try:
                        st.image(master.logo_url, width=200)
                    except:
                        pass
                
                st.markdown("**DESCRIPTION & EXPERTISE**")
                st.text(f"Slogan: {master.slogan or 'N/A'}")
                st.text(f"Expertise: {master.expertise_1 or 'N/A'}")
            
            with col2:
                st.markdown("**CONTACT**")
                st.text(f"Téléphone: {master.phone or 'N/A'}")
                st.text(f"Email: {master.email or 'N/A'}")
                st.text(f"Fax: {master.fax or 'N/A'}")
                
                st.markdown("**ADRESSE COMPLÈTE**")
                st.text(f"Rue: {master.street or 'N/A'}")
                st.text(f"Ville: {master.city or 'N/A'}")
                st.text(f"Code postal: {master.zip_code or 'N/A'}")
                st.text(f"Région: {master.region or 'N/A'}")
                st.text(f"Pays: {master.country or 'N/A'}")
                
                st.markdown("**DONNÉES CORPORATE**")
                st.text(f"Date création: {master.founding_date or 'N/A'}")
                st.text(f"Employés: {master.num_employees or 'N/A'}")
                st.text(f"Ticker: {master.ticker_symbol or 'N/A'}")
                st.text(f"LEI: {master.lei or 'N/A'}")
        
        st.markdown("---")
        
        # Generate JSON
        st.markdown("### ÉTAPE 3: Génération du JSON-LD Master")
        st.markdown("Ce JSON sera identique sur toutes les pages de votre site")
        
        if st.button("GÉNÉRER LE JSON-LD MASTER", type="primary"):
            template_path = "template.json"
            if os.path.exists(template_path):
                with st.spinner("Génération du JSON-LD..."):
                    builder = TemplateBuilder(template_path)
                    jsonld_master = builder.generate_jsonld(
                        master_data=master,
                        dynamic_data=None,
                        page_data=None
                    )
                    
                    st.session_state.jsonld_master = jsonld_master
                    st.success("JSON-LD Master généré avec succès")
                    
                    # Display
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.code(jsonld_master, language="json", line_numbers=True)
                    
                    with col2:
                        st.download_button(
                            label="TÉLÉCHARGER",
                            data=jsonld_master,
                            file_name=f"master_{master.brand_name.lower().replace(' ', '_')}.json",
                            mime="application/ld+json",
                            use_container_width=True
                        )
                        
                        # Stats
                        st.metric("Lignes", len(jsonld_master.split('\n')))
                        st.metric("Caractères", len(jsonld_master))
            else:
                st.error("Template introuvable. Vérifiez que template.json existe dans le projet.")

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
