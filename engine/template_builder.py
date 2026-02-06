"""
HOTARU v2 - Engine: Template Builder
Génération de JSON-LD à partir des données Master et Dynamic
"""

import json
from typing import Dict, Optional, Any
from datetime import datetime


class TemplateBuilder:
    """Construit le JSON-LD à partir d'un template et des données"""
    
    def __init__(self, template_path: str = None):
        self.template_path = template_path
        self.template = self._load_template() if template_path else {}
    
    def _load_template(self) -> Dict:
        """Charge le template JSON-LD"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._get_default_template()
        except json.JSONDecodeError:
            return self._get_default_template()
    
    def _get_default_template(self) -> Dict:
        """Template par défaut si aucun fichier trouvé"""
        return {
            "@context": "https://schema.org",
            "@type": "Organization"
        }
    
    def generate_jsonld(self, 
                        master_data: Any,
                        dynamic_data: Any = None,
                        page_data: Dict = None) -> str:
        """
        Génère le JSON-LD complet à partir des données Master + Dynamic + Page
        """
        # Base structure
        jsonld = {
            "@context": "https://schema.org",
            "@type": master_data.org_type if hasattr(master_data, 'org_type') and master_data.org_type else "Organization"
        }
        
        # Identity
        if master_data.brand_name:
            jsonld["name"] = master_data.brand_name
        if master_data.legal_name:
            jsonld["legalName"] = master_data.legal_name
        if master_data.description:
            jsonld["description"] = master_data.description
        if master_data.slogan:
            jsonld["slogan"] = master_data.slogan
        
        # Website
        if master_data.site_url:
            jsonld["url"] = master_data.site_url
        
        # Logo
        if master_data.logo_url:
            jsonld["logo"] = {
                "@type": "ImageObject",
                "url": master_data.logo_url,
                "width": master_data.logo_width if hasattr(master_data, 'logo_width') else "600",
                "height": master_data.logo_height if hasattr(master_data, 'logo_height') else "200"
            }
        
        # Identifiers
        identifiers = []
        if master_data.siren:
            identifiers.append({
                "@type": "PropertyValue",
                "propertyID": "SIREN",
                "value": master_data.siren
            })
        if master_data.siret:
            identifiers.append({
                "@type": "PropertyValue",
                "propertyID": "SIRET",
                "value": master_data.siret
            })
        if master_data.lei:
            identifiers.append({
                "@type": "PropertyValue",
                "propertyID": "LEI",
                "value": master_data.lei
            })
        if identifiers:
            jsonld["identifier"] = identifiers
        
        # Contact
        if master_data.phone:
            jsonld["telephone"] = master_data.phone
        if master_data.email:
            jsonld["email"] = master_data.email
        if master_data.fax:
            jsonld["faxNumber"] = master_data.fax
        
        # Address
        address = {}
        if master_data.street:
            address["streetAddress"] = master_data.street
        if master_data.city:
            address["addressLocality"] = master_data.city
        if master_data.region:
            address["addressRegion"] = master_data.region
        if master_data.zip_code:
            address["postalCode"] = master_data.zip_code
        if master_data.country:
            address["addressCountry"] = master_data.country
        if address:
            address["@type"] = "PostalAddress"
            jsonld["address"] = address
        
        # Geo coordinates
        if hasattr(master_data, 'latitude') and hasattr(master_data, 'longitude'):
            if master_data.latitude and master_data.longitude:
                jsonld["geo"] = {
                    "@type": "GeoCoordinates",
                    "latitude": master_data.latitude,
                    "longitude": master_data.longitude
                }
        
        # Social profiles
        same_as = []
        social_fields = ['wikipedia_url', 'linkedin_url', 'twitter_url', 
                        'facebook_url', 'instagram_url', 'youtube_url', 'tiktok_url']
        for field in social_fields:
            if hasattr(master_data, field):
                url = getattr(master_data, field)
                if url:
                    same_as.append(url)
        if same_as:
            jsonld["sameAs"] = same_as
        
        # Corporate info
        if master_data.founding_date:
            jsonld["foundingDate"] = master_data.founding_date
        if master_data.founder_name:
            jsonld["founder"] = {
                "@type": "Person",
                "name": master_data.founder_name
            }
        if master_data.num_employees:
            jsonld["numberOfEmployees"] = {
                "@type": "QuantitativeValue",
                "value": master_data.num_employees
            }
        if master_data.parent_org:
            jsonld["parentOrganization"] = {
                "@type": "Organization",
                "name": master_data.parent_org
            }
        
        # Stock info
        if hasattr(master_data, 'ticker_symbol') and master_data.ticker_symbol:
            jsonld["tickerSymbol"] = master_data.ticker_symbol
        
        # Wikidata/Knowledge Graph
        if master_data.qid:
            if "sameAs" not in jsonld:
                jsonld["sameAs"] = []
            jsonld["sameAs"].append(f"https://www.wikidata.org/wiki/{master_data.qid}")
        
        # Page-specific data
        if page_data:
            if page_data.get('url'):
                jsonld["mainEntityOfPage"] = {
                    "@type": "WebPage",
                    "@id": page_data['url']
                }
        
        # Dynamic data (predictions from AI)
        if dynamic_data:
            # Merge validated predictions
            if hasattr(dynamic_data, '__iter__'):
                for field in dynamic_data:
                    if hasattr(field, 'key') and hasattr(field, 'value') and hasattr(field, 'confidence'):
                        if field.confidence > 0.7 and field.value:
                            # Add high-confidence predictions
                            jsonld[field.key] = field.value
        
        return json.dumps(jsonld, ensure_ascii=False, indent=2)
    
    def generate_webpage_jsonld(self, master_data: Any, page_data: Dict) -> str:
        """Génère un JSON-LD WebPage"""
        jsonld = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "url": page_data.get('url', ''),
            "name": page_data.get('title', ''),
            "description": page_data.get('meta_desc', ''),
            "dateModified": datetime.now().isoformat(),
            "publisher": {
                "@type": "Organization",
                "name": master_data.brand_name if hasattr(master_data, 'brand_name') else "",
                "url": master_data.site_url if hasattr(master_data, 'site_url') else ""
            }
        }
        
        if master_data.logo_url:
            jsonld["publisher"]["logo"] = {
                "@type": "ImageObject",
                "url": master_data.logo_url
            }
        
        return json.dumps(jsonld, ensure_ascii=False, indent=2)


__all__ = ['TemplateBuilder']
