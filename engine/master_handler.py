"""
HOTARU v6 - ENTITY FORGE (BEAUTIFUL + FUNCTIONAL + INFORMATIVE)
Master Data Management - Client-Ready with Full UX Guidance
Author: Vince @ MediaAgency
"""

import streamlit as st
import requests
import json
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime


# ============================================================================
# PAGE CONFIG & CUSTOM CSS
# ============================================================================

st.set_page_config(
    page_title="HOTARU Entity Forge",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #1a1a2e;
    --accent: #00d4ff;
    --accent-dark: #0099cc;
    --success: #10b981;
    --warning: #f59e0b;
    --error: #ef4444;
    --bg: #0f0f1e;
    --bg-secondary: #1a1a2e;
    --border: #2d2d44;
    --text: #e5e7eb;
    --text-muted: #9ca3af;
}

* {
    font-family: 'Inter', sans-serif;
}

html, body {
    background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
    color: var(--text);
}

.main {
    background: transparent !important;
}

h1, h2, h3 {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #00d4ff, #0099cc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

input, textarea, select {
    background-color: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    font-family: 'Inter', sans-serif !important;
    padding: 10px 12px !important;
}

input:focus, textarea:focus, select:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.1) !important;
}

.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 2px !important;
}

.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    border: 1px solid var(--border) !important;
    border-bottom: none !important;
    color: var(--text-muted) !important;
    border-radius: 8px 8px 0 0 !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
}

.stTabs [aria-selected="true"] {
    background-color: var(--bg-secondary) !important;
    color: var(--accent) !important;
    border-color: var(--accent) !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%) !important;
    color: var(--primary) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    letter-spacing: 0.5px !important;
    transition: all 0.3s ease !important;
    font-family: 'Inter', sans-serif !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(0, 212, 255, 0.3) !important;
}

.stDownloadButton > button {
    background: linear-gradient(135deg, var(--success) 0%, #059669 100%) !important;
    color: white !important;
}

hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 2rem 0 !important;
}

label {
    color: var(--text) !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    margin-bottom: 8px !important;
}

.stCaption {
    color: var(--text-muted) !important;
    font-size: 0.875rem !important;
}

/* Helper text style */
.helper-text {
    color: var(--text-muted) !important;
    font-size: 0.85rem !important;
    font-style: italic !important;
    margin-top: 4px !important;
    line-height: 1.4 !important;
}

/* Info box */
.info-box {
    background-color: rgba(0, 212, 255, 0.05) !important;
    border: 1px solid rgba(0, 212, 255, 0.2) !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    margin: 8px 0 !important;
    font-size: 0.9rem !important;
    color: var(--text) !important;
    line-height: 1.5 !important;
}

.success-badge {
    background: rgba(16, 185, 129, 0.1) !important;
    border: 1px solid var(--success) !important;
    color: var(--success) !important;
    padding: 8px 16px !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    display: inline-block !important;
}

.warning-badge {
    background: rgba(245, 158, 11, 0.1) !important;
    border: 1px solid var(--warning) !important;
    color: var(--warning) !important;
    padding: 8px 16px !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    display: inline-block !important;
}

.field-counter {
    background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(0, 153, 204, 0.05)) !important;
    border: 1px solid rgba(0, 212, 255, 0.2) !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    color: var(--accent) !important;
    display: inline-block !important;
    margin: 8px 0 !important;
}

.section-title {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    margin: 20px 0 12px 0 !important;
    color: var(--accent) !important;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.stContainer {
    animation: fadeIn 0.6s ease-out;
}

.gradient-text {
    background: linear-gradient(135deg, #00d4ff, #0099cc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--accent);
}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# 1. DATA MODEL
# ============================================================================

@dataclass
class MasterData:
    """Master Data - Fixed, brand-level information"""
    
    master_brand_name: str = ""
    master_legal_name: str = ""
    master_alt_1: str = ""
    master_alt_2: str = ""
    master_description: str = ""
    master_slogan: str = ""
    master_site_url: str = ""
    master_org_type: str = "Organization"
    
    master_logo_url: str = ""
    master_logo_w: str = "600"
    master_logo_h: str = "200"
    master_image: str = ""
    
    master_siren: str = ""
    master_siret: str = ""
    master_lei: str = ""
    master_qid: str = ""
    master_duns: str = ""
    master_gln: str = ""
    
    master_phone: str = ""
    master_email: str = ""
    master_fax: str = ""
    master_phone_cs: str = ""
    master_email_cs: str = ""
    master_phone_sales: str = ""
    master_email_sales: str = ""
    master_phone_tech: str = ""
    master_email_tech: str = ""
    
    master_street: str = ""
    master_city: str = ""
    master_region: str = ""
    master_zip: str = ""
    master_country: str = "FR"
    master_lat: str = ""
    master_long: str = ""
    master_google_maps: str = ""
    
    master_wikipedia: str = ""
    master_linkedin: str = ""
    master_twitter: str = ""
    master_facebook: str = ""
    master_instagram: str = ""
    master_youtube: str = ""
    master_tiktok: str = ""
    
    master_expertise_1: str = ""
    master_exp_1_wiki: str = ""
    master_expertise_2: str = ""
    master_exp_2_wiki: str = ""
    
    master_founding_date: str = ""
    master_founding_city: str = ""
    master_founder_1: str = ""
    master_founder_1_li: str = ""
    master_founder_1_title: str = ""
    master_ceo: str = ""
    master_ceo_li: str = ""
    
    master_parent_name: str = ""
    master_parent_qid: str = ""
    master_parent_siren: str = ""
    master_sub_1: str = ""
    master_sub_1_wiki: str = ""
    master_member_of: str = ""
    
    master_employee_count: str = ""
    master_emp_min: str = ""
    master_emp_max: str = ""
    
    master_rating: str = ""
    master_review_count: str = ""
    master_reviewer_1: str = ""
    master_rev_1_rating: str = ""
    master_rev_1_text: str = ""
    master_rev_1_date: str = ""
    
    master_award_1: str = ""
    master_award_2: str = ""
    master_ticker: str = ""
    master_exchange: str = ""
    master_revenue: str = ""
    
    master_nonprofit: str = ""
    master_legal_status: str = ""
    master_price_range: str = ""
    master_photo_1: str = ""
    master_photo_2: str = ""
    
    master_publishing_principles_url: str = ""
    master_corrections_url: str = ""
    master_diversity_url: str = ""
    master_ethics_url: str = ""
    
    master_website_name: str = ""
    master_website_alt: str = ""
    master_website_desc: str = ""
    master_lang: str = "fr"
    master_copyright_year: str = ""
    master_license_url: str = ""
    
    status: str = "pending"
    errors: List[str] = field(default_factory=list)
    last_updated: str = ""
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() 
                if v and k not in ['errors', 'status', 'last_updated']}
    
    def count_filled_fields(self) -> int:
        return len(self.to_dict())


# ============================================================================
# 2. API CLIENTS
# ============================================================================

class WikidataAPI:
    BASE_URL = "https://www.wikidata.org/w/api.php"
    
    @staticmethod
    def search_entity(query: str, limit: int = 5) -> List[Dict]:
        params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "fr",
            "format": "json",
            "limit": limit,
            "type": "item"
        }
        headers = {"User-Agent": "HotaruEntityForge/6.0"}
        
        try:
            r = requests.get(WikidataAPI.BASE_URL, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            return r.json().get('search', [])
        except Exception as e:
            st.error(f"🔴 Wikidata search error: {e}")
            return []
    
    @staticmethod
    def get_entity_data(qid: str) -> Optional[Dict]:
        params = {
            "action": "wbgetentities",
            "ids": qid,
            "languages": "fr|en",
            "props": "labels|descriptions|claims",
            "format": "json"
        }
        headers = {"User-Agent": "HotaruEntityForge/6.0"}
        
        try:
            r = requests.get(WikidataAPI.BASE_URL, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            
            entity = r.json().get('entities', {}).get(qid, {})
            if not entity:
                return None
            
            labels = entity.get('labels', {})
            descs = entity.get('descriptions', {})
            claims = entity.get('claims', {})
            
            result = {
                "qid": qid,
                "name_fr": labels.get('fr', {}).get('value', ''),
                "name_en": labels.get('en', {}).get('value', ''),
                "desc_fr": descs.get('fr', {}).get('value', ''),
                "desc_en": descs.get('en', {}).get('value', ''),
                "siren": "",
                "lei": "",
                "website": "",
                "founding_date": ""
            }
            
            if 'P1616' in claims:
                try:
                    result["siren"] = claims['P1616'][0]['mainsnak']['datavalue']['value']
                except:
                    pass
            
            if 'P1278' in claims:
                try:
                    result["lei"] = claims['P1278'][0]['mainsnak']['datavalue']['value']
                except:
                    pass
            
            if 'P856' in claims:
                try:
                    result["website"] = claims['P856'][0]['mainsnak']['datavalue']['value']
                except:
                    pass
            
            if 'P571' in claims:
                try:
                    time_val = claims['P571'][0]['mainsnak']['datavalue']['value']['time']
                    result["founding_date"] = time_val[1:11]
                except:
                    pass
            
            return result
            
        except Exception as e:
            st.error(f"🔴 Wikidata fetch error: {e}")
            return None


class MistralEnricher:
    API_URL = "https://api.mistral.ai/v1/chat/completions"
    MODEL = "mistral-large-latest"
    
    @staticmethod
    def preview_enrichment(master: MasterData, api_key: str) -> Tuple[Optional[Dict], List[str]]:
        if not api_key:
            return None, ["API key missing"]
        
        existing = master.to_dict()
        
        prompt = f"""Tu es expert en enrichissement de données d'entités commerciales.

CONTEXTE:
{json.dumps(existing, ensure_ascii=False, indent=2)}

Enrichis UNIQUEMENT les champs MANQUANTS. Retourne UNIQUEMENT du JSON VALIDE (pas de markdown):

{{
  "master_qid": "Q...",
  "master_siren": "SIREN si FR",
  "master_legal_name": "Raison sociale",
  "master_description": "Description courte",
  "master_slogan": "Slogan (ou vide)",
  "master_founding_date": "YYYY-MM-DD",
  "master_employee_count": "Nombre d'employés",
  "master_linkedin": "URL LinkedIn",
  "master_twitter": "URL Twitter/X",
  "master_logo_url": "URL logo",
  "master_phone": "Téléphone",
  "master_email": "Email",
  "master_expertise_1": "Expertise 1",
  "master_expertise_2": "Expertise 2"
}}"""
        
        try:
            response = requests.post(
                MistralEnricher.API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MistralEnricher.MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 1500
                },
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"API error {response.status_code}"
                if response.status_code == 401:
                    error_msg += " - Invalid key"
                return None, [error_msg]
            
            content = response.json()['choices'][0]['message']['content']
            content = content.replace("```json", "").replace("```", "").strip()
            enriched_data = json.loads(content)
            
            return enriched_data, []
            
        except json.JSONDecodeError:
            return None, ["JSON parsing error"]
        except Exception as e:
            return None, [f"Error: {str(e)}"]
    
    @staticmethod
    def apply_enrichment(master: MasterData, enriched_data: Dict) -> MasterData:
        if not enriched_data:
            return master
        
        for key, value in enriched_data.items():
            if hasattr(master, key) and value:
                setattr(master, key, value)
        
        master.status = "complete"
        master.last_updated = datetime.now().isoformat()
        return master


# ============================================================================
# 3. STREAMLIT UI
# ============================================================================

def init_session():
    if 'master' not in st.session_state:
        st.session_state.master = MasterData()
    if 'api_key' not in st.session_state:
        try:
            st.session_state.api_key = st.secrets["mistral"]["api_key"]
        except (KeyError, TypeError):
            st.session_state.api_key = ""
    if 'mistral_preview' not in st.session_state:
        st.session_state.mistral_preview = None
    if 'mistral_errors' not in st.session_state:
        st.session_state.mistral_errors = []


def render_header():
    col1, col2, col3 = st.columns([0.5, 3, 1], gap="large")
    
    with col1:
        st.markdown("# 🏢")
    
    with col2:
        st.markdown("<h1 class='gradient-text'>HOTARU Entity Forge</h1>", unsafe_allow_html=True)
        st.caption("Master Data Management • AI-Powered Enrichment")
    
    with col3:
        if st.session_state.master.master_brand_name:
            st.markdown(f"""
            <div class='success-badge'>
                ✓ {st.session_state.master.master_brand_name}
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()


def render_search_section():
    st.markdown("### 🔍 Brand Identification (One Point of Master)")
    st.markdown("""
    <div class='info-box'>
    💡 <b>How it works:</b> Search for your brand name in Wikidata, select the correct result, 
    and we'll automatically populate key information (SIREN, founding date, website, etc.)
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1], gap="large")
    
    with col1:
        brand_query = st.text_input(
            "Search for your brand",
            placeholder="e.g., Carrefour, Google, Anthropic...",
            key="brand_search_input",
            label_visibility="collapsed"
        )
    
    with col2:
        search_btn = st.button("🔎 Search", use_container_width=True, key="search_btn")
    
    if search_btn and brand_query:
        with st.spinner("🌐 Searching Wikidata..."):
            results = WikidataAPI.search_entity(brand_query, limit=3)
            st.session_state.search_results = results
            
            if not results:
                st.warning("❌ No results found. Try a different search term.")
    
    if 'search_results' in st.session_state and st.session_state.search_results:
        st.markdown("**Select your brand:**")
        
        for result in st.session_state.search_results:
            col1, col2, col3 = st.columns([1, 3, 2], gap="medium")
            
            with col1:
                if st.button("✓ Select", key=f"sel_{result['id']}", use_container_width=True):
                    with st.spinner("📡 Fetching Wikidata data..."):
                        entity = WikidataAPI.get_entity_data(result['id'])
                        
                        if entity:
                            st.session_state.master.master_qid = result['id']
                            st.session_state.master.master_brand_name = entity.get('name_fr') or entity.get('name_en')
                            st.session_state.master.master_description = entity.get('desc_fr') or entity.get('desc_en')
                            st.session_state.master.master_siren = entity.get('siren', '')
                            st.session_state.master.master_site_url = entity.get('website', '')
                            st.session_state.master.master_founding_date = entity.get('founding_date', '')
                            st.session_state.master.status = "partial"
                            
                            st.success(f"✓ Loaded: {st.session_state.master.master_brand_name}")
                            st.rerun()
            
            with col2:
                st.markdown(f"**{result['label']}**")
                if result.get('description'):
                    st.caption(result['description'][:120])
            
            with col3:
                st.caption(f"📍 {result['id']}")


def render_mistral_section():
    st.divider()
    st.markdown("### 🤖 AI Enrichment (Mistral)")
    st.markdown("""
    <div class='info-box'>
    💡 <b>What it does:</b> Uses AI to suggest values for empty fields based on the brand name 
    and existing data. Review suggestions before applying.
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1], gap="medium")
    
    with col1:
        if st.button("✨ Preview Enrichment", key="preview_btn", use_container_width=True):
            if not st.session_state.master.master_brand_name:
                st.warning("⚠️ Please select a brand first")
            else:
                with st.spinner("🤔 Analyzing with Mistral AI..."):
                    enriched, errors = MistralEnricher.preview_enrichment(
                        st.session_state.master,
                        st.session_state.api_key
                    )
                    
                    st.session_state.mistral_preview = enriched
                    st.session_state.mistral_errors = errors
                    
                    if errors:
                        st.error(f"❌ {errors[0]}")
                    else:
                        st.success("✅ Preview ready!")
    
    with col2:
        if st.session_state.mistral_preview:
            if st.button("✓ Apply", key="apply_btn", use_container_width=True):
                st.session_state.master = MistralEnricher.apply_enrichment(
                    st.session_state.master,
                    st.session_state.mistral_preview
                )
                st.session_state.mistral_preview = None
                st.success("💾 Changes applied!")
                st.rerun()
    
    with col3:
        if st.session_state.mistral_preview:
            if st.button("✗ Reject", key="reject_btn", use_container_width=True):
                st.session_state.mistral_preview = None
                st.rerun()
    
    if st.session_state.mistral_preview:
        st.markdown("**Preview of AI suggestions:**")
        with st.container(border=True):
            preview_count = 0
            for key, value in st.session_state.mistral_preview.items():
                if value:
                    current = getattr(st.session_state.master, key, "")
                    if current != value:
                        preview_count += 1
                        col1, col2 = st.columns(2, gap="large")
                        with col1:
                            st.markdown(f"**{key.replace('master_', '').title()}**")
                            st.caption(f"Current: {current[:50] if current else '(empty)'}")
                        with col2:
                            st.caption(f"Suggested: {value[:50]}")
                        st.divider()
            
            if preview_count == 0:
                st.caption("✓ No changes - all key fields are already filled")


def render_field_input(label: str, value: str, placeholder: str = "", helper: str = "", key_suffix: str = "") -> str:
    """Helper to render a field with label, input, and helper text"""
    st.write(label)
    new_value = st.text_input(
        label,
        value=value,
        placeholder=placeholder,
        key=f"{key_suffix}_{label}",
        label_visibility="collapsed"
    )
    if helper:
        st.markdown(f"<p class='helper-text'>ℹ️ {helper}</p>", unsafe_allow_html=True)
    return new_value


def render_tab_identity():
    m = st.session_state.master
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("<div class='section-title'>📱 Brand Identity</div>", unsafe_allow_html=True)
        m.master_brand_name = st.text_input(
            "Brand Name",
            value=m.master_brand_name,
            placeholder="Official brand name",
            help="The primary name used by the brand for marketing and communication"
        )
        m.master_legal_name = st.text_input(
            "Legal Name",
            value=m.master_legal_name,
            placeholder="Registered legal entity name",
            help="Official business name registered with government authorities"
        )
        m.master_slogan = st.text_input(
            "Slogan",
            value=m.master_slogan,
            placeholder="e.g., 'Just Do It'",
            help="Brand tagline or motto used in marketing"
        )
    
    with col2:
        st.markdown("<div class='section-title'>🔍 Identifiers</div>", unsafe_allow_html=True)
        m.master_qid = st.text_input(
            "Wikidata QID",
            value=m.master_qid,
            placeholder="Q123456",
            help="Unique Wikidata identifier (search or populate automatically)"
        )
        m.master_alt_1 = st.text_input(
            "Alternative Name 1",
            value=m.master_alt_1,
            placeholder="e.g., former name",
            help="Also known as, previous brand name, or alternate spelling"
        )
        m.master_alt_2 = st.text_input(
            "Alternative Name 2",
            value=m.master_alt_2,
            placeholder="e.g., subsidiary name",
            help="Second alternative name if applicable"
        )
    
    st.markdown("<div class='section-title'>📝 Description</div>", unsafe_allow_html=True)
    m.master_description = st.text_area(
        "Brand Description",
        value=m.master_description,
        height=100,
        placeholder="Comprehensive brand description...",
        help="2-3 sentences describing what the brand does and its key value proposition"
    )
    
    st.markdown("<div class='section-title'>🎨 Visual Identity</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        m.master_logo_url = st.text_input(
            "Logo URL",
            value=m.master_logo_url,
            placeholder="https://...",
            help="Direct URL to high-quality logo image (PNG or SVG preferred)"
        )
    with col2:
        m.master_logo_w = st.text_input(
            "Width (px)",
            value=m.master_logo_w,
            help="Logo width in pixels for JSON-LD markup"
        )
    with col3:
        m.master_logo_h = st.text_input(
            "Height (px)",
            value=m.master_logo_h,
            help="Logo height in pixels for JSON-LD markup"
        )
    
    m.master_image = st.text_input(
        "Brand Image URL",
        value=m.master_image,
        placeholder="https://...",
        help="Hero image or main brand photo URL"
    )
    
    st.markdown("<div class='section-title'>⚙️ Organization Type</div>", unsafe_allow_html=True)
    m.master_org_type = st.selectbox(
        "Organization Type",
        ["Organization", "Corporation", "LocalBusiness", "NGO", "Government", "EducationalOrganization"],
        index=0,
        help="Choose the primary type that best describes the organization"
    )


def render_tab_legal():
    m = st.session_state.master
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("<div class='section-title'>⚖️ Legal Identifiers</div>", unsafe_allow_html=True)
        m.master_siren = st.text_input(
            "SIREN",
            value=m.master_siren,
            placeholder="123456789",
            help="French company registration number (9 digits) - auto-populated from Wikidata"
        )
        m.master_siret = st.text_input(
            "SIRET",
            value=m.master_siret,
            placeholder="12345678901234",
            help="French establishment registration number (14 digits)"
        )
        m.master_lei = st.text_input(
            "LEI",
            value=m.master_lei,
            placeholder="XXXX00XXXXXX000XXX00",
            help="Legal Entity Identifier - international business identifier"
        )
    
    with col2:
        st.markdown("<div class='section-title'>📦 Other IDs</div>", unsafe_allow_html=True)
        m.master_duns = st.text_input(
            "DUNS",
            value=m.master_duns,
            placeholder="12-345-6789",
            help="Dun & Bradstreet unique identifier"
        )
        m.master_gln = st.text_input(
            "GLN",
            value=m.master_gln,
            placeholder="5412345000013",
            help="Global Location Number for supply chain"
        )
    
    st.markdown("<div class='section-title'>📋 Status & Legal</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        m.master_legal_status = st.text_input(
            "Legal Status",
            value=m.master_legal_status,
            placeholder="e.g., Active, Dissolved",
            help="Current legal status of the company"
        )
    with col2:
        m.master_nonprofit = st.text_input(
            "Non-profit Status",
            value=m.master_nonprofit,
            placeholder="501c3 or similar",
            help="If applicable, non-profit designation"
        )
    with col3:
        m.master_country = st.text_input(
            "Country Code",
            value=m.master_country,
            placeholder="FR",
            help="ISO 3166-1 alpha-2 country code (e.g., FR for France)"
        )


def render_tab_contact():
    m = st.session_state.master
    
    st.markdown("<div class='section-title'>☎️ Main Contact</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        m.master_phone = st.text_input(
            "Phone",
            value=m.master_phone,
            placeholder="+33 1 23 45 67 89",
            help="Main company phone number (include country code)"
        )
        m.master_email = st.text_input(
            "Email",
            value=m.master_email,
            placeholder="contact@company.com",
            help="General inquiry email address"
        )
    with col2:
        m.master_fax = st.text_input(
            "Fax",
            value=m.master_fax,
            placeholder="+33 1 23 45 67 89",
            help="Company fax number (if available)"
        )
    
    st.markdown("<div class='section-title'>👥 Customer Service</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        m.master_phone_cs = st.text_input(
            "CS Phone",
            value=m.master_phone_cs,
            help="Dedicated customer service phone line"
        )
        m.master_email_cs = st.text_input(
            "CS Email",
            value=m.master_email_cs,
            help="Dedicated customer service email"
        )
    
    with col2:
        st.markdown("&nbsp;")
        m.master_phone_sales = st.text_input(
            "Sales Phone",
            value=m.master_phone_sales,
            help="Sales department phone"
        )
        m.master_email_sales = st.text_input(
            "Sales Email",
            value=m.master_email_sales,
            help="Sales department email"
        )
    
    m.master_phone_tech = st.text_input(
        "Tech Support Phone",
        value=m.master_phone_tech,
        help="Technical support hotline"
    )
    m.master_email_tech = st.text_input(
        "Tech Support Email",
        value=m.master_email_tech,
        help="Technical support email"
    )
    
    st.markdown("<div class='section-title'>📍 Address</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        m.master_street = st.text_input(
            "Street",
            value=m.master_street,
            placeholder="123 Main Street",
            help="Street address of headquarters"
        )
        m.master_city = st.text_input(
            "City",
            value=m.master_city,
            help="City of headquarters"
        )
        m.master_zip = st.text_input(
            "ZIP Code",
            value=m.master_zip,
            help="Postal code"
        )
    with col2:
        m.master_region = st.text_input(
            "Region/State",
            value=m.master_region,
            help="Region or state"
        )
        m.master_lat = st.text_input(
            "Latitude",
            value=m.master_lat,
            placeholder="48.8566",
            help="GPS latitude coordinate"
        )
        m.master_long = st.text_input(
            "Longitude",
            value=m.master_long,
            placeholder="2.3522",
            help="GPS longitude coordinate"
        )
    
    m.master_google_maps = st.text_input(
        "Google Maps URL",
        value=m.master_google_maps,
        placeholder="https://maps.google.com/...",
        help="Link to Google Maps location"
    )


def render_tab_social():
    m = st.session_state.master
    
    st.markdown("<div class='section-title'>🌐 Website & Knowledge Graph</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        m.master_site_url = st.text_input(
            "Website",
            value=m.master_site_url,
            placeholder="https://www.example.com",
            help="Main company website URL"
        )
        m.master_wikipedia = st.text_input(
            "Wikipedia",
            value=m.master_wikipedia,
            placeholder="https://en.wikipedia.org/wiki/...",
            help="Wikipedia article URL if exists"
        )
        m.master_linkedin = st.text_input(
            "LinkedIn",
            value=m.master_linkedin,
            placeholder="https://www.linkedin.com/company/...",
            help="LinkedIn company page URL"
        )
        m.master_twitter = st.text_input(
            "Twitter/X",
            value=m.master_twitter,
            placeholder="https://twitter.com/...",
            help="Official Twitter/X profile URL"
        )
    
    with col2:
        m.master_facebook = st.text_input(
            "Facebook",
            value=m.master_facebook,
            placeholder="https://www.facebook.com/...",
            help="Official Facebook page URL"
        )
        m.master_instagram = st.text_input(
            "Instagram",
            value=m.master_instagram,
            placeholder="https://www.instagram.com/...",
            help="Official Instagram profile URL"
        )
        m.master_youtube = st.text_input(
            "YouTube",
            value=m.master_youtube,
            placeholder="https://www.youtube.com/...",
            help="YouTube channel URL"
        )
        m.master_tiktok = st.text_input(
            "TikTok",
            value=m.master_tiktok,
            placeholder="https://www.tiktok.com/...",
            help="TikTok account URL if exists"
        )
    
    st.markdown("<div class='section-title'>🎯 Expertise & Topics</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        m.master_expertise_1 = st.text_input(
            "Expertise Domain 1",
            value=m.master_expertise_1,
            placeholder="e.g., Retail, E-commerce",
            help="Primary business domain or expertise area"
        )
        m.master_exp_1_wiki = st.text_input(
            "Expertise 1 (Wikidata)",
            value=m.master_exp_1_wiki,
            placeholder="https://www.wikidata.org/wiki/Q...",
            help="Wikidata URL for the expertise domain"
        )
    with col2:
        m.master_expertise_2 = st.text_input(
            "Expertise Domain 2",
            value=m.master_expertise_2,
            placeholder="e.g., Distribution",
            help="Secondary business domain if applicable"
        )
        m.master_exp_2_wiki = st.text_input(
            "Expertise 2 (Wikidata)",
            value=m.master_exp_2_wiki,
            placeholder="https://www.wikidata.org/wiki/Q...",
            help="Wikidata URL for the second expertise domain"
        )


def render_tab_corporate():
    m = st.session_state.master
    
    st.markdown("<div class='section-title'>🏭 History & Founders</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        m.master_founding_date = st.text_input(
            "Founding Date",
            value=m.master_founding_date,
            placeholder="YYYY-MM-DD",
            help="Date company was founded (YYYY-MM-DD format)"
        )
        m.master_founding_city = st.text_input(
            "Founding City",
            value=m.master_founding_city,
            help="City where company was founded"
        )
    
    with col2:
        m.master_founder_1 = st.text_input(
            "Founder Name",
            value=m.master_founder_1,
            help="Name of primary founder"
        )
        m.master_founder_1_title = st.text_input(
            "Founder Title",
            value=m.master_founder_1_title,
            help="Founder's role/title at founding"
        )
    
    m.master_founder_1_li = st.text_input(
        "Founder LinkedIn",
        value=m.master_founder_1_li,
        placeholder="https://www.linkedin.com/in/...",
        help="Founder's LinkedIn profile URL"
    )
    
    st.markdown("<div class='section-title'>👔 Current Leadership</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        m.master_ceo = st.text_input(
            "CEO Name",
            value=m.master_ceo,
            help="Current Chief Executive Officer name"
        )
    with col2:
        m.master_ceo_li = st.text_input(
            "CEO LinkedIn",
            value=m.master_ceo_li,
            help="CEO's LinkedIn profile URL"
        )
    
    st.markdown("<div class='section-title'>🏢 Organization Structure</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        m.master_parent_name = st.text_input(
            "Parent Organization",
            value=m.master_parent_name,
            help="Name of parent company if applicable"
        )
    with col2:
        m.master_parent_qid = st.text_input(
            "Parent QID",
            value=m.master_parent_qid,
            help="Wikidata ID of parent company"
        )
    with col3:
        m.master_parent_siren = st.text_input(
            "Parent SIREN",
            value=m.master_parent_siren,
            help="SIREN of parent company"
        )
    
    col1, col2 = st.columns(2, gap="large")
    with col1:
        m.master_sub_1 = st.text_input(
            "Subsidiary",
            value=m.master_sub_1,
            help="Name of major subsidiary company"
        )
    with col2:
        m.master_sub_1_wiki = st.text_input(
            "Subsidiary (Wikidata)",
            value=m.master_sub_1_wiki,
            help="Wikidata URL of subsidiary"
        )
    
    m.master_member_of = st.text_input(
        "Member Of Organization",
        value=m.master_member_of,
        help="Professional organizations or associations the company belongs to"
    )
    
    st.markdown("<div class='section-title'>📊 Size & Performance</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        m.master_employee_count = st.text_input(
            "Employee Count",
            value=m.master_employee_count,
            placeholder="5000",
            help="Approximate total number of employees"
        )
    with col2:
        m.master_emp_min = st.text_input(
            "Min Employees",
            value=m.master_emp_min,
            help="Minimum for employee range"
        )
    with col3:
        m.master_emp_max = st.text_input(
            "Max Employees",
            value=m.master_emp_max,
            help="Maximum for employee range"
        )
    
    st.markdown("<div class='section-title'>⭐ Social Proof & Awards</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        m.master_rating = st.text_input(
            "Average Rating",
            value=m.master_rating,
            placeholder="4.5",
            help="Average customer rating (out of 5)"
        )
        m.master_review_count = st.text_input(
            "Review Count",
            value=m.master_review_count,
            help="Total number of customer reviews"
        )
        m.master_award_1 = st.text_input(
            "Award 1",
            value=m.master_award_1,
            help="Notable award or recognition"
        )
    
    with col2:
        m.master_reviewer_1 = st.text_input(
            "Sample Reviewer",
            value=m.master_reviewer_1,
            help="Name of person who left a sample review"
        )
        m.master_rev_1_rating = st.text_input(
            "Review Rating",
            value=m.master_rev_1_rating,
            help="Rating given in sample review"
        )
        m.master_award_2 = st.text_input(
            "Award 2",
            value=m.master_award_2,
            help="Second notable award"
        )
    
    m.master_rev_1_text = st.text_area(
        "Sample Review Text",
        value=m.master_rev_1_text,
        height=80,
        help="Sample customer testimonial or review"
    )
    m.master_rev_1_date = st.text_input(
        "Review Date",
        value=m.master_rev_1_date,
        placeholder="YYYY-MM-DD",
        help="Date of the sample review"
    )
    
    st.markdown("<div class='section-title'>💰 Finance</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        m.master_ticker = st.text_input(
            "Ticker Symbol",
            value=m.master_ticker,
            placeholder="ORCL",
            help="Stock ticker if publicly traded"
        )
    with col2:
        m.master_exchange = st.text_input(
            "Stock Exchange",
            value=m.master_exchange,
            placeholder="NYSE",
            help="Stock exchange where listed"
        )
    with col3:
        m.master_revenue = st.text_input(
            "Annual Revenue",
            value=m.master_revenue,
            placeholder="€1.2B",
            help="Annual revenue (approximate)"
        )


def render_export_section():
    st.divider()
    st.markdown("### 📤 Export Master Data")
    st.markdown("""
    <div class='info-box'>
    💡 <b>Export formats:</b> Download your Master Data as JSON for use in JSON-LD markup, 
    databases, or other systems.
    </div>
    """, unsafe_allow_html=True)
    
    master_json = json.dumps(st.session_state.master.to_dict(), ensure_ascii=False, indent=2)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.download_button(
            label="📥 Download as JSON",
            data=master_json,
            file_name=f"master_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        if st.button("📋 View JSON", use_container_width=True):
            st.session_state.show_json = not st.session_state.get('show_json', False)
    
    if st.session_state.get('show_json'):
        st.code(master_json, language="json", line_numbers=True)


def render_status():
    st.divider()
    st.markdown("### 📊 Status & Completeness")
    
    m = st.session_state.master
    fields_filled = m.count_filled_fields()
    completion_pct = int((fields_filled / 65) * 100) if fields_filled else 0
    
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    
    with col1:
        if m.status == "complete":
            st.markdown("""
            <div class='success-badge'>
                ✓ Complete
            </div>
            """, unsafe_allow_html=True)
        elif m.status == "partial":
            st.markdown("""
            <div class='warning-badge'>
                ⚠ Partial
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption(f"Status: {m.status}")
    
    with col2:
        st.markdown(f"""
        <div class='field-counter'>
            📊 {fields_filled} fields filled
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.progress(completion_pct / 100, text=f"{completion_pct}% Complete")
    
    with col4:
        if m.errors:
            st.markdown(f"""
            <div class='warning-badge'>
                ⚠ {len(m.errors)} issue(s)
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='success-badge'>
                ✓ No errors
            </div>
            """, unsafe_allow_html=True)


# ============================================================================
# MAIN
# ============================================================================

def main():
    init_session()
    
    if not st.session_state.api_key:
        st.warning("⚠️ Mistral API key not configured")
        st.info("Configure `[mistral]` `api_key` in ~/.streamlit/secrets.toml")
    
    render_header()
    render_search_section()
    render_mistral_section()
    
    st.divider()
    
    st.markdown("## Master Data Fields")
    
    tabs = st.tabs(["📇 Identity", "⚖️ Legal", "📞 Contact", "🌐 Social", "🏛️ Corporate"])
    
    with tabs[0]:
        render_tab_identity()
    with tabs[1]:
        render_tab_legal()
    with tabs[2]:
        render_tab_contact()
    with tabs[3]:
        render_tab_social()
    with tabs[4]:
        render_tab_corporate()
    
    render_export_section()
    render_status()


if __name__ == "__main__":
    main()
