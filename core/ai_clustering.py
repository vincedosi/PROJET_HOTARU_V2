"""
HOTARU - AI Clustering Module
Uses Mistral AI API to intelligently categorize and group URLs.
"""

import streamlit as st
import requests
import json
from typing import List, Dict, Optional


def get_mistral_api_key() -> Optional[str]:
    """Get Mistral API key from secrets."""
    return st.secrets.get("mistral", {}).get("api_key", None)


def categorize_urls_with_ai(urls: List[Dict], site_url: str) -> Optional[Dict]:
    """
    Use Mistral AI to intelligently categorize URLs into meaningful groups.

    Args:
        urls: List of URL dictionaries with path, title, etc.
        site_url: The base site URL

    Returns:
        Dictionary with categories and their URLs
    """
    api_key = get_mistral_api_key()

    if not api_key:
        st.warning("Cle API Mistral non configuree. Ajoutez-la dans les secrets.")
        return None

    # Prepare URL data for the prompt
    url_list = []
    for u in urls[:100]:  # Limit to 100 URLs for API call
        url_list.append({
            "path": u.get("path", ""),
            "title": u.get("title", "")[:50] if u.get("title") else ""
        })

    prompt = f"""Analyse ces URLs du site {site_url} et cree des categories intelligentes en francais.

URLs a analyser:
{json.dumps(url_list, indent=2, ensure_ascii=False)}

INSTRUCTIONS:
1. Identifie les patterns dans les URLs (ex: /cirfa-*, /emploi-*, /metier-*)
2. Cree des categories claires avec des noms comprehensibles en francais
3. Chaque categorie doit avoir un nom court et descriptif (ex: "CIRFA", "Offres d'emploi", "Metiers", "Actualites")
4. Regroupe les URLs similaires ensemble
5. Maximum 10 categories

Reponds UNIQUEMENT avec un JSON valide dans ce format exact:
{{
  "categories": [
    {{
      "name": "Nom de la categorie",
      "description": "Description courte",
      "url_patterns": ["pattern1", "pattern2"],
      "paths": ["/chemin1", "/chemin2"]
    }}
  ]
}}
"""

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-small-latest",
                "messages": [
                    {
                        "role": "system",
                        "content": "Tu es un expert SEO qui analyse la structure des sites web. Tu reponds uniquement en JSON valide."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            },
            timeout=60
        )

        if response.status_code != 200:
            st.error(f"Erreur API Mistral: {response.status_code} - {response.text}")
            return None

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Parse JSON from response
        # Handle potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())

    except json.JSONDecodeError as e:
        st.error(f"Erreur parsing JSON: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Erreur API: {str(e)}")
        return None


def apply_ai_categories(pages: List[Dict], categories: Dict) -> List[Dict]:
    """
    Apply AI-generated categories to pages.

    Args:
        pages: Original page list
        categories: AI-generated categories

    Returns:
        Updated pages with ai_category field
    """
    if not categories or "categories" not in categories:
        return pages

    cat_list = categories["categories"]

    for page in pages:
        path = page.get("path", "").lower()
        assigned = False

        # Try to match patterns
        for cat in cat_list:
            patterns = cat.get("url_patterns", [])
            paths = cat.get("paths", [])

            # Check patterns
            for pattern in patterns:
                pattern_clean = pattern.lower().replace("*", "")
                if pattern_clean in path:
                    page["ai_category"] = cat["name"]
                    page["ai_category_desc"] = cat.get("description", "")
                    assigned = True
                    break

            if assigned:
                break

            # Check exact paths
            for p in paths:
                if p.lower() == path or path.startswith(p.lower()):
                    page["ai_category"] = cat["name"]
                    page["ai_category_desc"] = cat.get("description", "")
                    assigned = True
                    break

            if assigned:
                break

        if not assigned:
            page["ai_category"] = "Autres"
            page["ai_category_desc"] = "Pages non categorisees"

    return pages


def generate_smart_graph_data(pages: List[Dict], site_url: str) -> Dict:
    """
    Generate smart graph data from AI-categorized pages.

    Args:
        pages: Pages with ai_category field
        site_url: Base site URL

    Returns:
        Graph data with nodes and edges
    """
    nodes = []
    edges = []

    # Root node
    nodes.append({
        "id": "root",
        "label": site_url.replace("https://", "").replace("http://", ""),
        "size": 35,
        "color": "#FFFFFF",
        "type": "root"
    })

    # Group by AI category
    categories = {}
    for page in pages:
        cat = page.get("ai_category", "Autres")
        if cat not in categories:
            categories[cat] = {
                "pages": [],
                "description": page.get("ai_category_desc", "")
            }
        categories[cat]["pages"].append(page)

    # Create category nodes and page nodes
    for cat_name, cat_data in categories.items():
        cat_id = f"cat_{cat_name.replace(' ', '_')}"
        page_count = len(cat_data["pages"])

        # Category node
        nodes.append({
            "id": cat_id,
            "label": f"{cat_name} ({page_count})",
            "size": 25,
            "color": "#FFFFFF",
            "type": "category",
            "description": cat_data["description"]
        })

        edges.append({
            "source": "root",
            "target": cat_id,
            "width": 2
        })

        # Page nodes (limit per category for readability)
        for i, page in enumerate(cat_data["pages"][:15]):
            score = page.get("score", 0)

            # Short label
            path_parts = page["path"].strip("/").split("/")
            short_label = path_parts[-1][:25] if path_parts[-1] else "index"

            page_id = f"page_{hash(page['url']) % 100000}"

            nodes.append({
                "id": page_id,
                "label": short_label,
                "size": 12,
                "color": "#FFFFFF",
                "type": "page",
                "url": page["url"],
                "score": score,
                "title": page.get("title", ""),
                "full_path": page["path"]
            })

            edges.append({
                "source": cat_id,
                "target": page_id,
                "width": 1
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "categories": list(categories.keys())
    }
