# =============================================================================
# JSON-LD Service - Logique métier réutilisable (Streamlit + API)
# Clustering DOM, nommage Mistral, génération JSON-LD optimisé, graphe.
# Aucune dépendance Streamlit.
# =============================================================================

import re
import json
import os
import time
import logging
import requests
from typing import Optional, Tuple
from urllib.parse import urlparse
from collections import defaultdict

from bs4 import BeautifulSoup


# Poids du score combiné (total 100)
WEIGHT_STRUCTURE = 0.40   # 40 points - Hiérarchie HTML
WEIGHT_URL = 0.30        # 30 points - Pattern URL
WEIGHT_SEMANTIC = 0.30   # 30 points - Contenu sémantique

# Seuil pour regrouper dans le même cluster (SaaS : pas trop permissif)
CLUSTER_SIMILARITY_THRESHOLD = 0.85

# Balises de structure prises en compte (comptage)
STRUCTURE_TAGS = ["h1", "h2", "h3", "article", "section", "form", "table"]

# =============================================================================
# TOLÉRANCES DE CLUSTERING
# =============================================================================

# Balises structurelles : doivent être très similaires (±20%)
STRICT_TAGS = ["h1", "article", "section", "form", "table"]
STRICT_TOLERANCE = 0.20  # ±20%

# Balises de contenu : peuvent varier selon le contenu (±60%)
FLEXIBLE_TAGS = ["h2", "h3"]
FLEXIBLE_TOLERANCE = 0.60  # ±60%

STRUCTURE_TOLERANCE = STRICT_TOLERANCE


def extract_dom_structure(html_content: str) -> dict:
    """
    Extrait la structure DOM d'une page : comptage des balises principales.
    Returns:
        dict avec clés h1, h2, h3, article, section, form, table.
    """
    if not html_content or not html_content.strip():
        return {tag: 0 for tag in STRUCTURE_TAGS}

    soup = BeautifulSoup(html_content, "html.parser")
    structure = {}
    for tag in STRUCTURE_TAGS:
        structure[tag] = len(soup.find_all(tag))
    return structure


def extract_semantic_features(html_content: str, json_ld: list) -> dict:
    """
    Extrait les features sémantiques : paragraphes, listes, images, formulaires, boutons.
    + type(s) JSON-LD déjà présents.
    """
    features = {
        "p": 0,
        "lists": 0,
        "images": 0,
        "has_form": 0,
        "buttons": 0,
        "jsonld_types": [],
    }

    if not html_content or not html_content.strip():
        return features

    soup = BeautifulSoup(html_content, "html.parser")
    features["p"] = len(soup.find_all("p"))
    features["lists"] = len(soup.find_all(["ul", "ol"]))
    features["images"] = len(soup.find_all("img"))
    features["has_form"] = 1 if soup.find("form") else 0
    features["buttons"] = len(soup.find_all("button")) + len(
        soup.find_all("input", type=re.compile(r"submit|button", re.I))
    )

    for block in json_ld or []:
        if isinstance(block, dict):
            at_type = block.get("@type")
            if at_type:
                if isinstance(at_type, list):
                    features["jsonld_types"].extend(at_type)
                else:
                    features["jsonld_types"].append(at_type)
        elif isinstance(block, list):
            for item in block:
                if isinstance(item, dict) and item.get("@type"):
                    features["jsonld_types"].append(item["@type"])

    features["jsonld_types"] = list(set(features["jsonld_types"]))
    return features


def _segment_looks_dynamic(segment: str) -> bool:
    """True si le segment d'URL ressemble à un ID/slug (dynamique)."""
    if not segment or len(segment) > 80:
        return True
    if segment.isdigit():
        return True
    if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", segment, re.I):
        return True
    if re.match(r"^[a-z0-9-]+$", segment, re.I) and len(segment) >= 10:
        return True
    if len(segment) >= 8 and re.match(r"^[a-f0-9]+$", segment, re.I):
        return True
    return False


def get_url_path_pattern(url: str) -> list:
    """
    Découpe le path en segments et remplace les segments "dynamiques" par {slug}.
    Returns:
        Liste de segments (strings).
    """
    parsed = urlparse(url)
    path = (parsed.path or "/").strip().lower()
    path = path.rstrip("/") or "/"
    segments = [s for s in path.split("/") if s]

    pattern = []
    for seg in segments:
        if _segment_looks_dynamic(seg):
            pattern.append("{slug}")
        else:
            pattern.append(seg)
    return pattern


def url_pattern_similarity(url_a: str, url_b: str) -> float:
    """Similarité entre deux URLs basée sur le pattern de path (0 à 1)."""
    pa = get_url_path_pattern(url_a)
    pb = get_url_path_pattern(url_b)

    if not pa and not pb:
        return 1.0
    if not pa or not pb:
        return 0.0

    if len(pa) != len(pb):
        common = sum(1 for a, b in zip(pa, pb) if a == b)
        return (common / max(len(pa), len(pb))) * 0.85

    matches = sum(1 for a, b in zip(pa, pb) if a == b)
    return matches / len(pa)


def structure_similarity(struct_a: dict, struct_b: dict) -> float:
    """
    Similarité structure DOM avec tolérance VARIABLE selon le type de balise.
    Returns:
        float entre 0 et 1 (1 = structures identiques)
    """
    total = 0.0
    count = 0

    for tag in STRUCTURE_TAGS:
        ca = struct_a.get(tag, 0)
        cb = struct_b.get(tag, 0)
        count += 1

        if tag in FLEXIBLE_TAGS:
            tolerance = FLEXIBLE_TOLERANCE
        else:
            tolerance = STRICT_TOLERANCE

        if ca == 0 and cb == 0:
            total += 1.0
        elif ca == 0 or cb == 0:
            total += 0.0
        else:
            ratio = ca / cb if cb else 0

            if 1 - tolerance <= ratio <= 1 + tolerance:
                total += 1.0
            else:
                if ratio < 1:
                    deviation = (1 - ratio) / (1 - (1 - tolerance))
                    total += max(0, 1 - deviation)
                else:
                    deviation = (ratio - 1) / tolerance
                    total += max(0, 1 - deviation)

    return total / count if count else 1.0


def semantic_similarity(sem_a: dict, sem_b: dict) -> float:
    """Similarité contenu sémantique (0 à 1)."""
    total = 0.0
    for key in ["p", "lists", "images", "buttons"]:
        va = sem_a.get(key, 0)
        vb = sem_b.get(key, 0)
        if va == 0 and vb == 0:
            total += 1.0
        elif va == 0 or vb == 0:
            total += 0.0
        else:
            r = va / vb if vb else 0
            if 1 - STRUCTURE_TOLERANCE <= r <= 1 + STRUCTURE_TOLERANCE:
                total += 1.0
            else:
                total += max(0, 1 - abs(r - 1) / 2)

    if sem_a.get("has_form") == sem_b.get("has_form"):
        total += 1.0
    else:
        total += 0.5

    num_criteria = 6
    score_so_far = total / num_criteria

    types_a = set(sem_a.get("jsonld_types") or [])
    types_b = set(sem_b.get("jsonld_types") or [])
    if types_a or types_b:
        inter = len(types_a & types_b)
        union = len(types_a | types_b)
        jsonld_score = inter / union if union else 1.0
    else:
        jsonld_score = 1.0

    return (score_so_far * 5 + jsonld_score) / 6


def page_similarity(page_a: dict, page_b: dict) -> float:
    """Score de similarité combiné entre deux pages (0 à 1)."""
    url_a = page_a.get("url", "")
    url_b = page_b.get("url", "")
    html_a = page_a.get("html_content", "") or ""
    html_b = page_b.get("html_content", "") or ""
    json_ld_a = page_a.get("json_ld", []) or []
    json_ld_b = page_b.get("json_ld", []) or []

    struct_a = page_a.get("dom_structure")
    struct_b = page_b.get("dom_structure")
    if struct_a is None:
        struct_a = extract_dom_structure(html_a)
    if struct_b is None:
        struct_b = extract_dom_structure(html_b)
    s_struct = structure_similarity(struct_a, struct_b)

    s_url = url_pattern_similarity(url_a, url_b)

    sem_a = page_a.get("semantic_features")
    sem_b = page_b.get("semantic_features")
    if sem_a is None:
        sem_a = extract_semantic_features(html_a, json_ld_a)
    if sem_b is None:
        sem_b = extract_semantic_features(html_b, json_ld_b)
    s_sem = semantic_similarity(sem_a, sem_b)

    return WEIGHT_STRUCTURE * s_struct + WEIGHT_URL * s_url + WEIGHT_SEMANTIC * s_sem


def enrich_pages_for_clustering(results: list) -> list:
    """Enrichit chaque résultat de crawl avec dom_structure et semantic_features."""
    enriched = []
    for r in results:
        row = dict(r)
        row["dom_structure"] = extract_dom_structure(row.get("html_content") or "")
        row["semantic_features"] = extract_semantic_features(
            row.get("html_content") or "",
            row.get("json_ld") or [],
        )
        enriched.append(row)
    return enriched


def cluster_pages(results: list, threshold: float = None) -> list:
    """
    Regroupe les pages par similarité DOM/URL/sémantique.
    Returns:
        Liste de clusters : chaque cluster est une liste d'indices dans results.
    """
    if threshold is None:
        threshold = CLUSTER_SIMILARITY_THRESHOLD

    if not results:
        return []

    pages = enrich_pages_for_clustering(results)
    n = len(pages)

    parent = list(range(n))

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            sim = page_similarity(pages[i], pages[j])
            if sim >= threshold:
                union(i, j)

    clusters_by_root = defaultdict(list)
    for i in range(n):
        clusters_by_root[find(i)].append(i)

    clusters = list(clusters_by_root.values())
    clusters.sort(key=len, reverse=True)
    return clusters


def get_cluster_url_pattern(urls: list) -> str:
    """Dérive un pattern URL lisible à partir d'une liste d'URLs du cluster."""
    if not urls:
        return ""
    patterns = [get_url_path_pattern(u) for u in urls]
    base = max(patterns, key=len)
    return "/" + "/".join(base)


# =============================================================================
# Mistral AI
# =============================================================================

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-small-latest"
MISTRAL_TIMEOUT = 25
MISTRAL_RETRY = 2


def _parse_mistral_json(content: str):
    """Extrait un objet JSON de la réponse Mistral."""
    content = (content or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{[\s\S]*\}", content)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


def name_cluster_with_mistral(api_key: str, results: list, cluster_indices: list, timeout: Optional[int] = None) -> Optional[dict]:
    """
    Demande à Mistral un nom de modèle et un type Schema.org pour un cluster.
    Returns:
        {"model_name": "...", "schema_type": "..."} ou None en cas d'erreur.
    """
    if timeout is None:
        timeout = MISTRAL_TIMEOUT
    samples = []
    for idx in cluster_indices[:5]:
        if idx >= len(results):
            continue
        r = results[idx]
        url = r.get("url", "")
        h1 = (r.get("h1") or "").strip()[:200]
        desc = (r.get("description") or "").strip()[:300]
        samples.append(f"- URL : {url} | H1 : {h1} | Meta : {desc}")

    if not samples:
        return None

    user_prompt = """Analyse ces URLs d'un même groupe :

"""
    user_prompt += "\n".join(samples)
    user_prompt += """

Génère :
1. Nom du modèle (2-4 mots, français, professionnel). Exemples : "Offres d'emploi", "Fiches produits", "Articles blog".
2. Type Schema.org recommandé (un seul). Exemples : JobPosting, Product, Article, Event, Organization, LocalBusiness.

Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après :
{"model_name": "...", "schema_type": "..."}
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": MISTRAL_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Tu es un expert en données structurées (Schema.org) et en architecture d'information. Tu réponds uniquement en JSON valide.",
            },
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }

    last_error = None
    for attempt in range(MISTRAL_RETRY + 1):
        try:
            response = requests.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            raw = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            parsed = _parse_mistral_json(raw)
            if not parsed or not isinstance(parsed, dict):
                return None
            model_name = (parsed.get("model_name") or "").strip() or "Modèle sans nom"
            schema_type = (parsed.get("schema_type") or "").strip() or "WebPage"
            return {"model_name": model_name, "schema_type": schema_type}
        except requests.exceptions.Timeout:
            last_error = "timeout"
            if attempt < MISTRAL_RETRY:
                time.sleep(1)
        except requests.exceptions.RequestException as e:
            last_error = str(e)[:100] if e else "erreur réseau"
            break
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
    return None


def generate_optimized_jsonld(
    api_key: str,
    schema_type: str,
    dom_structure: dict,
    sample_pages: list,
    existing_jsonld: Optional[dict],
    url_pattern: str,
    timeout: int = 30,
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Génère un JSON-LD Schema.org optimisé complet via Mistral AI.
    Returns:
        tuple (dict|None, str|None) : (JSON-LD optimisé, ou None) et (message d'erreur, ou None)
    """
    system_prompt = f"""Tu es un expert mondial en données structurées Schema.org et en SEO technique.

Ta mission : générer un JSON-LD Schema.org PARFAIT et COMPLET pour un type de page web.

**Règles absolues :**
1. Respecte à 100% la spécification Schema.org pour le type `{schema_type}`
2. Remplis TOUS les champs obligatoires (required) du type
3. Remplis TOUS les champs recommandés (recommended) du type
4. Ajoute les champs optionnels pertinents qui enrichissent la sémantique
5. Utilise des valeurs réalistes et cohérentes basées sur les exemples fournis
6. Structure le JSON-LD pour être OPTIMAL pour les LLMs (ChatGPT, Claude, Gemini, Perplexity)
7. Inclus TOUJOURS @context et @type
8. Pour les entités liées (Organization, Person, Place), crée des objets complets avec @id
9. Pour les dates : format ISO 8601 (YYYY-MM-DD ou YYYY-MM-DDTHH:mm:ssZ)
10. Pour les URLs : URLs complètes et valides
11. Pour les prix : objets PriceSpecification avec currency="EUR"
12. Pour les images : objets ImageObject avec url, width, height

**Types de champs à maximiser selon le type :**

JobPosting : title, description, datePosted, validThrough, employmentType, hiringOrganization (complet), jobLocation (complet), baseSalary, responsibilities, skills, qualifications, benefits, jobBenefits, workHours, educationRequirements, experienceRequirements, industry

Product : name, description, brand, offers (avec price, priceCurrency, availability, seller), image, aggregateRating, review, sku, gtin, mpn, category, color, material, size

Article : headline, description, author (Person complet), publisher (Organization complet), datePublished, dateModified, image, articleBody, articleSection, wordCount, keywords

Event : name, description, startDate, endDate, location (Place complet), organizer, performer, offers, image, eventStatus, eventAttendanceMode

LocalBusiness : name, description, address (PostalAddress complet), geo, telephone, openingHours, priceRange, aggregateRating, image, url, sameAs

Organization : name, legalName, description, url, logo, address, contactPoint, sameAs, founder, foundingDate, numberOfEmployees, brand, slogan

**Réponds UNIQUEMENT avec le JSON-LD valide, sans texte avant ou après, sans balises markdown.**
"""

    user_prompt = f"""Génère un JSON-LD Schema.org de type `{schema_type}` pour les pages suivantes.

**Type détecté :** {schema_type}
**Pattern d'URL :** {url_pattern}

**Structure DOM type :**
{json.dumps(dom_structure, indent=2, ensure_ascii=False)}

**Exemples de pages (contenu réel) :**
"""
    for i, page in enumerate(sample_pages, 1):
        user_prompt += f"""
--- Page {i} ---
URL : {page.get('url', '')}
Titre : {page.get('title', '')}
H1 : {page.get('h1', '')}
Meta description : {page.get('description', '')}
Extrait HTML (5000 premiers chars) :
{(page.get('html_snippet', '') or '')[:5000]}

"""
    if existing_jsonld:
        user_prompt += f"""
**JSON-LD actuel détecté sur ces pages :**
{json.dumps(existing_jsonld, indent=2, ensure_ascii=False)[:3000]}

⚠️ ATTENTION : Le JSON-LD actuel est incomplet. Ton objectif est de le COMPLÉTER et l'OPTIMISER en ajoutant TOUS les champs manquants recommandés par Schema.org pour le type `{schema_type}`.
"""
    else:
        user_prompt += f"""
**JSON-LD actuel :** Aucun JSON-LD détecté sur ces pages.

⚠️ Tu dois créer un JSON-LD COMPLET from scratch.
"""
    user_prompt += f"""

**Instructions finales :**
1. Analyse le contenu réel des pages exemples ci-dessus
2. Génère un JSON-LD `{schema_type}` COMPLET avec TOUS les champs obligatoires + recommandés + optionnels pertinents
3. Utilise les vraies données extraites des exemples (titres, descriptions, etc.)
4. Pour les champs manquants dans les exemples, utilise des placeholders réalistes entre {{{{double_accolades}}}} (ex: {{{{job_title}}}}, {{{{price}}}}, {{{{author_name}}}})
5. Respecte à 100% la spec Schema.org
6. Optimise pour la citation par les LLMs (ChatGPT, Claude, Gemini)

Réponds UNIQUEMENT avec le JSON-LD valide, sans aucun texte, sans balises markdown, sans commentaires.
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": "mistral-large-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
    }

    try:
        response = requests.post(
            MISTRAL_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        if response.status_code >= 400:
            try:
                err_body = response.json()
                err_detail = err_body.get("message") or err_body.get("error") or str(err_body)[:300]
            except Exception:
                err_detail = response.text[:300] if response.text else str(response.status_code)
            err = f"Mistral API erreur {response.status_code} pour {schema_type}: {err_detail}"
            logging.error(err)
            return None, err
        response.raise_for_status()
        data = response.json()
        raw_content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")

        if not raw_content or not str(raw_content).strip():
            err = f"Réponse Mistral vide pour {schema_type}. L'API a renvoyé une structure sans contenu (choices/message/content)."
            logging.error(err)
            return None, err

        parsed = _parse_mistral_json(raw_content)
        if not parsed or not isinstance(parsed, dict):
            try:
                parsed = json.loads(raw_content.strip())
            except json.JSONDecodeError:
                err = f"Parse JSON impossible (Mistral a renvoyé du texte invalide pour {schema_type}). Réponse brute (200 premiers chars): {repr((raw_content or '')[:200])}"
                logging.error(f"Mistral JSON-LD parse failed for {schema_type}: {raw_content[:300]}")
                return None, err

        if "@context" not in parsed or "@type" not in parsed:
            err = f"Réponse Mistral invalide: manque @context ou @type pour {schema_type}. Structure reçue: {list(parsed.keys())[:10] if isinstance(parsed, dict) else type(parsed).__name__}"
            logging.error(f"Mistral JSON-LD invalid (@context/@type) for {schema_type}")
            return None, err

        return parsed, None

    except requests.exceptions.Timeout:
        err = f"Timeout Mistral ({timeout}s) pour {schema_type}. L'API est peut-être surchargée."
        logging.error(f"Timeout Mistral pour {schema_type}")
        return None, err
    except requests.exceptions.RequestException as e:
        err = f"Erreur API Mistral pour {schema_type}: {str(e)[:300]}"
        logging.error(f"Erreur API Mistral : {str(e)[:200]}")
        return None, err
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        err = f"Erreur inattendue lors du parsing: {type(e).__name__}: {str(e)[:200]}"
        logging.exception(f"Mistral JSON-LD exception for {schema_type}")
        return None, err


# =============================================================================
# Graphe interactif (pyvis + networkx)
# =============================================================================

CLUSTER_NODE_COLORS = [
    "#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#2563eb",
    "#7c3aed", "#db2777", "#0d9488", "#f59e0b", "#6366f1",
    "#ef4444", "#84cc16", "#06b6d4", "#8b5cf6", "#ec4899",
]


def build_jsonld_graph_html(domain: str, cluster_labels: list, cluster_urls: list) -> str:
    """Construit le graphe pyvis : domaine -> clusters -> URLs exemples. Nœuds colorés."""
    import networkx as nx
    from pyvis.network import Network

    G = nx.DiGraph()
    domain_node = f"domain_{domain}"
    G.add_node(
        domain_node,
        label=domain[:30] + ("..." if len(domain) > 30 else ""),
        size=35,
        color="#0f172a",
        font={"color": "#ffffff", "face": "Inter"},
        title=domain,
    )

    for i in range(len(cluster_labels)):
        label = cluster_labels[i] if i < len(cluster_labels) else {}
        name = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
        urls = cluster_urls[i] if i < len(cluster_urls) else []
        cluster_id = f"cluster_{i}"
        cluster_size = 15 + min(len(urls), 25)
        cluster_color = CLUSTER_NODE_COLORS[i % len(CLUSTER_NODE_COLORS)]
        G.add_node(
            cluster_id,
            label=name[:25] + ("..." if len(name) > 25 else ""),
            size=cluster_size,
            color=cluster_color,
            font={"color": "#ffffff", "face": "Inter"},
            title=f"{name} — {len(urls)} page(s)",
        )
        G.add_edge(domain_node, cluster_id)

        for u in urls[:5]:
            short_label = (urlparse(u).path or "/")[-40:] or "URL"
            G.add_node(
                u,
                label=short_label,
                size=10,
                color="#e2e8f0",
                font={"color": "#0f172a", "face": "Inter", "size": 10},
                title=u,
            )
            G.add_edge(cluster_id, u)

    nt = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="#0f172a")
    nt.from_nx(G)
    opts = {
        "nodes": {"font": {"face": "Inter", "size": 12}, "borderWidth": 2},
        "edges": {"color": "#cbd5e1", "smooth": {"type": "dynamic", "roundness": 0.2}},
        "physics": {
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {"gravitationalConstant": -80, "springLength": 150, "avoidOverlap": 1},
            "stabilization": {"enabled": True, "iterations": 150},
        },
    }
    nt.set_options(json.dumps(opts))
    path = "temp_jsonld_graph.html"
    nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    try:
        os.remove(path)
    except OSError:
        pass

    click_handler = """
    <script>
        (function() {
            function tryNavigate(clusterIndex) {
                try {
                    var target = window.top || window.parent || window;
                    var href = target.location.href;
                    var url = new URL(href);
                    url.searchParams.set('jsonld_cluster', clusterIndex);
                    target.location.href = url.toString();
                    return true;
                } catch (e) {
                    try {
                        var ref = document.referrer;
                        if (!ref) return false;
                        var url = new URL(ref);
                        url.searchParams.set('jsonld_cluster', clusterIndex);
                        var a = document.createElement('a');
                        a.href = url.toString();
                        a.target = '_top';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        return true;
                    } catch (e2) { return false; }
                }
            }
            function attachClickHandler() {
                if (typeof network !== 'undefined') {
                    network.on("click", function(params) {
                        if (params.nodes.length > 0) {
                            var nodeId = params.nodes[0];
                            if (String(nodeId).startsWith('cluster_')) {
                                var clusterIndex = parseInt(String(nodeId).replace('cluster_', ''), 10);
                                tryNavigate(clusterIndex);
                            } else if (String(nodeId).startsWith('http')) {
                                window.open(nodeId, '_blank');
                            }
                        }
                    });
                    return true;
                }
                return false;
            }
            function init() {
                if (!attachClickHandler()) {
                    setTimeout(init, 200);
                }
            }
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() { setTimeout(init, 400); });
            } else {
                setTimeout(init, 400);
            }
        })();
    </script>
    """
    html = html.replace("</body>", click_handler + "</body>")
    return html
