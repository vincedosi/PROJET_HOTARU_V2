"""
HOTARU v2 - Engine: Master Data Handler
Gestion des données Master avec enrichissement Wikidata + Mistral
"""

import requests
import json
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime


# ============================================================================
# DATA MODEL
# ============================================================================

@dataclass
class MasterData:
    """Master Data - Fixed, brand-level information"""
    
    # Identity
    brand_name: str = ""
    legal_name: str = ""
    description: str = ""
    slogan: str = ""
    org_type: str = "Corporation"
    
    # Identifiers
    qid: str = ""
    siren: str = ""
    siret: str = ""
    lei: str = ""
    ticker_symbol: str = ""
    stock_exchange: str = ""
    
    # Web & Social
    site_url: str = ""
    wikipedia_url: str = ""
    linkedin_url: str = ""
    twitter_url: str = ""
    facebook_url: str = ""
    instagram_url: str = ""
    youtube_url: str = ""
    tiktok_url: str = ""
    
    # Visual
    logo_url: str = ""
    logo_width: str = "600"
    logo_height: str = "200"
    
    # Contact
    phone: str = ""
    email: str = ""
    fax: str = ""
    
    # Address
    street: str = ""
    city: str = ""
    region: str = ""
    zip_code: str = ""
    country: str = "FR"
    latitude: str = ""
    longitude: str = ""
    
    # Corporate
    founding_date: str = ""
    founder_name: str = ""
    num_employees: str = ""
    annual_revenue: str = ""
    parent_org: str = ""
    
    # Status
    status: str = "pending"
    errors: List[str] = field(default_factory=list)
    last_updated: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dict, excluding meta fields"""
        return {k: v for k, v in asdict(self).items() 
                if v and k not in ['errors', 'status', 'last_updated']}
    
    def count_filled_fields(self) -> int:
        """Count non-empty fields"""
        return len(self.to_dict())


# ============================================================================
# WIKIDATA API CLIENT
# ============================================================================

class WikidataAPI:
    """Client pour l'API Wikidata"""
    
    BASE_URL = "https://www.wikidata.org/w/api.php"
    HEADERS = {"User-Agent": "HotaruEntityForge/2.0"}
    
    @staticmethod
    def search_entity(query: str, limit: int = 5) -> List[Dict]:
        """Recherche une entité par nom"""
        params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "fr",
            "format": "json",
            "limit": limit,
            "type": "item"
        }
        
        try:
            r = requests.get(WikidataAPI.BASE_URL, params=params, 
                           headers=WikidataAPI.HEADERS, timeout=10)
            r.raise_for_status()
            return r.json().get('search', [])
        except Exception as e:
            print(f"Wikidata search error: {e}")
            return []
    
    @staticmethod
    def search_by_siren(siren: str) -> Optional[str]:
        """Recherche un QID par SIREN"""
        sparql_url = "https://query.wikidata.org/sparql"
        query = f"""
        SELECT ?item WHERE {{
            ?item wdt:P1616 "{siren}" .
        }}
        LIMIT 1
        """
        
        try:
            r = requests.get(sparql_url, 
                           params={"query": query, "format": "json"},
                           headers=WikidataAPI.HEADERS, timeout=10)
            r.raise_for_status()
            results = r.json().get('results', {}).get('bindings', [])
            if results:
                uri = results[0]['item']['value']
                return uri.split('/')[-1]  # Extract QID from URI
        except Exception as e:
            print(f"SPARQL error: {e}")
        
        return None
    
    @staticmethod
    def get_entity_data(qid: str) -> Optional[Dict]:
        """Récupère les données complètes d'une entité"""
        params = {
            "action": "wbgetentities",
            "ids": qid,
            "languages": "fr|en",
            "props": "labels|descriptions|claims|sitelinks",
            "format": "json"
        }
        
        try:
            r = requests.get(WikidataAPI.BASE_URL, params=params,
                           headers=WikidataAPI.HEADERS, timeout=10)
            r.raise_for_status()
            
            entity = r.json().get('entities', {}).get(qid, {})
            if not entity:
                return None
            
            labels = entity.get('labels', {})
            descs = entity.get('descriptions', {})
            claims = entity.get('claims', {})
            sitelinks = entity.get('sitelinks', {})
            
            result = {
                "qid": qid,
                "name_fr": labels.get('fr', {}).get('value', ''),
                "name_en": labels.get('en', {}).get('value', ''),
                "desc_fr": descs.get('fr', {}).get('value', ''),
                "desc_en": descs.get('en', {}).get('value', ''),
            }
            
            # SIREN (P1616)
            if 'P1616' in claims:
                try:
                    result["siren"] = claims['P1616'][0]['mainsnak']['datavalue']['value']
                except:
                    pass
            
            # LEI (P1278)
            if 'P1278' in claims:
                try:
                    result["lei"] = claims['P1278'][0]['mainsnak']['datavalue']['value']
                except:
                    pass
            
            # Website (P856)
            if 'P856' in claims:
                try:
                    result["website"] = claims['P856'][0]['mainsnak']['datavalue']['value']
                except:
                    pass
            
            # Founding date (P571)
            if 'P571' in claims:
                try:
                    time_val = claims['P571'][0]['mainsnak']['datavalue']['value']['time']
                    result["founding_date"] = time_val[1:11]  # Extract YYYY-MM-DD
                except:
                    pass
            
            # Logo (P154)
            if 'P154' in claims:
                try:
                    logo_name = claims['P154'][0]['mainsnak']['datavalue']['value']
                    logo_name = logo_name.replace(' ', '_')
                    result["logo_url"] = f"https://commons.wikimedia.org/wiki/Special:FilePath/{logo_name}"
                except:
                    pass
            
            # LinkedIn (P4264)
            if 'P4264' in claims:
                try:
                    linkedin_id = claims['P4264'][0]['mainsnak']['datavalue']['value']
                    result["linkedin_url"] = f"https://www.linkedin.com/company/{linkedin_id}"
                except:
                    pass
            
            # Twitter (P2002)
            if 'P2002' in claims:
                try:
                    twitter_id = claims['P2002'][0]['mainsnak']['datavalue']['value']
                    result["twitter_url"] = f"https://twitter.com/{twitter_id}"
                except:
                    pass
            
            # Facebook (P2013)
            if 'P2013' in claims:
                try:
                    fb_id = claims['P2013'][0]['mainsnak']['datavalue']['value']
                    result["facebook_url"] = f"https://www.facebook.com/{fb_id}"
                except:
                    pass
            
            # Instagram (P2003)
            if 'P2003' in claims:
                try:
                    insta_id = claims['P2003'][0]['mainsnak']['datavalue']['value']
                    result["instagram_url"] = f"https://www.instagram.com/{insta_id}"
                except:
                    pass
            
            # YouTube (P2397)
            if 'P2397' in claims:
                try:
                    yt_id = claims['P2397'][0]['mainsnak']['datavalue']['value']
                    result["youtube_url"] = f"https://www.youtube.com/channel/{yt_id}"
                except:
                    pass
            
            # Employees (P1128)
            if 'P1128' in claims:
                try:
                    result["num_employees"] = str(claims['P1128'][0]['mainsnak']['datavalue']['value']['amount']).lstrip('+')
                except:
                    pass
            
            # Wikipedia
            if 'frwiki' in sitelinks:
                result["wikipedia_url"] = f"https://fr.wikipedia.org/wiki/{sitelinks['frwiki']['title'].replace(' ', '_')}"
            elif 'enwiki' in sitelinks:
                result["wikipedia_url"] = f"https://en.wikipedia.org/wiki/{sitelinks['enwiki']['title'].replace(' ', '_')}"
            
            return result
            
        except Exception as e:
            print(f"Wikidata fetch error: {e}")
            return None


# ============================================================================
# MASTER DATA HANDLER
# ============================================================================

class MasterDataHandler:
    """Gestionnaire principal des données Master"""
    
    MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
    MISTRAL_MODEL = "mistral-large-latest"
    
    def __init__(self):
        self.wikidata = WikidataAPI()
    
    def auto_enrich(self, 
                    search_query: Optional[str] = None,
                    qid: Optional[str] = None,
                    siren: Optional[str] = None) -> MasterData:
        """
        Enrichit automatiquement les données Master depuis Wikidata.
        Accepte soit un nom de recherche, soit un QID, soit un SIREN.
        """
        master = MasterData()
        master.errors = []
        
        # Résolution du QID
        resolved_qid = qid
        
        if not resolved_qid and siren:
            resolved_qid = WikidataAPI.search_by_siren(siren)
            if not resolved_qid:
                master.errors.append(f"SIREN {siren} non trouvé dans Wikidata")
        
        if not resolved_qid and search_query:
            results = WikidataAPI.search_entity(search_query, limit=1)
            if results:
                resolved_qid = results[0]['id']
            else:
                master.errors.append(f"Aucun résultat pour '{search_query}'")
        
        if not resolved_qid:
            master.status = "failed"
            master.errors.append("Impossible de trouver l'entité")
            return master
        
        # Récupération des données
        entity_data = WikidataAPI.get_entity_data(resolved_qid)
        
        if not entity_data:
            master.status = "failed"
            master.errors.append(f"Impossible de récupérer les données pour {resolved_qid}")
            return master
        
        # Mapping des données
        master.qid = entity_data.get('qid', '')
        master.brand_name = entity_data.get('name_fr') or entity_data.get('name_en', '')
        master.description = entity_data.get('desc_fr') or entity_data.get('desc_en', '')
        master.siren = entity_data.get('siren', '') or (siren if siren else '')
        master.lei = entity_data.get('lei', '')
        master.site_url = entity_data.get('website', '')
        master.founding_date = entity_data.get('founding_date', '')
        master.logo_url = entity_data.get('logo_url', '')
        master.linkedin_url = entity_data.get('linkedin_url', '')
        master.twitter_url = entity_data.get('twitter_url', '')
        master.facebook_url = entity_data.get('facebook_url', '')
        master.instagram_url = entity_data.get('instagram_url', '')
        master.youtube_url = entity_data.get('youtube_url', '')
        master.wikipedia_url = entity_data.get('wikipedia_url', '')
        master.num_employees = entity_data.get('num_employees', '')
        
        master.status = "partial"
        master.last_updated = datetime.now().isoformat()
        
        return master
    
    def auto_complete_with_mistral(self, master: MasterData, api_key: str) -> MasterData:
        """
        Complète les champs manquants avec Mistral AI.
        """
        if not api_key:
            master.errors.append("Clé API Mistral manquante")
            return master
        
        existing = master.to_dict()
        
        prompt = f"""Tu es expert en enrichissement de données d'entreprises.

CONTEXTE - Données existantes:
{json.dumps(existing, ensure_ascii=False, indent=2)}

Complète UNIQUEMENT les champs VIDES. Retourne UNIQUEMENT du JSON valide (pas de markdown):

{{
    "legal_name": "Raison sociale officielle",
    "slogan": "Slogan ou tagline (ou vide si inconnu)",
    "description": "Description complète si manquante",
    "phone": "Téléphone principal au format international",
    "email": "Email de contact général",
    "street": "Adresse du siège",
    "city": "Ville du siège",
    "zip_code": "Code postal",
    "region": "Région/État",
    "country": "Code pays ISO (FR, US, etc.)",
    "founder_name": "Nom du fondateur principal",
    "annual_revenue": "CA annuel approximatif",
    "ticker_symbol": "Ticker boursier si coté",
    "stock_exchange": "Bourse (Euronext, NYSE, etc.)"
}}

RÈGLES:
- Ne retourne QUE les champs que tu peux compléter avec certitude
- Laisse vide si incertain
- Utilise des données publiques vérifiables"""

        try:
            response = requests.post(
                self.MISTRAL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.MISTRAL_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1500
                },
                timeout=30
            )
            
            if response.status_code != 200:
                master.errors.append(f"Erreur Mistral API: {response.status_code}")
                return master
            
            content = response.json()['choices'][0]['message']['content']
            content = content.replace("```json", "").replace("```", "").strip()
            enriched_data = json.loads(content)
            
            # Appliquer uniquement les champs vides
            for key, value in enriched_data.items():
                if hasattr(master, key) and value:
                    current_value = getattr(master, key, "")
                    if not current_value:  # Ne remplace que si vide
                        setattr(master, key, value)
            
            master.status = "complete"
            master.last_updated = datetime.now().isoformat()
            
        except json.JSONDecodeError:
            master.errors.append("Erreur parsing JSON Mistral")
        except Exception as e:
            master.errors.append(f"Erreur Mistral: {str(e)}")
        
        return master


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ['MasterData', 'MasterDataHandler', 'WikidataAPI']
