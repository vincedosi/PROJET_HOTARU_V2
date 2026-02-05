"""
DYNAMIC DATA HANDLER
Handles contextual, AI-predicted data based on business sector using Mistral AI
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json


@dataclass
class DynamicField:
    """Structure for a single dynamic field prediction"""
    key: str
    value: str
    confidence: float  # 0.0 to 1.0
    decision: str  # "keep", "hesitant", "reject"
    reason: str
    category: str  # e.g., "product", "article", "service"


@dataclass
class DynamicData:
    """Dynamic data structure for sector-specific predictions"""
    sector: str = ""  # A-Q (Article, Product, Recipe, Event, etc.)
    fields: List[DynamicField] = field(default_factory=list)
    status: str = "pending"  # pending, processing, complete, failed
    errors: List[str] = field(default_factory=list)


class MistralAI:
    """Mistral AI client for dynamic field prediction"""
    
    # Sector definitions matching the JSON-LD template
    SECTORS = {
        "A": "Article/BlogPosting",
        "B": "Product/Offer",
        "C": "Recipe",
        "D": "Event",
        "E": "Course/EducationalOccupationalProgram",
        "F": "JobPosting",
        "G": "LocalBusiness (extensions)",
        "H": "Service",
        "I": "SoftwareApplication",
        "J": "Book",
        "K": "Movie",
        "L": "MusicAlbum",
        "M": "MedicalEntity",
        "N": "Vehicle",
        "O": "Podcast",
        "P": "VideoGame",
        "Q": "Dataset"
    }
    
    # Field mappings per sector (from JSON template analysis)
    SECTOR_FIELDS = {
        "A": ["DYN_ARTICLE_HEADLINE", "DYN_WORD_COUNT", "DYN_AUTHOR", "DYN_ARTICLE_BODY"],
        "B": ["DYN_PRODUCT_NAME", "DYN_SKU", "DYN_PRICE", "DYN_AVAILABILITY", "DYN_BRAND"],
        "C": ["DYN_RECIPE_NAME", "DYN_PREP_TIME", "DYN_COOK_TIME", "DYN_INGREDIENTS"],
        "D": ["DYN_EVENT_NAME", "DYN_START_DATE", "DYN_LOCATION", "DYN_PERFORMER"],
        "E": ["DYN_COURSE_NAME", "DYN_PROVIDER", "DYN_DURATION", "DYN_COURSE_MODE"],
        "F": ["DYN_JOB_TITLE", "DYN_SALARY", "DYN_EMPLOYMENT_TYPE", "DYN_DATE_POSTED"],
        "G": ["DYN_OPENING_HOURS", "DYN_PRICE_RANGE", "DYN_AREA_SERVED", "DYN_PAYMENT_ACCEPTED"],
        "H": ["DYN_SERVICE_TYPE", "DYN_SERVICE_OUTPUT", "DYN_PROVIDER_MOBILITY"],
        "I": ["DYN_APP_NAME", "DYN_OS", "DYN_APP_CATEGORY", "DYN_APP_VERSION"],
        "J": ["DYN_ISBN", "DYN_BOOK_FORMAT", "DYN_NUM_PAGES", "DYN_PUBLISHER"],
        "K": ["DYN_MOVIE_TITLE", "DYN_DIRECTOR", "DYN_DURATION", "DYN_GENRE"],
        "L": ["DYN_ALBUM_NAME", "DYN_ARTIST", "DYN_NUM_TRACKS", "DYN_GENRE"],
        "M": ["DYN_CONDITION", "DYN_TREATMENT", "DYN_SYMPTOMS", "DYN_RISK_FACTORS"],
        "N": ["VEHICLE_MAKE", "VEHICLE_MODEL", "VEHICLE_VIN", "VEHICLE_YEAR"],
        "O": ["PODCAST_SERIES", "PODCAST_EP_NUM", "PODCAST_DURATION", "PODCAST_HOST"],
        "P": ["GAME_PLATFORM", "GAME_PLAYERS", "GAME_MODE", "GAME_GENRE"],
        "Q": ["DATASET_URL", "DATASET_TEMPORAL", "DATASET_VARIABLES", "DATASET_LICENSE"]
    }
    
    @staticmethod
    def build_prompt(company_name: str, description: str, sector: str, website: str = "") -> str:
        """Build structured prompt for Mistral AI"""
        
        sector_name = MistralAI.SECTORS.get(sector, "Unknown")
        fields = MistralAI.SECTOR_FIELDS.get(sector, [])
        
        prompt = f"""Tu es un expert en structured data et Schema.org. 

MISSION: Prédire les champs dynamiques pour enrichir les données structurées JSON-LD d'une entreprise.

ENTREPRISE:
- Nom: {company_name}
- Description: {description}
- Site web: {website}

SECTEUR DÉTECTÉ: {sector} - {sector_name}

CHAMPS À PRÉDIRE:
{chr(10).join(f"- {field}" for field in fields)}

RÈGLES:
1. Pour chaque champ, fournis:
   - value: Valeur prédite (laisse vide si impossible à deviner)
   - confidence: Score de 0.0 à 1.0
   - decision: "keep" (>0.7), "hesitant" (0.4-0.7), ou "reject" (<0.4)
   - reason: Justification courte en français

2. Base-toi sur:
   - Le nom de l'entreprise
   - Sa description
   - Le type de secteur
   - Les conventions Schema.org

3. Sois conservateur: mieux vaut laisser vide que d'inventer.

IMPORTANT: Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après, au format:
{{
  "predictions": [
    {{
      "key": "DYN_PRODUCT_NAME",
      "value": "Widget Premium",
      "confidence": 0.8,
      "decision": "keep",
      "reason": "Déduit du nom de l'entreprise"
    }}
  ]
}}"""
        
        return prompt
    
    @staticmethod
    def predict_fields(company_name: str, description: str, sector: str, website: str = "", api_key: str = "") -> DynamicData:
        """Predict dynamic fields using Mistral AI"""
        
        dynamic_data = DynamicData(sector=sector)
        
        # Check if API key is available
        if not api_key:
            api_key = os.getenv("MISTRAL_API_KEY", "")
        
        if not api_key:
            dynamic_data.status = "failed"
            dynamic_data.errors.append("Mistral API key not configured")
            return dynamic_data
        
        # Build prompt
        prompt = MistralAI.build_prompt(company_name, description, sector, website)
        
        try:
            # Call Mistral API
            import requests
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "mistral-large-latest",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Low temperature for consistent predictions
                "max_tokens": 2000
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse response
            content = result["choices"][0]["message"]["content"]
            
            # Extract JSON from response (handle potential markdown formatting)
            content_clean = content.strip()
            if content_clean.startswith("```json"):
                content_clean = content_clean[7:]
            if content_clean.endswith("```"):
                content_clean = content_clean[:-3]
            content_clean = content_clean.strip()
            
            predictions_data = json.loads(content_clean)
            
            # Convert to DynamicField objects
            for pred in predictions_data.get("predictions", []):
                field = DynamicField(
                    key=pred.get("key", ""),
                    value=pred.get("value", ""),
                    confidence=pred.get("confidence", 0.0),
                    decision=pred.get("decision", "reject"),
                    reason=pred.get("reason", ""),
                    category=sector
                )
                dynamic_data.fields.append(field)
            
            dynamic_data.status = "complete"
            
        except requests.exceptions.RequestException as e:
            dynamic_data.status = "failed"
            dynamic_data.errors.append(f"Mistral API error: {str(e)}")
        except json.JSONDecodeError as e:
            dynamic_data.status = "failed"
            dynamic_data.errors.append(f"JSON parsing error: {str(e)}")
        except Exception as e:
            dynamic_data.status = "failed"
            dynamic_data.errors.append(f"Unexpected error: {str(e)}")
        
        return dynamic_data


class DynamicDataHandler:
    """Main handler for dynamic data prediction"""
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.mistral = MistralAI()
    
    def predict_sector(self, company_name: str, description: str) -> str:
        """Auto-detect most likely sector based on company description"""
        
        # Simple keyword-based heuristics (can be enhanced with ML)
        description_lower = description.lower()
        name_lower = company_name.lower()
        combined = f"{name_lower} {description_lower}"
        
        sector_keywords = {
            "B": ["produit", "vente", "commerce", "boutique", "e-commerce", "shop"],
            "H": ["service", "conseil", "consulting", "agence", "bureau"],
            "I": ["software", "application", "app", "saas", "logiciel"],
            "A": ["blog", "article", "média", "presse", "journal"],
            "C": ["recette", "cuisine", "restaurant", "chef"],
            "D": ["événement", "concert", "festival", "spectacle"],
            "E": ["formation", "cours", "école", "université", "training"],
            "F": ["emploi", "recrutement", "job", "carrière"],
            "G": ["local", "magasin", "point de vente", "retail"],
            "J": ["livre", "édition", "publisher", "book"],
            "K": ["film", "cinéma", "movie", "production"],
            "L": ["musique", "album", "artist", "label"],
            "M": ["médical", "santé", "health", "clinic", "hospital"],
            "N": ["véhicule", "auto", "car", "vehicle"],
            "O": ["podcast", "audio", "émission"],
            "P": ["jeu", "game", "gaming", "esport"],
            "Q": ["data", "dataset", "research", "recherche"]
        }
        
        # Score each sector
        scores = {}
        for sector, keywords in sector_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined)
            scores[sector] = score
        
        # Return sector with highest score (default to B - Product if no match)
        best_sector = max(scores, key=scores.get) if max(scores.values()) > 0 else "B"
        
        return best_sector
    
    def generate_predictions(
        self,
        company_name: str,
        description: str,
        sector: str = None,
        website: str = ""
    ) -> DynamicData:
        """Generate dynamic field predictions"""
        
        # Auto-detect sector if not provided
        if not sector:
            sector = self.predict_sector(company_name, description)
        
        # Generate predictions using Mistral
        dynamic_data = self.mistral.predict_fields(
            company_name=company_name,
            description=description,
            sector=sector,
            website=website,
            api_key=self.api_key
        )
        
        return dynamic_data
    
    def get_fields_by_decision(self, dynamic_data: DynamicData) -> Dict[str, List[DynamicField]]:
        """Group fields by decision category for UX display"""
        
        grouped = {
            "keep": [],      # ✅ High confidence (>0.7)
            "hesitant": [],  # ⚠️ Medium confidence (0.4-0.7)
            "reject": []     # 🚫 Low confidence (<0.4)
        }
        
        for field in dynamic_data.fields:
            decision = field.decision
            if decision in grouped:
                grouped[decision].append(field)
        
        return grouped
