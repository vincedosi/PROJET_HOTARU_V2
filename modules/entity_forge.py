"""
ENTITY FORGE ULTIMATE - Module Hotaru Strategic
"Agentic AI" : Search -> Select -> Predict -> Review
"""

import streamlit as st
import requests
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# =============================================================================
# 1. DATA MODEL & CONFIG
# =============================================================================
TEMPLATE_PATH = "jsonld_MAXIMAL_final.json"
if not os.path.exists(TEMPLATE_PATH):
    TEMPLATE_PATH = "templates/jsonld_MAXIMAL_final.json"

@dataclass
class EntityData:
    # --- BLOC 1 : MASTER (API + FIXE) ---
    org_type: str = "Organization"
    brand_name: str = ""
    legal_name: str = ""
    alt_names: str = ""
    description: str = ""
    slogan: str = ""
    site_url: str = ""
    logo_url: str = ""
    
    # IDs
    siret: str = ""
    siren: str = ""
    lei: str = ""
    duns: str = ""
    qid: str = ""
    iso6523: str = ""
    
    # Adresse
    street: str = ""
    city: str = ""
    zip_code: str = ""
    country: str = "FR"
    phone: str = ""
    email: str = ""
    
    # Social
    linkedin: str = ""
    twitter: str = ""
    facebook: str = ""
    wikipedia: str = ""
    
    # Dates
    founding_date: str = ""
    
    # --- PAGE CONTEXT ---
    page_url: str = ""
    page_title: str = ""
    page_desc: str = ""
    
    # --- CHAMPS DYNAMIQUES (MISTRAL) ---
    # Dictionnaire pour stocker n'importe quel champ prédit par l'IA
    dynamic_fields: Dict[str, str] = field(default_factory=dict)

# =============================================================================
# 2. APIs SEARCH (LISTES DE CHOIX)
# =============================================================================
class INSEEAPI:
    @staticmethod
    def search_list(query: str):
        """Retourne une liste de candidats pour le choix utilisateur"""
        try:
            r = requests.get("https://recherche-entreprises.api.gouv.fr/search", 
                           params={"q": query, "per_page": 5, "etat_administratif": "A"}, timeout=5)
            return r.json().get('results', [])
        except: return []

class WikidataAPI:
    BASE_URL = "https://www.wikidata.org/w/api.php"
    
    @staticmethod
    def search_list(query: str):
        try:
            r = requests.get(WikidataAPI.BASE_URL, params={
                "action": "wbsearchentities", "search": query, "language": "fr",
                "format": "json", "limit": 5, "type": "item"
            }, timeout=5)
            return r.json().get('search', [])
        except: return []

    @staticmethod
    def get_details(qid: str):
        """Récupère les détails profonds une fois le QID choisi"""
        try:
            r = requests.get(WikidataAPI.BASE_URL, params={
                "action": "wbgetentities", "ids": qid, "languages": "fr",
                "props": "labels|descriptions|claims|sitelinks", "format": "json"
            }, timeout=5)
            entity = r.json().get('entities', {}).get(qid, {})
            claims = entity.get('claims', {})
            
            data = {
                "desc": entity.get('descriptions', {}).get('fr', {}).get('value', ''),
                "website": "", "siren": "", "founded": "", "logo": "", "social": {}
            }
            
            # Helpers d'extraction
            if 'P856' in claims: data['website'] = claims['P856'][0]['mainsnak']['datavalue']['value']
            if 'P1616' in claims: data['siren'] = claims['P1616'][0]['mainsnak']['datavalue']['value']
            if 'P571' in claims: data['founded'] = claims['P571'][0]['mainsnak']['datavalue']['value']['time'][1:11]
            if 'P154' in claims: # Logo image
                 img = claims['P154'][0]['mainsnak']['datavalue']['value']
                 data['logo'] = f"https://commons.wikimedia.org/wiki/Special:FilePath/{img}"
            
            # Socials
            if 'P2013' in claims: data['social']['facebook'] = f"https://facebook.com/{claims['P2013'][0]['mainsnak']['datavalue']['value']}"
            if 'P2002' in claims: data['social']['twitter'] = f"https://x.com/{claims['P2002'][0]['mainsnak']['datavalue']['value']}"
            if 'P4264' in claims: data['social']['linkedin'] = f"https://linkedin.com/company/{claims['P4264'][0]['mainsnak']['datavalue']['value']}"

            return data
        except: return {}

# =============================================================================
# 3. MISTRAL AGENT (PREDICTIVE FILL)
# =============================================================================
def mistral_predict_fields(api_key, sector, entity_name, description):
    """
    IA Agent : Analyse le secteur ET tente de remplir les valeurs.
    """
    # Liste des champs Schema.org complexes à analyser
    target_fields = [
        "AggregateRating (Avis)", "PriceRange (Prix)", "OpeningHours (Horaires)", 
        "AreaServed (Zone)", "Awards (Récompenses)", "PaymentAccepted (Paiement)",
        "HasMenu (Restaurant)", "MakesOffer (Offre)", "Audience (Cible)"
    ]
    
    prompt = f"""
    Tu es une IA experte en Web Sémantique (JSON-LD) pour le SEO.
    
    CONTEXTE :
    - Entité : "{entity_name}"
    - Secteur : "{sector}"
    - Description : "{description}"

    TA MISSION :
    1. Pour chaque champ Schema.org de cette liste : {', '.join(target_fields)}.
    2. Détermine s'il est pertinent (kept), incertain (hesitant) ou inutile (rejected).
    3. SI PERTINENT (kept) : Tu DOIS inventer/prédire une valeur standard réaliste pour ce secteur (ex: "Mo-Fr 09:00-18:00" pour des bureaux).

    FORMAT DE RÉPONSE ATTENDU (JSON STRICT) :
    {{
        "predictions": [
            {{
                "field": "Nom du champ (ex: PriceRange)",
                "status": "kept" | "hesitant" | "rejected",
                "value_proposal": "Ta proposition de valeur (ex: €€-€€€) ou vide si incertain",
                "label_fr": "Label humain (ex: Gamme de prix)",
                "reason": "Pourquoi tu as choisi ça"
            }}
        ]
    }}
    """
    
    try:
        r = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "mistral-large-latest", 
                "messages": [{"role": "user", "content": prompt}], 
                "response_format": {"type": "json_object"},
                "temperature": 0.3 # Un peu de créativité pour les propositions
            },
            timeout=20
        )
        return json.loads(r.json()['choices'][0]['message']['content'])
    except Exception as e:
        st.error(f"Erreur IA : {e}")
        return {"predictions": []}

# =============================================================================
# 4. ENGINE (GENERATOR)
# =============================================================================
def generate_final_json(data: EntityData, template_str: str):
    """Fusionne Master + Dynamic Fields dans le Template"""
    
    # 1. Mapping Master Standard
    mapping = {
        "{{MASTER_ORG_TYPE}}": data.org_type,
        "{{MASTER_BRAND_NAME}}": data.brand_name,
        "{{MASTER_LEGAL_NAME}}": data.legal_name,
        "{{MASTER_ALT_1}}": data.alt_names,
        "{{MASTER_DESCRIPTION}}": data.description,
        "{{MASTER_SLOGAN}}": data.slogan,
        "{{MASTER_SITE_URL}}": data.site_url,
        "{{MASTER_LOGO_URL}}": data.logo_url,
        "{{MASTER_SIRET}}": data.siret,
        "{{MASTER_SIREN}}": data.siren,
        "{{MASTER_LEI}}": data.lei,
        "{{MASTER_DUNS}}": data.duns,
        "{{MASTER_QID}}": data.qid,
        "{{MASTER_STREET}}": data.street,
        "{{MASTER_CITY}}": data.city,
        "{{MASTER_ZIP}}": data.zip_code,
        "{{MASTER_COUNTRY}}": data.country,
        "{{MASTER_PHONE}}": data.phone,
        "{{MASTER_EMAIL}}": data.email,
        "{{MASTER_FOUNDING_DATE}}": data.founding_date,
        "{{SOCIAL_LINKEDIN}}": data.linkedin,
        "{{SOCIAL_TWITTER}}": data.twitter,
        "{{SOCIAL_WIKI}}": data.wikipedia,
        "{{PAGE_URL}}": data.page_url,
        "{{PAGE_TITLE}}": data.page_title,
        "{{PAGE_META_DESC}}": data.page_desc,
    }
    
    # 2. Injection des champs dynamiques (IA)
    # Note : Cela suppose que ton JSON template a des placeholders génériques 
    # ou alors on utilise une approche simplifiée ici pour les champs clés connus.
    # Pour faire simple et robuste, on mappe les connus :
    
    mapping["{{DYN_PRICE_RANGE}}"] = data.dynamic_fields.get("PriceRange", "")
    mapping["{{DYN_OPENING_HOURS}}"] = data.dynamic_fields.get("OpeningHours", "")
    mapping["{{DYN_AREA_SERVED}}"] = data.dynamic_fields.get("AreaServed", "")
    mapping["{{DYN_AWARDS}}"] = data.dynamic_fields.get("Awards", "")
    mapping["{{DYN_PAYMENT}}"] = data.dynamic_fields.get("PaymentAccepted", "")
    
    final_str = template_str
    for k, v in mapping.items():
        val = str(v) if v else ""
        final_str = final_str.replace(k, val)
        
    return '\n'.join([l for l in final_str.split('\n') if not ("{{" in l and "}}" in l)])

# =============================================================================
# 5. UI PRINCIPALE
# =============================================================================
def render_entity_forge():
    # --- CSS CLEAN UI ---
    st.markdown("""
    <style>
        .block-header { font-size: 1.2rem; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #1e3a8a; border-bottom: 2px solid #e5e7eb; padding-bottom: 5px; }
        .kept-box { border-left: 4px solid #10b981; padding-left: 10px; margin-bottom: 15px; }
        .hesi-box { border-left: 4px solid #f59e0b; padding-left: 10px; margin-bottom: 15px; background-color: #fffbeb; padding: 10px; border-radius: 4px;}
        .search-result-card { padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 5px; cursor: pointer; }
        .search-result-card:hover { background-color: #f0f9ff; }
    </style>
    """, unsafe_allow_html=True)

    # Session Init
    if 'data' not in st.session_state: st.session_state.data = EntityData()
    if 'predictions' not in st.session_state: st.session_state.predictions = None
    if 'search_results_insee' not in st.session_state: st.session_state.search_results_insee = []
    if 'search_results_wiki' not in st.session_state: st.session_state.search_results_wiki = []
    
    d = st.session_state.data

    st.markdown("## 🏗️ Entity Forge : GEO Builder")
    st.caption("Construisez une entité parfaite en 4 blocs : Master > Dynamique > Incertain > Rejeté.")

    # -------------------------------------------------------------------------
    # PHASE DE RECHERCHE (Sélection intelligente)
    # -------------------------------------------------------------------------
    col_search, col_act = st.columns([3, 1])
    with col_search:
        query = st.text_input("Rechercher une organisation (ex: Fnac, EDF...)", label_visibility="collapsed")
    with col_act:
        if st.button("🔍 Trouver", type="primary", use_container_width=True):
            with st.spinner("Scan INSEE & Wikidata..."):
                st.session_state.search_results_insee = INSEEAPI.search_list(query)
                st.session_state.search_results_wiki = WikidataAPI.search_list(query)

    # Affichage des résultats pour sélection
    if st.session_state.search_results_insee or st.session_state.search_results_wiki:
        st.info("Sélectionnez l'entité exacte pour pré-remplir le BLOC 1 :")
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("**Résultats INSEE (Légal)**")
            for item in st.session_state.search_results_insee:
                label = f"{item.get('nom_complet')} ({item.get('siren')}) - {item.get('siege', {}).get('commune')}"
                if st.button(label, key=f"insee_{item.get('siren')}", use_container_width=True):
                    # ACTION : REMPLISSAGE INSEE
                    d.legal_name = item.get('nom_raison_sociale', '')
                    d.brand_name = item.get('nom_complet', '')
                    d.siren = item.get('siren', '')
                    siege = item.get('siege', {})
                    d.siret = siege.get('siret', '')
                    d.street = siege.get('adresse', '')
                    d.city = siege.get('commune', '')
                    d.zip_code = siege.get('code_postal', '')
                    d.founding_date = item.get('date_creation', '')
                    d.iso6523 = f"0002:{d.siren}"
                    # Reset search
                    st.session_state.search_results_insee = []
                    st.session_state.search_results_wiki = []
                    st.success(f"Données INSEE chargées pour {d.brand_name}")
                    st.rerun()

        with c2:
            st.markdown("**Résultats Wikidata (Knowledge)**")
            for item in st.session_state.search_results_wiki:
                label = f"{item['label']} ({item.get('description', 'Pas de desc')})"
                if st.button(label, key=f"wiki_{item['id']}", use_container_width=True):
                    # ACTION : REMPLISSAGE WIKI
                    d.qid = item['id']
                    d.brand_name = item['label']
                    details = WikidataAPI.get_details(d.qid)
                    d.description = details.get('desc', d.description)
                    d.site_url = details.get('website', d.site_url)
                    d.logo_url = details.get('logo', d.logo_url)
                    d.founding_date = details.get('founded', d.founding_date)
                    if details.get('siren'): d.siren = details['siren']
                    
                    soc = details.get('social', {})
                    d.facebook = soc.get('facebook', '')
                    d.twitter = soc.get('twitter', '')
                    d.linkedin = soc.get('linkedin', '')
                    d.wikipedia = f"https://fr.wikipedia.org/wiki/{item['label'].replace(' ', '_')}"
                    
                    # Reset search
                    st.session_state.search_results_insee = []
                    st.session_state.search_results_wiki = []
                    st.success(f"Données Wikidata chargées pour {d.brand_name}")
                    st.rerun()

    st.markdown("---")

    # -------------------------------------------------------------------------
    # BLOC 1 : MASTER DATA (Rempli par API + Utilisateur)
    # -------------------------------------------------------------------------
    st.markdown("<div class='block-header'>1️⃣ BLOC MASTER (Données Fixes)</div>", unsafe_allow_html=True)
    
    with st.expander("Voir / Modifier les données Master", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            d.org_type = st.selectbox("Type", ["Organization", "Corporation", "LocalBusiness"], index=0)
            d.brand_name = st.text_input("Nom de Marque", d.brand_name)
            d.legal_name = st.text_input("Raison Sociale", d.legal_name)
            d.description = st.text_area("Description (SEO)", d.description, height=100)
        with c2:
            d.site_url = st.text_input("Site Web Officiel", d.site_url)
            d.logo_url = st.text_input("URL du Logo", d.logo_url)
            d.siren = st.text_input("SIREN", d.siren)
            d.qid = st.text_input("Wikidata ID", d.qid)
            
        st.markdown("**Réseaux & Contact**")
        c1, c2, c3 = st.columns(3)
        d.linkedin = c1.text_input("LinkedIn", d.linkedin)
        d.twitter = c2.text_input("Twitter", d.twitter)
        d.wikipedia = c3.text_input("Wikipedia", d.wikipedia)
        
        c1, c2 = st.columns(2)
        d.street = c1.text_input("Adresse", d.street)
        d.city = c2.text_input("Ville", d.city)

    # -------------------------------------------------------------------------
    # ANALYSE IA (Le Cerveau)
    # -------------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    col_input, col_btn = st.columns([3, 1])
    
    with col_input:
        sector = st.text_input("Secteur d'activité (pour l'IA)", placeholder="ex: Cabinet d'avocat fiscaliste")
    with col_btn:
        st.write("")
        if st.button("🤖 Mistral Auto-Fill", type="primary", use_container_width=True):
            if not st.secrets.get("mistral", {}).get("api_key"):
                st.error("Pas de clé API Mistral")
            else:
                with st.spinner("L'IA remplit les champs pour vous..."):
                    res = mistral_predict_fields(
                        st.secrets["mistral"]["api_key"], 
                        sector, d.brand_name, d.description
                    )
                    st.session_state.predictions = res.get("predictions", [])

    # -------------------------------------------------------------------------
    # BLOC 2 : CHAMPS DYNAMIQUES (Validés & Pré-remplis)
    # -------------------------------------------------------------------------
    if st.session_state.predictions:
        preds = st.session_state.predictions
        kept = [p for p in preds if p['status'] == 'kept']
        hesitant = [p for p in preds if p['status'] == 'hesitant']
        rejected = [p for p in preds if p['status'] == 'rejected']
        
        st.markdown(f"<div class='block-header'>2️⃣ BLOC DYNAMIQUE (Pertinence : Haute)</div>", unsafe_allow_html=True)
        st.caption(f"Mistral a identifié {len(kept)} champs essentiels et a proposé des valeurs.")
        
        for item in kept:
            field_key = item['field'].split(' ')[0] # Clean "PriceRange (Prix)" -> "PriceRange"
            
            # Layout propre : Label + Raison | Input Pré-rempli
            col_txt, col_inp = st.columns([1, 2])
            with col_txt:
                st.markdown(f"**{item.get('label_fr', item['field'])}**")
                st.caption(f"💡 {item['reason']}")
            with col_inp:
                # On utilise dynamic_fields du dataclass pour stocker
                val = st.text_input(
                    label="Valeur", 
                    value=item.get('value_proposal', ''), 
                    key=f"dyn_{field_key}",
                    label_visibility="collapsed"
                )
                d.dynamic_fields[field_key] = val
        
        # -------------------------------------------------------------------------
        # BLOC 3 : CHAMPS INCERTAINS (À valider)
        # -------------------------------------------------------------------------
        if hesitant:
            st.markdown(f"<div class='block-header'>3️⃣ BLOC INCERTAIN (À valider)</div>", unsafe_allow_html=True)
            for item in hesitant:
                field_key = item['field'].split(' ')[0]
                with st.container():
                    st.markdown(f"""<div class='hesi-box'>
                        <strong>{item['field']}</strong> : {item['reason']}
                    </div>""", unsafe_allow_html=True)
                    
                    use_it = st.checkbox("Utiliser ce champ ?", key=f"chk_{field_key}")
                    if use_it:
                        d.dynamic_fields[field_key] = st.text_input("Valeur", value=item.get('value_proposal', ''))

        # -------------------------------------------------------------------------
        # BLOC 4 : REJETÉS (Masqués)
        # -------------------------------------------------------------------------
        with st.expander(f"🗑️ BLOC 4 : Rejetés par l'IA ({len(rejected)})"):
            for item in rejected:
                st.markdown(f"- **{item['field']}** : {item['reason']}")

    # -------------------------------------------------------------------------
    # EXPORT FINAL
    # -------------------------------------------------------------------------
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    
    # Page Context avant export
    with c1:
        st.markdown("##### 📄 Contexte de la page (Optionnel)")
        cc1, cc2 = st.columns(2)
        d.page_url = cc1.text_input("URL Page", d.page_url)
        d.page_title = cc2.text_input("Titre Page", d.page_title)
    
    with c2:
        st.write("")
        st.write("")
        if st.button("🚀 TÉLÉCHARGER JSON-LD", type="primary", use_container_width=True):
            if os.path.exists(TEMPLATE_PATH):
                with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                final_json = generate_final_json(d, template_content)
                
                st.download_button(
                    label="💾 Sauvegarder .json",
                    data=final_json,
                    file_name=f"schema_{d.brand_name.replace(' ', '_')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.error("Template introuvable.")

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    render_entity_forge()
