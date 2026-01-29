"""
HOTARU - AI Clustering Module
Uses Mistral AI API to intelligently categorize and group URLs.
"""

import streamlit as st
import requests
import json
from typing import List, Dict, Optional


def categorize_urls_with_ai(urls: List[Dict], site_url: str, api_key: str) -> Optional[Dict]:
    """
    Use Mistral AI to intelligently categorize URLs into meaningful groups.

    Args:
        urls: List of URL dictionaries with path, title, etc.
        site_url: The base site URL
        api_key: Mistral API key (passed from session)

    Returns:
        Dictionary with clusters and renamed pages
    """
    if not api_key:
        return None

    # Prepare URL data for the prompt
    nodes_data = []
    for u in urls[:80]:  # Limit for API
        nodes_data.append({
            "url": u.get("url", ""),
            "path": u.get("path", ""),
            "title": u.get("title", "")[:60] if u.get("title") else "",
            "h1": u.get("h1", "")[:60] if u.get("h1") else ""
        })

    # Expert prompt for architecture analysis
    system_prompt = """Tu es un expert en architecture d'information et UX.
Tu analyses des structures de sites web pour les reorganiser de maniere logique.
Tu reponds UNIQUEMENT en JSON valide, sans texte avant ou apres."""

    user_prompt = f"""Analyse ces pages du site {site_url} et reorganise-les intelligemment.

PAGES A ANALYSER:
{json.dumps(nodes_data, indent=2, ensure_ascii=False)}

MISSION:
1. Cree des CLUSTERS (categories meres) logiques et clairs en francais
2. Associe chaque page au cluster le plus pertinent
3. Renomme chaque page avec un titre COURT et LISIBLE (max 25 caracteres)
   - Exemple: "contact-us.html" -> "Contact"
   - Exemple: "product-category-furniture-sofas" -> "Canapes"
   - Exemple: "cirfa-de-lyon-69" -> "CIRFA Lyon"

REGLES:
- Maximum 8 clusters
- Noms de clusters courts (1-3 mots)
- Noms de pages comprehensibles par un humain
- Garde l'URL originale pour le lien

REPONDS UNIQUEMENT avec ce JSON:
{{
  "clusters": [
    {{
      "name": "Nom du Cluster",
      "description": "Description courte",
      "pages": [
        {{
          "url": "url_originale",
          "label": "Nom Court Lisible",
          "original_path": "/chemin/original"
        }}
      ]
    }}
  ]
}}"""

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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 4000
            },
            timeout=90
        )

        if response.status_code != 200:
            st.error(f"Erreur API Mistral: {response.status_code}")
            return None

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Clean JSON from markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())

    except json.JSONDecodeError as e:
        st.error(f"Erreur parsing: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Erreur: {str(e)}")
        return None


def generate_smart_graph_data(ai_result: Dict, site_url: str, original_pages: List[Dict]) -> Dict:
    """
    Generate graph data from AI-categorized results.

    Args:
        ai_result: Result from Mistral with clusters
        site_url: Base site URL
        original_pages: Original pages with scores

    Returns:
        Graph data with nodes and edges
    """
    nodes = []
    edges = []

    # Create URL to score mapping
    score_map = {p.get("url", ""): p.get("score", 50) for p in original_pages}

    # Root node
    root_label = site_url.replace("https://", "").replace("http://", "").replace("www.", "")
    if len(root_label) > 30:
        root_label = root_label[:27] + "..."

    nodes.append({
        "id": "root",
        "label": root_label,
        "size": 40,
        "color": "#FFFFFF",
        "type": "root",
        "url": site_url
    })

    clusters = ai_result.get("clusters", [])

    for i, cluster in enumerate(clusters):
        cluster_name = cluster.get("name", f"Groupe {i+1}")
        cluster_id = f"cluster_{i}"
        pages = cluster.get("pages", [])

        # Cluster node
        nodes.append({
            "id": cluster_id,
            "label": f"{cluster_name} ({len(pages)})",
            "size": 28,
            "color": "#FFFFFF",
            "type": "cluster",
            "description": cluster.get("description", "")
        })

        edges.append({
            "source": "root",
            "target": cluster_id,
            "width": 2
        })

        # Page nodes
        for j, page in enumerate(pages[:12]):  # Limit per cluster
            page_url = page.get("url", "")
            page_label = page.get("label", "Page")
            page_id = f"page_{i}_{j}"

            # Get score from original data
            score = score_map.get(page_url, 50)

            nodes.append({
                "id": page_id,
                "label": page_label[:25],
                "size": 15,
                "color": "#FFFFFF",
                "type": "page",
                "url": page_url,
                "score": score,
                "original_path": page.get("original_path", "")
            })

            edges.append({
                "source": cluster_id,
                "target": page_id,
                "width": 1
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "cluster_count": len(clusters)
    }
