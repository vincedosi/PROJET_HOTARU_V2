"""
HOTARU v2 - Engine: Master Data Handler
Gestion des données Master avec enrichissement Wikidata + Mistral
"""

import requests
import json
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class MasterData:
    """Master Data - Fixed, brand-level information"""
    
    brand_name: str = ""
    legal_name: str = ""
    description: str = ""
    slogan: str = ""
    org_type: str = "Corporation"
    
    qid: str = ""
    siren: str = ""
    siret: str = ""
    lei: str = ""
    ticker_symbol: str = ""
    stock_exchange: str = ""
    
    site_url: str = ""
    wikipedia_url: str = ""
    linkedin_url: str = ""
    twitter_url: str = ""
    facebook_url: str = ""
    instagram_url: str = ""
    youtube_url: str = ""
    tiktok_url: str = ""
    
    logo_url: str = ""
    logo_width: str = "600"
    logo_height: str = "200"
    
    phone: str = ""
    email: str = ""
    fax: str = ""
    
    street: str = ""
    city: str = ""
    region: str = ""
    zip_code: str = ""
    country: str = "FR"
    latitude: str = ""
    longitude: str = ""
    
    founding_date: str = ""
    founder_name: str = ""
    num_employees: str = ""
    annual_revenue: str = ""
    parent_org: str = ""
    
    status: str = "pending"
    errors: List[str] = field(default_factory=list)
    last_updated: str = ""
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() 
                if v and k not in ['errors', 'status', 'last_updated']}
    
    def count_filled_fields(self) -> int:
        return len(self.to_dict())


class WikidataAPI:
    BASE_URL = "https://www.wikidata.org/w/api.php"
    HEADERS = {"User-Agent": "HotaruEntityForge/2.0"}
    
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
        sparql_url = "https://query.wikidata.org/sparql"
        query = f'SELECT ?item WHERE {{ ?item wdt:P1616 "{siren}" . }} LIMIT 1'
        try:
            r = requests.get(sparql_url, params={"query": query, "format": "json"},
                           headers=WikidataAPI.HEADERS, timeout=10)
            r.raise_for_status()
            results = r.json().get('results', {}).get('bindings', [])
            if results:
                return results[0]['item']['value'].split('/')[-1]
        except:
            pass
        return None
    
    @staticmethod
    def get_entity_data(qid: str) -> Optional[Dict]:
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
            
            # SIREN, LEI, Website
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
            
            # Founding date
            if 'P571' in claims:
                try:
                    result["founding_date"] = claims['P571'][0]['mainsnak']['datavalue']['value']['time'][1:11]
                except:
                    pass
            
            # Logo
            if 'P154' in claims:
                try:
                    logo = claims['P154'][0]['mainsnak']['datavalue']['value'].replace(' ', '_')
                    result["logo_url"] = f"https://commons.wikimedia.org/wiki/Special:FilePath/{logo}"
                except:
                    pass
            
            # Social media
            if 'P4264' in claims:
                try:
                    val = claims['P4264'][0]['mainsnak']['datavalue']['value']
                    result["linkedin_url"] = f"https://www.linkedin.com/company/{val}"
                except:
                    pass
            if 'P2002' in claims:
                try:
                    val = claims['P2002'][0]['mainsnak']['datavalue']['value']
                    result["twitter_url"] = f"https://twitter.com/{val}"
                except:
                    pass
            if 'P2013' in claims:
                try:
                    val = claims['P2013'][0]['mainsnak']['datavalue']['value']
                    result["facebook_url"] = f"https://www.facebook.com/{val}"
                except:
                    pass
            if 'P2003' in claims:
                try:
                    val = claims['P2003'][0]['mainsnak']['datavalue']['value']
                    result["instagram_url"] = f"https://www.instagram.com/{val}"
                except:
                    pass
            if 'P2397' in claims:
                try:
                    val = claims['P2397'][0]['mainsnak']['datavalue']['value']
                    result["youtube_url"] = f"https://www.youtube.com/channel/{val}"
                except:
                    pass
            
            # Employees
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


class MasterDataHandler:
    MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
    MISTRAL_MODEL = "mistral-large-latest"
    
    def __init__(self):
        self.wikidata = WikidataAPI()
    
    def auto_enrich(self, search_query: Optional[str] = None,
                    qid: Optional[str] = None, siren: Optional[str] = None) -> MasterData:
        master = MasterData()
        master.errors = []
        resolved_qid = qid
        
        if not resolved_qid and siren:
            resolved_qid = WikidataAPI.search_by_siren(siren)
            if not resolved_qid:
                master.errors.append(f"SIREN {siren} non trouvé")
        
        if not resolved_qid and search_query:
            results = WikidataAPI.search_entity(search_query, limit=1)
            if results:
                resolved_qid = results[0]['id']
            else:
                master.errors.append(f"Aucun résultat pour '{search_query}'")
        
        if not resolved_qid:
            master.status = "failed"
            master.errors.append("Entité introuvable")
            return master
        
        entity_data = WikidataAPI.get_entity_data(resolved_qid)
        if not entity_data:
            master.status = "failed"
            master.errors.append(f"Données indisponibles pour {resolved_qid}")
            return master
        
        master.qid = entity_data.get('qid', '')
        master.brand_name = entity_data.get('name_fr') or entity_data.get('name_en', '')
        master.description = entity_data.get('desc_fr') or entity_data.get('desc_en', '')
        master.siren = entity_data.get('siren', '') or (siren or '')
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
        """Appelle l'API Mistral pour enrichir les champs manquants et journalise le détail."""

        if not api_key:
            master.errors.append("Clé API Mistral manquante")
            return master

        existing = master.to_dict()
        prompt = f"""Tu es expert en enrichissement de données d'entreprises.
CONTEXTE (JSON existant, certains champs peuvent déjà être remplis) :
{json.dumps(existing, ensure_ascii=False)}

Complète UNIQUEMENT les champs manquants ou vides en respectant strictement ce schéma JSON :
{{
  "legal_name": "<raison sociale complète de l'entreprise>",
  "slogan": "<slogan marketing concis>",
  "phone": "<numéro de téléphone international (ex: +33...)>",
  "email": "<adresse email de contact>",
  "street": "<adresse postale (rue et numéro)>",
  "city": "<ville>",
  "zip_code": "<code postal>",
  "region": "<région ou état>",
  "country": "<pays>",
  "founder_name": "<nom du ou des fondateurs>",
  "annual_revenue": "<chiffre d'affaires annuel (avec devise)>",
  "ticker_symbol": "<ticker boursier si coté, sinon laisse une chaîne vide>",
  "stock_exchange": "<nom de la bourse où l'entreprise est cotée, sinon laisse une chaîne vide>"
}}

IMPORTANT :
- Ne renvoie que ce JSON (aucun texte avant ou après).
- Pour un champ inconnu, renvoie une chaîne vide "".
"""

        try:
            response = requests.post(
                self.MISTRAL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.MISTRAL_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1500,
                },
                timeout=30,
            )

            master.errors.append(f"[Mistral] Statut HTTP: {response.status_code}")

            if response.status_code != 200:
                master.errors.append(
                    f"[Mistral] Réponse brute: {response.text[:300]}..."
                )
                master.errors.append("Erreur Mistral API: statut différent de 200")
                return master

            try:
                resp_json = response.json()
            except Exception as e_json:
                master.errors.append(f"[Mistral] Erreur parse JSON brut: {e_json}")
                master.errors.append(f"[Mistral] Contenu brut: {response.text[:400]}")
                return master

            content = (
                resp_json.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if not content or not str(content).strip():
                master.errors.append("[Mistral] Contenu de réponse vide.")
                return master

            master.errors.append(f"[Mistral] Contenu brut: {str(content)[:300]}...")

            # Nettoyage éventuel des balises ```json
            if isinstance(content, str):
                content_clean = (
                    content.replace("```json", "").replace("```", "").strip()
                )
            else:
                content_clean = str(content).strip()

            try:
                enriched = json.loads(content_clean or "{}")
            except json.JSONDecodeError as e_json:
                master.errors.append(
                    f"[Mistral] Erreur parsing JSON: {e_json} / payload: {content_clean[:300]}..."
                )
                return master

            updated_keys = []
            for key, value in enriched.items():
                if hasattr(master, key) and isinstance(value, str):
                    if value and not getattr(master, key, ""):
                        setattr(master, key, value)
                        updated_keys.append(key)

            if updated_keys:
                master.errors.append(
                    "[Mistral] Champs mis à jour: " + ", ".join(updated_keys)
                )
                master.status = "complete"
            else:
                master.errors.append(
                    "[Mistral] Aucun champ mis à jour (déjà remplis ou réponses vides)."
                )

            master.last_updated = datetime.now().isoformat()
        except Exception as e:
            master.errors.append(f"[Mistral] Exception: {str(e)}")
        return master


__all__ = ['MasterData', 'MasterDataHandler', 'WikidataAPI']
