"""
MASTER DATA HANDLER
Handles fixed, factual data from external APIs (Wikidata, INSEE)
"""

import requests
from typing import Dict, Optional, List
from dataclasses import dataclass, field
import re


def log(msg: str):
    """Simple logging helper"""
    print(f"[WikidataAPI] {msg}")


@dataclass
class MasterData:
    """Master data structure for organization entity"""
    # IDENTITÉ
    brand_name: str = ""
    legal_name: str = ""
    alt_name_1: str = ""
    alt_name_2: str = ""
    description: str = ""
    slogan: str = ""
    site_url: str = ""
    org_type: str = "Corporation"
    
    # IDENTIFIANTS LÉGAUX
    siren: str = ""
    siret: str = ""
    lei: str = ""
    duns: str = ""
    gln: str = ""
    qid: str = ""  # Wikidata ID
    
    # VISUEL
    logo_url: str = ""
    logo_width: str = "600"
    logo_height: str = "200"
    image_url: str = ""
    
    # KNOWLEDGE GRAPH
    wikipedia_url: str = ""
    linkedin_url: str = ""
    twitter_url: str = ""
    facebook_url: str = ""
    instagram_url: str = ""
    youtube_url: str = ""
    tiktok_url: str = ""
    
    # EXPERTISE
    expertise_1: str = ""
    expertise_1_wiki: str = ""
    expertise_2: str = ""
    expertise_2_wiki: str = ""
    
    # ADRESSE
    street: str = ""
    city: str = ""
    region: str = ""
    zip_code: str = ""
    country: str = "FR"
    latitude: str = ""
    longitude: str = ""
    google_maps_url: str = ""
    
    # CONTACT
    phone: str = ""
    email: str = ""
    fax: str = ""
    phone_cs: str = ""  # Customer service
    email_cs: str = ""
    phone_sales: str = ""
    email_sales: str = ""
    phone_tech: str = ""
    email_tech: str = ""
    
    # HORAIRES
    opening_hours: str = "Mo-Fr 09:00-18:00"
    
    # STRUCTURE CORPORATE
    founder_name: str = ""
    founder_url: str = ""
    founding_date: str = ""
    parent_org: str = ""
    num_employees: str = ""
    
    # SOCIAL PROOF
    rating_value: str = ""
    rating_count: str = ""
    review_count: str = ""
    
    # FINANCIER
    ticker_symbol: str = ""
    stock_exchange: str = ""
    annual_revenue: str = ""
    
    # STATUT
    status: str = "pending"  # pending, partial, complete, failed
    errors: List[str] = field(default_factory=list)


class WikidataAPI:
    """Wikidata API client for entity enrichment"""
    
    BASE_URL = "https://www.wikidata.org/w/api.php"
    SPARQL_URL = "https://query.wikidata.org/sparql"
    
    @staticmethod
    def search_entity(query: str, limit: int = 5) -> List[Dict]:
        """Search for entities on Wikidata"""
        print(f"[DEBUG] === DEBUT RECHERCHE WIKIDATA ===")
        print(f"[DEBUG] Query: '{query}'")
        print(f"[DEBUG] Limit: {limit}")
        
        params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "fr",
            "uselang": "fr",
            "format": "json",
            "limit": limit,
            "type": "item"
        }
        
        headers = {
            "User-Agent": "HotaruEntityForge/2.0",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(
                WikidataAPI.BASE_URL, 
                params=params, 
                headers=headers, 
                timeout=20
            )
            
            response.raise_for_status()
            data = response.json()
            results = data.get('search', [])
            
            if results:
                return results
            
            # Fallback: try English
            params["language"] = "en"
            params["uselang"] = "en"
            
            response = requests.get(
                WikidataAPI.BASE_URL,
                params=params,
                headers=headers,
                timeout=20
            )
            
            response.raise_for_status()
            data = response.json()
            results = data.get('search', [])
            
            return results
            
        except Exception as e:
            print(f"[ERROR] Wikidata search failed: {e}")
            return []
    
    @staticmethod
    def get_entity_data(qid: str) -> Optional[Dict]:
        """Get complete entity data from Wikidata"""
        print(f"\n[GET_ENTITY] QID: {qid}")
        
        result = {
            "name_fr": "", "name_en": "", "desc_fr": "", "desc_en": "", 
            "siren": "", "lei": "", "website": "", "founding_date": "",
            "parent_qid": "", "parent_name": ""
        }
        
        headers = {
            "User-Agent": "HotaruEntityForge/2.0",
            "Accept": "application/json"
        }
        
        params = {
            "action": "wbgetentities",
            "ids": qid,
            "languages": "fr|en",
            "props": "labels|descriptions|claims",
            "format": "json"
        }
        
        try:
            r = requests.get(
                WikidataAPI.BASE_URL,
                params=params,
                headers=headers,
                timeout=20
            )
            
            if r.status_code != 200:
                return None
            
            entity = r.json().get('entities', {}).get(qid, {})
            
            if not entity:
                return None
            
            labels = entity.get('labels', {})
            descs = entity.get('descriptions', {})
            claims = entity.get('claims', {})
            
            result["name_fr"] = labels.get('fr', {}).get('value', '')
            result["name_en"] = labels.get('en', {}).get('value', '')
            result["desc_fr"] = descs.get('fr', {}).get('value', '')
            result["desc_en"] = descs.get('en', {}).get('value', '')
            
            # SIREN P1616
            if 'P1616' in claims:
                try:
                    result["siren"] = claims['P1616'][0]['mainsnak']['datavalue']['value']
                except:
                    pass
            
            # LEI P1278
            if 'P1278' in claims:
                try:
                    result["lei"] = claims['P1278'][0]['mainsnak']['datavalue']['value']
                except:
                    pass
            
            # Website P856
            if 'P856' in claims:
                try:
                    result["website"] = claims['P856'][0]['mainsnak']['datavalue']['value']
                except:
                    pass
            
            # Founding date P571
            if 'P571' in claims:
                try:
                    time_val = claims['P571'][0]['mainsnak']['datavalue']['value']['time']
                    result["founding_date"] = time_val[1:11]  # +YYYY-MM-DD -> YYYY-MM-DD
                except:
                    pass
            
            return result
            
        except Exception as e:
            print(f"[GET_ENTITY] EXCEPTION: {e}")
            return None
    
    @staticmethod
    def extract_master_data(entity_data: Dict) -> Dict[str, str]:
        """Extract relevant fields from Wikidata entity"""
        result = {}
        
        if not entity_data:
            return result
        
        result["brand_name"] = entity_data.get("name_fr") or entity_data.get("name_en", "")
        result["description"] = entity_data.get("desc_fr") or entity_data.get("desc_en", "")
        result["siren"] = entity_data.get("siren", "")
        result["lei"] = entity_data.get("lei", "")
        result["site_url"] = entity_data.get("website", "")
        result["founding_date"] = entity_data.get("founding_date", "")
        
        return result


class INSEEAPI:
    """INSEE Sirene API client for French company data"""
    
    BASE_URL = "https://api.insee.fr/entreprises/sirene/V3"
    
    @staticmethod
    def get_company_data(siren: str) -> Optional[Dict]:
        """Get company data from INSEE Sirene API"""
        # Clean SIREN
        siren_clean = re.sub(r'\D', '', siren)
        
        if len(siren_clean) != 9:
            return None
        
        # Mock structure for demo
        return {
            "siren": siren_clean,
            "legal_name": "",
            "address": {},
            "activity_code": "",
            "legal_category": "",
        }
    
    @staticmethod
    def extract_master_data(insee_data: Dict) -> Dict[str, str]:
        """Extract relevant fields from INSEE data"""
        result = {}
        
        if not insee_data:
            return result
        
        result["siren"] = insee_data.get("siren", "")
        result["legal_name"] = insee_data.get("legal_name", "")
        
        address = insee_data.get("address", {})
        if address:
            result["street"] = address.get("street", "")
            result["city"] = address.get("city", "")
            result["zip_code"] = address.get("postal_code", "")
        
        return result


class MasterDataHandler:
    """Main handler for master data enrichment"""
    
    def __init__(self):
        self.wikidata = WikidataAPI()
        self.insee = INSEEAPI()
    
    def auto_complete_with_mistral(self, master_data: MasterData, mistral_key: str) -> MasterData:
        """Auto-complete master data with Mistral AI"""
        print(f"\n[MISTRAL_ENRICH] === DEBUT ENRICHISSEMENT ===")
        
        if not mistral_key:
            master_data.errors.append("Clé Mistral manquante")
            return master_data
        
        prompt = f"""Tu es un expert en enrichissement de données entreprises.

ENTREPRISE:
- Nom: {master_data.brand_name}
- QID Wikidata: {master_data.qid}
- Site web: {master_data.site_url}
- Description actuelle: {master_data.description}

MISSION: Enrichir automatiquement TOUTES les données manquantes.

TROUVE ET RETOURNE en JSON:
1. description_seo: Description SEO optimisée 150-180 caractères
2. slogan: Slogan accrocheur de la marque (ou null)
3. expertise: Liste de 3-5 domaines d'expertise (séparés par virgules)
4. wikipedia_url: URL Wikipedia FR si existe (ou null)
5. linkedin_url: URL LinkedIn officielle (ou null)
6. twitter_url: URL Twitter/X officielle (ou null)
7. facebook_url: URL Facebook officielle (ou null)
8. instagram_url: URL Instagram officielle (ou null)
9. youtube_url: URL YouTube officielle (ou null)
10. logo_url: URL du logo si trouvable (ou null)
11. phone: Numéro de téléphone principal (ou null)
12. email: Email contact (ou null)
13. street: Adresse siège social (ou null)
14. city: Ville siège (ou null)
15. postal_code: Code postal (ou null)

RÉPONDS UNIQUEMENT EN JSON VALIDE, PAS DE MARKDOWN:
{{"description_seo": "...", "slogan": "..." ou null, "expertise": "A, B, C", ...}}"""

        try:
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {mistral_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistral-large-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                timeout=30
            )
            
            if response.status_code != 200:
                master_data.errors.append(f"Mistral API error: {response.status_code}")
                return master_data
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Clean JSON
            content = content.replace("```json", "").replace("```", "").strip()
            
            import json
            data = json.loads(content)
            
            # Apply enrichments
            if data.get("description_seo") and not master_data.description:
                master_data.description = data["description_seo"]
            
            if data.get("slogan"):
                master_data.slogan = data["slogan"]
            
            if data.get("expertise"):
                master_data.expertise_1 = data["expertise"]
            
            # Social networks
            if data.get("wikipedia_url"):
                master_data.wikipedia_url = data["wikipedia_url"]
            if data.get("linkedin_url"):
                master_data.linkedin_url = data["linkedin_url"]
            if data.get("twitter_url"):
                master_data.twitter_url = data["twitter_url"]
            if data.get("facebook_url"):
                master_data.facebook_url = data["facebook_url"]
            if data.get("instagram_url"):
                master_data.instagram_url = data["instagram_url"]
            if data.get("youtube_url"):
                master_data.youtube_url = data["youtube_url"]
            
            # Logo
            if data.get("logo_url") and not master_data.logo_url:
                master_data.logo_url = data["logo_url"]
            
            # Contact
            if data.get("phone") and not master_data.phone:
                master_data.phone = data["phone"]
            if data.get("email") and not master_data.email:
                master_data.email = data["email"]
            
            # Address
            if data.get("street") and not master_data.street:
                master_data.street = data["street"]
            if data.get("city") and not master_data.city:
                master_data.city = data["city"]
            if data.get("postal_code") and not master_data.zip_code:
                master_data.zip_code = data["postal_code"]
            
            print(f"[MISTRAL_ENRICH] === FIN ENRICHISSEMENT ===\n")
            
        except Exception as e:
            print(f"[MISTRAL_ENRICH] EXCEPTION: {e}")
            master_data.errors.append(f"Mistral enrichment failed: {str(e)}")
        
        return master_data
    
    def enrich_from_wikidata(self, qid: str, master_data: MasterData) -> MasterData:
        """Enrich master data from Wikidata entity"""
        entity_data = self.wikidata.get_entity_data(qid)
        
        if not entity_data:
            master_data.errors.append(f"Wikidata: QID {qid} not found")
            return master_data
        
        # Extract data
        extracted = self.wikidata.extract_master_data(entity_data)
        
        # Update master_data
        if extracted.get("brand_name"):
            master_data.brand_name = extracted["brand_name"]
        if extracted.get("description"):
            master_data.description = extracted["description"]
        if extracted.get("site_url"):
            master_data.site_url = extracted["site_url"]
        if extracted.get("founding_date"):
            master_data.founding_date = extracted["founding_date"]
        if extracted.get("siren"):
            master_data.siren = extracted["siren"]
        if extracted.get("lei"):
            master_data.lei = extracted["lei"]
        
        # Store QID
        master_data.qid = qid
        
        return master_data
    
    def enrich_from_siren(self, siren: str, master_data: MasterData) -> MasterData:
        """Enrich master data from INSEE SIREN"""
        insee_data = self.insee.get_company_data(siren)
        
        if not insee_data:
            master_data.errors.append(f"INSEE: SIREN {siren} not found")
            return master_data
        
        # Extract data
        extracted = self.insee.extract_master_data(insee_data)
        
        # Update master_data
        if extracted.get("siren"):
            master_data.siren = extracted["siren"]
        if extracted.get("legal_name"):
            master_data.legal_name = extracted["legal_name"]
        if extracted.get("street"):
            master_data.street = extracted["street"]
        if extracted.get("city"):
            master_data.city = extracted["city"]
        if extracted.get("zip_code"):
            master_data.zip_code = extracted["zip_code"]
        
        return master_data
    
    def auto_enrich(self, search_query: str = None, qid: str = None, siren: str = None) -> MasterData:
        """Auto-enrich master data from available identifiers"""
        print(f"\n[AUTO_ENRICH] === DEBUT ===")
        print(f"[AUTO_ENRICH] search_query: {search_query}")
        print(f"[AUTO_ENRICH] qid: {qid}")
        print(f"[AUTO_ENRICH] siren: {siren}")
        
        master_data = MasterData()
        
        # Try Wikidata first if QID provided
        if qid:
            master_data = self.enrich_from_wikidata(qid, master_data)
            master_data.status = "partial"
        
        # Try Wikidata search if query provided and no QID
        elif search_query and not qid:
            results = self.wikidata.search_entity(search_query, limit=1)
            
            if results:
                qid = results[0]["id"]
                master_data = self.enrich_from_wikidata(qid, master_data)
                master_data.status = "partial"
            else:
                master_data.errors.append(f"Wikidata: No results for '{search_query}'")
        
        # Try INSEE if SIREN provided
        if siren:
            master_data = self.enrich_from_siren(siren, master_data)
            master_data.status = "partial"
        
        # Update status
        if master_data.brand_name and (master_data.qid or master_data.siren):
            master_data.status = "complete"
        elif master_data.errors:
            master_data.status = "failed"
        
        print(f"[AUTO_ENRICH] === FIN ===\n")
        
        return master_data
