# =============================================================================
# JSON-LD Analyzer - Phase 1 : Clustering DOM
# Analyse de sites pour regrouper les pages par structure similaire.
# Compatible avec les résultats SmartScraper (sans modifier core/scraping.py).
# =============================================================================

import re
import json
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

# Tolérance pour la comparaison des comptes (±20%)
STRUCTURE_TOLERANCE = 0.20


def extract_dom_structure(html_content: str) -> dict:
    """
    Extrait la structure DOM d'une page : comptage des balises principales.
    Utilisé pour le critère "Structure HTML" (40 points).

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
    Utilisé pour le critère "Contenu sémantique" (30 points).

    Args:
        html_content: HTML brut de la page
        json_ld: liste des blocs JSON-LD déjà extraits (par SmartScraper)

    Returns:
        dict avec p, lists, images, has_form, buttons, jsonld_types (list)
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
    # Numérique
    if segment.isdigit():
        return True
    # UUID-like
    if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", segment, re.I):
        return True
    # Slug typique (lettres-chiffres-tirets)
    if re.match(r"^[a-z0-9-]+$", segment, re.I) and len(segment) >= 10:
        return True
    # Hash court
    if len(segment) >= 8 and re.match(r"^[a-f0-9]+$", segment, re.I):
        return True
    return False


def get_url_path_pattern(url: str) -> list:
    """
    Découpe le path en segments et remplace les segments "dynamiques" par {slug}.
    Ex: /blog/123/post-name → ["blog", "{slug}", "{slug}"]
    /produits/abc-123 → ["produits", "{slug}"]

    Returns:
        Liste de segments (strings), segments dynamiques normalisés en "{slug}".
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
    """
    Similarité entre deux URLs basée sur le pattern de path (30 points max).
    Retourne une valeur entre 0 et 1.
    """
    pa = get_url_path_pattern(url_a)
    pb = get_url_path_pattern(url_b)

    if not pa and not pb:
        return 1.0
    if not pa or not pb:
        return 0.0

    # Même longueur et mêmes segments (ou placeholders au même endroit)
    if len(pa) != len(pb):
        # Pénalité si longueurs différentes
        common = sum(1 for a, b in zip(pa, pb) if a == b)
        return (common / max(len(pa), len(pb))) * 0.85  # cap à 0.85 si diff de longueur

    matches = sum(1 for a, b in zip(pa, pb) if a == b)
    return matches / len(pa)


def structure_similarity(struct_a: dict, struct_b: dict) -> float:
    """
    Similarité structure DOM avec tolérance ±20% par balise (40 points max).
    Chaque balise contribue proportionnellement ; si count_a dans [count_b*(1-tol), count_b*(1+tol)], score 1 pour cette balise.
    """
    total = 0.0
    count = 0
    for tag in STRUCTURE_TAGS:
        ca = struct_a.get(tag, 0)
        cb = struct_b.get(tag, 0)
        count += 1
        if ca == 0 and cb == 0:
            total += 1.0
        elif ca == 0 or cb == 0:
            # Un seul à 0 → pas de similarité pour cette balise
            total += 0.0
        else:
            ratio = ca / cb if cb else 0
            if 1 - STRUCTURE_TOLERANCE <= ratio <= 1 + STRUCTURE_TOLERANCE:
                total += 1.0
            else:
                # Dégradation linéaire en dehors de la tolérance
                if ratio < 1:
                    total += max(0, 1 - (1 - ratio) / (1 - (1 - STRUCTURE_TOLERANCE)))
                else:
                    total += max(0, 1 - (ratio - 1) / STRUCTURE_TOLERANCE)
    return total / count if count else 1.0


def semantic_similarity(sem_a: dict, sem_b: dict) -> float:
    """
    Similarité contenu sémantique (30 points max).
    Compare p, lists, images, has_form, buttons avec tolérance ±20%.
    Bonus si les types JSON-LD ont une intersection.
    """
    total = 0.0
    # Comptes numériques avec tolérance
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
                total += max(0, 1 - abs(r - 1) / 2)  # dégradation
    # has_form : binaire
    if sem_a.get("has_form") == sem_b.get("has_form"):
        total += 1.0
    else:
        total += 0.5  # pas totalement différent
    # Normaliser sur 6 critères (p, lists, images, buttons, has_form + jsonld)
    num_criteria = 6
    score_so_far = total / num_criteria

    # JSON-LD types : intersection / union
    types_a = set(sem_a.get("jsonld_types") or [])
    types_b = set(sem_b.get("jsonld_types") or [])
    if types_a or types_b:
        inter = len(types_a & types_b)
        union = len(types_a | types_b)
        jsonld_score = inter / union if union else 1.0
    else:
        jsonld_score = 1.0  # aucun des deux n'a de JSON-LD → même profil

    # Moyenne pondérée : 5 critères structurels + 1 jsonld
    return (score_so_far * 5 + jsonld_score) / 6


def page_similarity(page_a: dict, page_b: dict) -> float:
    """
    Score de similarité combiné entre deux pages (0 à 1).
    - Structure HTML : 40%
    - URL Pattern : 30%
    - Contenu sémantique : 30%

    Les pages doivent contenir au minimum url et html_content.
    Si html_content manque, on utilise les champs déjà présents (h2_count, lists_count, json_ld).
    """
    url_a = page_a.get("url", "")
    url_b = page_b.get("url", "")
    html_a = page_a.get("html_content", "") or ""
    html_b = page_b.get("html_content", "") or ""
    json_ld_a = page_a.get("json_ld", []) or []
    json_ld_b = page_b.get("json_ld", []) or []

    # Structure
    struct_a = page_a.get("dom_structure")
    struct_b = page_b.get("dom_structure")
    if struct_a is None:
        struct_a = extract_dom_structure(html_a)
    if struct_b is None:
        struct_b = extract_dom_structure(html_b)
    s_struct = structure_similarity(struct_a, struct_b)

    # URL
    s_url = url_pattern_similarity(url_a, url_b)

    # Sémantique
    sem_a = page_a.get("semantic_features")
    sem_b = page_b.get("semantic_features")
    if sem_a is None:
        sem_a = extract_semantic_features(html_a, json_ld_a)
    if sem_b is None:
        sem_b = extract_semantic_features(html_b, json_ld_b)
    s_sem = semantic_similarity(sem_a, sem_b)

    return WEIGHT_STRUCTURE * s_struct + WEIGHT_URL * s_url + WEIGHT_SEMANTIC * s_sem


def enrich_pages_for_clustering(results: list) -> list:
    """
    Enrichit chaque résultat de crawl avec dom_structure et semantic_features
    pour éviter de recalculer lors du clustering.
    """
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
    Deux pages sont dans le même cluster si leur similarité >= threshold (défaut 0.85).

    Algorithme : composantes connexes. On construit un graphe où une arête existe
    entre deux pages si similarity >= threshold ; chaque composante connexe = 1 cluster.

    Args:
        results: liste de dicts (format SmartScraper : url, html_content, json_ld, ...)
        threshold: seuil de similarité (défaut CLUSTER_SIMILARITY_THRESHOLD)

    Returns:
        Liste de clusters : chaque cluster est une liste d'indices dans results.
        Les clusters sont triés par taille décroissante.
    """
    if threshold is None:
        threshold = CLUSTER_SIMILARITY_THRESHOLD

    if not results:
        return []

    # Enrichir une fois
    pages = enrich_pages_for_clustering(results)
    n = len(pages)

    # Union-Find pour composantes connexes
    parent = list(range(n))

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Matrice de similarité (on ne calcule que le strict nécessaire)
    for i in range(n):
        for j in range(i + 1, n):
            sim = page_similarity(pages[i], pages[j])
            if sim >= threshold:
                union(i, j)

    # Grouper par racine
    clusters_by_root = defaultdict(list)
    for i in range(n):
        clusters_by_root[find(i)].append(i)

    clusters = list(clusters_by_root.values())
    # Trier par taille décroissante
    clusters.sort(key=len, reverse=True)
    return clusters


def get_cluster_url_pattern(urls: list) -> str:
    """
    Dérive un pattern URL lisible à partir d'une liste d'URLs du cluster.
    Ex: ["/blog/a", "/blog/b"] → "/blog/{slug}"
    """
    if not urls:
        return ""
    patterns = [get_url_path_pattern(u) for u in urls]
    # Prendre le plus long ou le plus fréquent comme base
    base = max(patterns, key=len)
    return "/" + "/".join(base)
