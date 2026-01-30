"""
HOTARU - AI Clustering Module
Uses Mistral AI API to intelligently categorize and group URLs.

Features:
- Progress callback for UI feedback
- Streaming response handling
- Smart category naming in French
"""

import streamlit as st
import requests
import json
import time
from typing import List, Dict, Optional, Callable, Generator


def categorize_urls_with_ai(
    urls: List[Dict],
    site_url: str,
    api_key: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> Optional[Dict]:
    """
    Use Mistral AI to intelligently categorize URLs into meaningful groups.

    Args:
        urls: List of URL dictionaries with path, title, etc.
        site_url: The base site URL
        api_key: Mistral API key
        progress_callback: Optional callback for progress updates (message, percent)
        log_callback: Optional callback for log messages

    Returns:
        Dictionary with clusters and renamed pages
    """
    if not api_key:
        if log_callback:
            log_callback("❌ Cle API manquante")
        return None

    def log(msg: str):
        if log_callback:
            log_callback(msg)

    def progress(msg: str, pct: float):
        if progress_callback:
            progress_callback(msg, pct)

    log("🚀 Demarrage de l'analyse IA...")
    progress("Preparation des donnees...", 0.1)

    # Prepare URL data for the prompt
    nodes_data = []
    for u in urls[:80]:  # Limit for API
        nodes_data.append({
            "url": u.get("url", ""),
            "path": u.get("path", ""),
            "title": u.get("title", "")[:60] if u.get("title") else "",
            "h1": u.get("h1", "")[:60] if u.get("h1") else ""
        })

    log(f"📊 {len(nodes_data)} pages preparees pour l'analyse")
    progress("Envoi a Mistral AI...", 0.2)

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

    log("📡 Connexion a l'API Mistral...")
    progress("Attente de la reponse IA...", 0.3)

    try:
        start_time = time.time()

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
            timeout=120
        )

        elapsed = time.time() - start_time
        log(f"⏱️ Reponse recue en {elapsed:.1f}s")
        progress("Traitement de la reponse...", 0.7)

        if response.status_code != 200:
            error_msg = f"Erreur API: {response.status_code}"
            log(f"❌ {error_msg}")
            try:
                error_detail = response.json()
                log(f"   Details: {error_detail.get('error', {}).get('message', 'Inconnu')}")
            except:
                pass
            return None

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        log("✅ Reponse JSON recue")
        progress("Parsing du JSON...", 0.85)

        # Clean JSON from markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        parsed = json.loads(content.strip())

        # Validate structure
        clusters = parsed.get("clusters", [])
        total_pages = sum(len(c.get("pages", [])) for c in clusters)

        log(f"📁 {len(clusters)} clusters crees avec {total_pages} pages")
        progress("Analyse terminee!", 1.0)

        return parsed

    except requests.exceptions.Timeout:
        log("❌ Timeout - L'API n'a pas repondu a temps")
        return None
    except json.JSONDecodeError as e:
        log(f"❌ Erreur parsing JSON: {str(e)}")
        return None
    except Exception as e:
        log(f"❌ Erreur: {str(e)}")
        return None


def generate_smart_graph_data(
    ai_result: Dict,
    site_url: str,
    original_pages: List[Dict],
    patterns_summary: Optional[List[Dict]] = None
) -> Dict:
    """
    Generate graph data from AI-categorized results.

    Creates an organigramme-style graph with:
    - Root node (site)
    - Cluster nodes (categories)
    - Page nodes (individual pages or grouped templates)

    Args:
        ai_result: Result from Mistral with clusters
        site_url: Base site URL
        original_pages: Original pages with scores
        patterns_summary: Optional pattern groups for collapsing similar pages

    Returns:
        Graph data with nodes and edges
    """
    nodes = []
    edges = []

    # Create URL to score mapping
    score_map = {p.get("url", ""): p.get("score", 50) for p in original_pages}

    # Create URL to pattern mapping
    pattern_map = {}
    if patterns_summary:
        for p in original_pages:
            pattern_map[p.get("url", "")] = p.get("pattern_group", "")

    # Root node
    root_label = site_url.replace("https://", "").replace("http://", "").replace("www.", "")
    if len(root_label) > 30:
        root_label = root_label[:27] + "..."

    nodes.append({
        "id": "root",
        "label": root_label,
        "size": 45,
        "color": "#FFFFFF",
        "borderColor": "#000000",
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
            "size": 30,
            "color": "#FFFFFF",
            "borderColor": "#FFD700",
            "type": "cluster",
            "description": cluster.get("description", ""),
            "page_count": len(pages)
        })

        edges.append({
            "source": "root",
            "target": cluster_id,
            "width": 2,
            "color": "#000000"
        })

        # Group pages by pattern if available
        pages_by_pattern: Dict[str, List] = {}
        for page in pages:
            page_url = page.get("url", "")
            pattern = pattern_map.get(page_url, "unique")

            if pattern not in pages_by_pattern:
                pages_by_pattern[pattern] = []
            pages_by_pattern[pattern].append(page)

        # Create nodes for each pattern group or individual page
        node_idx = 0
        for pattern, pattern_pages in pages_by_pattern.items():
            if len(pattern_pages) > 5 and pattern != "unique":
                # Create a grouped node for similar pages
                group_id = f"group_{i}_{node_idx}"
                first_page = pattern_pages[0]

                # Calculate average score
                avg_score = sum(
                    score_map.get(p.get("url", ""), 50) for p in pattern_pages
                ) / len(pattern_pages)

                nodes.append({
                    "id": group_id,
                    "label": f"{first_page.get('label', 'Groupe')} (+{len(pattern_pages)-1})",
                    "size": 20,
                    "color": "#FFFFFF",
                    "borderColor": get_score_color(avg_score),
                    "type": "group",
                    "url": first_page.get("url", ""),
                    "score": avg_score,
                    "page_count": len(pattern_pages),
                    "pages": [p.get("url", "") for p in pattern_pages]
                })

                edges.append({
                    "source": cluster_id,
                    "target": group_id,
                    "width": 1,
                    "color": "#000000"
                })
                node_idx += 1
            else:
                # Create individual nodes (limit to 12 per cluster)
                for j, page in enumerate(pattern_pages[:12]):
                    page_url = page.get("url", "")
                    page_label = page.get("label", "Page")
                    page_id = f"page_{i}_{node_idx}"

                    score = score_map.get(page_url, 50)

                    nodes.append({
                        "id": page_id,
                        "label": page_label[:25],
                        "size": 15,
                        "color": "#FFFFFF",
                        "borderColor": get_score_color(score),
                        "type": "page",
                        "url": page_url,
                        "score": score,
                        "original_path": page.get("original_path", "")
                    })

                    edges.append({
                        "source": cluster_id,
                        "target": page_id,
                        "width": 1,
                        "color": "#000000"
                    })
                    node_idx += 1

    return {
        "nodes": nodes,
        "edges": edges,
        "cluster_count": len(clusters),
        "total_pages": sum(len(c.get("pages", [])) for c in clusters)
    }


def get_score_color(score: float) -> str:
    """Get border color based on score."""
    if score >= 70:
        return "#22C55E"  # Green
    elif score >= 40:
        return "#F97316"  # Orange
    else:
        return "#EF4444"  # Red
