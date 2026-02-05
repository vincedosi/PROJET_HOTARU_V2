"""
TEMPLATE BUILDER
Handles placeholder replacement and JSON-LD generation from template
"""

import json
import re
from typing import Dict, Any
from pathlib import Path


class TemplateBuilder:
    """Builds final JSON-LD by replacing placeholders in template"""
    
    def __init__(self, template_path: str):
        """Initialize with path to JSON-LD template"""
        self.template_path = template_path
        self.template_content = self._load_template()
    
    def _load_template(self) -> str:
        """Load template file as string"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            raise Exception(f"Failed to load template: {str(e)}")
    
    def _clean_json_comments(self, json_str: str) -> str:
        """Remove JavaScript-style comments from JSON string"""
        # Remove single-line comments
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        # Remove multi-line comments
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        return json_str
    
    def build_placeholder_map(self, master_data: Any, dynamic_data: Any, page_data: Dict = None) -> Dict[str, str]:
        """Build complete placeholder mapping from all data sources"""
        
        placeholder_map = {}
        
        # MASTER DATA PLACEHOLDERS
        if master_data:
            # Identité
            placeholder_map["{{MASTER_BRAND_NAME}}"] = master_data.brand_name
            placeholder_map["{{MASTER_LEGAL_NAME}}"] = master_data.legal_name or master_data.brand_name
            placeholder_map["{{MASTER_ALT_1}}"] = master_data.alt_name_1
            placeholder_map["{{MASTER_ALT_2}}"] = master_data.alt_name_2
            placeholder_map["{{MASTER_DESCRIPTION}}"] = master_data.description
            placeholder_map["{{MASTER_SLOGAN}}"] = master_data.slogan
            placeholder_map["{{MASTER_SITE_URL}}"] = master_data.site_url
            placeholder_map["{{MASTER_ORG_TYPE}}"] = master_data.org_type
            
            # Identifiants légaux
            placeholder_map["{{MASTER_SIREN}}"] = master_data.siren
            placeholder_map["{{MASTER_SIRET}}"] = master_data.siret or master_data.siren
            placeholder_map["{{MASTER_LEI}}"] = master_data.lei
            placeholder_map["{{MASTER_DUNS}}"] = master_data.duns
            placeholder_map["{{MASTER_GLN}}"] = master_data.gln
            placeholder_map["{{MASTER_QID}}"] = master_data.qid
            
            # Visuel
            placeholder_map["{{MASTER_LOGO_URL}}"] = master_data.logo_url
            placeholder_map["{{MASTER_LOGO_W}}"] = master_data.logo_width
            placeholder_map["{{MASTER_LOGO_H}}"] = master_data.logo_height
            placeholder_map["{{MASTER_IMAGE}}"] = master_data.image_url
            
            # Knowledge Graph
            placeholder_map["{{MASTER_WIKIPEDIA}}"] = master_data.wikipedia_url
            placeholder_map["{{MASTER_LINKEDIN}}"] = master_data.linkedin_url
            placeholder_map["{{MASTER_TWITTER}}"] = master_data.twitter_url
            placeholder_map["{{MASTER_FACEBOOK}}"] = master_data.facebook_url
            placeholder_map["{{MASTER_INSTAGRAM}}"] = master_data.instagram_url
            placeholder_map["{{MASTER_YOUTUBE}}"] = master_data.youtube_url
            placeholder_map["{{MASTER_TIKTOK}}"] = master_data.tiktok_url
            
            # Expertise
            placeholder_map["{{MASTER_EXPERTISE_1}}"] = master_data.expertise_1
            placeholder_map["{{MASTER_EXP_1_WIKI}}"] = master_data.expertise_1_wiki
            placeholder_map["{{MASTER_EXPERTISE_2}}"] = master_data.expertise_2
            placeholder_map["{{MASTER_EXP_2_WIKI}}"] = master_data.expertise_2_wiki
            
            # Adresse
            placeholder_map["{{MASTER_STREET}}"] = master_data.street
            placeholder_map["{{MASTER_CITY}}"] = master_data.city
            placeholder_map["{{MASTER_REGION}}"] = master_data.region
            placeholder_map["{{MASTER_ZIP}}"] = master_data.zip_code
            placeholder_map["{{MASTER_COUNTRY}}"] = master_data.country
            placeholder_map["{{MASTER_LAT}}"] = master_data.latitude
            placeholder_map["{{MASTER_LONG}}"] = master_data.longitude
            placeholder_map["{{MASTER_GOOGLE_MAPS}}"] = master_data.google_maps_url
            
            # Contact
            placeholder_map["{{MASTER_PHONE}}"] = master_data.phone
            placeholder_map["{{MASTER_EMAIL}}"] = master_data.email
            placeholder_map["{{MASTER_FAX}}"] = master_data.fax
            placeholder_map["{{MASTER_PHONE_CS}}"] = master_data.phone_cs or master_data.phone
            placeholder_map["{{MASTER_EMAIL_CS}}"] = master_data.email_cs or master_data.email
            placeholder_map["{{MASTER_PHONE_SALES}}"] = master_data.phone_sales or master_data.phone
            placeholder_map["{{MASTER_EMAIL_SALES}}"] = master_data.email_sales or master_data.email
            placeholder_map["{{MASTER_PHONE_TECH}}"] = master_data.phone_tech or master_data.phone
            placeholder_map["{{MASTER_EMAIL_TECH}}"] = master_data.email_tech or master_data.email
            
            # Structure corporate
            placeholder_map["{{MASTER_FOUNDER_NAME}}"] = master_data.founder_name
            placeholder_map["{{MASTER_FOUNDER_URL}}"] = master_data.founder_url
            placeholder_map["{{MASTER_FOUNDING_DATE}}"] = master_data.founding_date
            placeholder_map["{{MASTER_PARENT_ORG}}"] = master_data.parent_org
            placeholder_map["{{MASTER_NUM_EMPLOYEES}}"] = master_data.num_employees
            
            # Social proof
            placeholder_map["{{MASTER_RATING_VALUE}}"] = master_data.rating_value
            placeholder_map["{{MASTER_RATING_COUNT}}"] = master_data.rating_count
            placeholder_map["{{MASTER_REVIEW_COUNT}}"] = master_data.review_count
            
            # Financier
            placeholder_map["{{MASTER_TICKER}}"] = master_data.ticker_symbol
            placeholder_map["{{MASTER_STOCK_EXCHANGE}}"] = master_data.stock_exchange
            placeholder_map["{{MASTER_REVENUE}}"] = master_data.annual_revenue
        
        # DYNAMIC DATA PLACEHOLDERS
        if dynamic_data and dynamic_data.fields:
            for field in dynamic_data.fields:
                # Only include fields with "keep" decision
                if field.decision == "keep" and field.value:
                    placeholder_map[f"{{{{{field.key}}}}}"] = field.value
        
        # PAGE DATA PLACEHOLDERS
        if page_data:
            for key, value in page_data.items():
                placeholder_map[f"{{{{PAGE_{key.upper()}}}}}"] = str(value)
        
        return placeholder_map
    
    def replace_placeholders(self, content: str, placeholder_map: Dict[str, str]) -> str:
        """Replace all placeholders in content with values"""
        
        result = content
        
        for placeholder, value in placeholder_map.items():
            # Only replace if value is not empty
            if value:
                result = result.replace(placeholder, value)
        
        return result
    
    def remove_empty_placeholders(self, content: str) -> str:
        """Remove lines containing unreplaced placeholders"""
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Check if line contains any unreplaced placeholder
            if not re.search(r'\{\{[A-Z_]+\}\}', line):
                cleaned_lines.append(line)
            # Keep structural lines even if they have placeholders
            elif any(marker in line for marker in ['{', '}', '[', ']', '@context', '@type', '@id']):
                # Remove the placeholder but keep the line structure
                cleaned_line = re.sub(r'"[^"]*\{\{[A-Z_]+\}\}[^"]*"', '""', line)
                cleaned_line = re.sub(r'\{\{[A-Z_]+\}\}', '', cleaned_line)
                if cleaned_line.strip() and cleaned_line.strip() not in [',', '']:
                    cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
    
    def generate_jsonld(
        self,
        master_data: Any,
        dynamic_data: Any = None,
        page_data: Dict = None,
        clean_empty: bool = True
    ) -> str:
        """Generate final JSON-LD content"""
        
        # Build placeholder map
        placeholder_map = self.build_placeholder_map(master_data, dynamic_data, page_data)
        
        # Replace placeholders
        content = self.replace_placeholders(self.template_content, placeholder_map)
        
        # Clean empty placeholders
        if clean_empty:
            content = self.remove_empty_placeholders(content)
        
        # Clean comments
        content = self._clean_json_comments(content)
        
        return content
    
    def validate_json(self, json_str: str) -> tuple[bool, str]:
        """Validate if generated content is valid JSON"""
        try:
            json.loads(json_str)
            return True, "Valid JSON"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
    
    def generate_and_validate(
        self,
        master_data: Any,
        dynamic_data: Any = None,
        page_data: Dict = None
    ) -> tuple[str, bool, str]:
        """Generate JSON-LD and validate it"""
        
        # Generate content
        content = self.generate_jsonld(master_data, dynamic_data, page_data)
        
        # Validate
        is_valid, message = self.validate_json(content)
        
        return content, is_valid, message
    
    def save_to_file(self, content: str, output_path: str) -> bool:
        """Save generated JSON-LD to file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            return False
    
    def get_sector_specific_section(self, sector: str) -> str:
        """Extract sector-specific section from template (for preview)"""
        
        # Define sector line ranges (from template analysis)
        sector_ranges = {
            "A": (251, 350),   # Article/BlogPosting
            "B": (351, 450),   # Product
            "C": (451, 550),   # Recipe
            "D": (551, 650),   # Event
            "E": (651, 750),   # Course
            "F": (751, 850),   # JobPosting
            "G": (851, 950),   # LocalBusiness
            "H": (951, 1000),  # Service
            "I": (1001, 1050), # SoftwareApplication
            "J": (1051, 1100), # Book
            "K": (1101, 1150), # Movie
            "L": (1151, 1200), # MusicAlbum
            "M": (1201, 1250), # MedicalEntity
            "N": (1251, 1300), # Vehicle
            "O": (1301, 1350), # Podcast
            "P": (1351, 1370), # VideoGame
            "Q": (1371, 1378), # Dataset
        }
        
        if sector not in sector_ranges:
            return ""
        
        start_line, end_line = sector_ranges[sector]
        lines = self.template_content.split('\n')
        
        return '\n'.join(lines[start_line:end_line])
