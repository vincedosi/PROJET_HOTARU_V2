# =============================================================================
# JSON-LD Analyzer - Phase 1 : Clustering DOM
# Analyse de sites pour regrouper les pages par structure similaire.
# Compatible avec les résultats SmartScraper (sans modifier core/scraping.py).
# =============================================================================

import re
import json
import requests
from typing import Optional
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


# =============================================================================
# Étape 3 : Nommage intelligent (Mistral AI)
# =============================================================================

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-small-latest"
MISTRAL_TIMEOUT = 25


def _parse_mistral_json(content: str):
    """Extrait un objet JSON de la réponse Mistral (texte ou bloc markdown)."""
    content = (content or "").strip()
    # Bloc ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Objet {...} brut
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
    Utilise 3 à 5 URLs exemples avec H1 et meta description.

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
        return None
    except requests.exceptions.RequestException:
        return None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


# =============================================================================
# Étape 2 : Interface Streamlit basique (input + résultats texte)
# =============================================================================

def render_jsonld_analyzer_tab():
    """Onglet Analyse JSON-LD : crawl + clustering, affichage résultats texte."""
    import streamlit as st
    from core.scraping import SmartScraper

    st.markdown(
        "<p class='section-title'>ANALYSE JSON-LD</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='home-tagline' style='margin-bottom:1.5rem;'>"
        "Détection des types de pages par structure DOM et pattern d'URL. Clustering intelligent (seuil 85 %).</p>",
        unsafe_allow_html=True,
    )

    url_input = st.text_input(
        "URL du site à analyser",
        placeholder="https://www.example.com",
        key="jsonld_analyzer_url",
    )
    max_pages = st.slider(
        "Nombre de pages à crawler",
        min_value=50,
        max_value=500,
        value=150,
        step=10,
        key="jsonld_analyzer_max_pages",
    )

    if st.button("LANCER L'ANALYSE", type="primary", use_container_width=True, key="jsonld_analyzer_btn"):
        if not url_input or not url_input.strip():
            st.warning("Veuillez saisir une URL.")
            return

        url = url_input.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        logs = []
        def add_log(msg):
            logs.append(msg)

        progress_placeholder = st.empty()
        log_placeholder = st.container()

        with progress_placeholder:
            bar = st.progress(0.0, "Initialisation...")

        try:
            scr = SmartScraper(
                [url],
                max_urls=max_pages,
                use_selenium=False,
                log_callback=add_log,
            )
            res, crawl_meta = scr.run_analysis(
                progress_callback=lambda msg, val: bar.progress(min(val, 1.0), msg),
            )
        except Exception as e:
            progress_placeholder.empty()
            st.error(f"Erreur lors du crawl : {e}")
            return

        progress_placeholder.empty()

        if not res:
            st.warning("Aucune page récupérée. Vérifiez l'URL et réessayez.")
            if logs:
                with st.expander("Logs de crawl"):
                    st.text("\n".join(logs[-100:]))
            return

        # Clustering
        with st.spinner("Clustering des pages..."):
            clusters = cluster_pages(res)

        # Nommage Mistral (étape 3)
        cluster_labels = []
        try:
            mistral_key = st.secrets["mistral"]["api_key"]
        except Exception:
            mistral_key = None

        if mistral_key:
            for i, cluster_indices in enumerate(clusters):
                with st.spinner(f"Nommage Mistral — cluster {i + 1}/{len(clusters)}..."):
                    out = name_cluster_with_mistral(mistral_key, res, cluster_indices)
                if out:
                    cluster_labels.append(out)
                else:
                    cluster_labels.append({"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"})
        else:
            cluster_labels = [
                {"model_name": f"Cluster {i + 1}", "schema_type": "—"}
                for i in range(len(clusters))
            ]
            st.info("Clé API Mistral absente : nommage automatique désactivé. Configurez `st.secrets['mistral']['api_key']` pour activer.")

        domain = urlparse(url).netloc or "site"
        # Sauvegarde en session (sans HTML) pour affichage persistant après rerun
        cluster_urls = [[res[idx]["url"] for idx in indices] for indices in clusters]
        st.session_state["jsonld_analyzer_results"] = {
            "domain": domain,
            "total_pages": len(res),
            "cluster_labels": cluster_labels,
            "cluster_urls": cluster_urls,
            "logs": logs,
        }
        st.rerun()

    # Affichage des résultats (depuis session_state, persistant après rerun)
    if "jsonld_analyzer_results" in st.session_state:
        data = st.session_state["jsonld_analyzer_results"]
        domain = data["domain"]
        total_pages = data["total_pages"]
        cluster_labels = data["cluster_labels"]
        cluster_urls = data["cluster_urls"]
        logs = data.get("logs", [])
        num_clusters = len(cluster_labels)

        st.markdown("---")
        st.markdown("##### Vue d'ensemble")
        st.markdown(f"- **Site :** {domain}")
        st.markdown(f"- **Pages analysées :** {total_pages}")
        st.markdown(f"- **Modèles détectés :** {num_clusters}")

        st.markdown("---")
        st.markdown("##### Détail des clusters")

        for i in range(num_clusters):
            label = cluster_labels[i] if i < len(cluster_labels) else {"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"}
            urls_in_cluster = cluster_urls[i] if i < len(cluster_urls) else []
            pattern = get_cluster_url_pattern(urls_in_cluster)
            sample = urls_in_cluster[:5]
            # Libellés toujours non vides (texte simple pour le titre d'expander)
            name = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
            schema_type = (label.get("schema_type") or "").strip() or "—"
            expander_label = f"{name} — {schema_type} — {len(urls_in_cluster)} page(s) — {pattern}"

            with st.expander(expander_label, expanded=False, key=f"jsonld_cluster_exp_{i}"):
                st.markdown(f"**Type Schema.org recommandé :** `{schema_type}`")
                st.markdown("**Exemples d'URLs :**")
                for u in sample:
                    st.code(u, language=None)
                if len(urls_in_cluster) > 5:
                    st.caption(f"... et {len(urls_in_cluster) - 5} autre(s) page(s).")

        if logs:
            with st.expander("Logs de crawl", key="jsonld_analyzer_logs"):
                st.text("\n".join(logs[-150:]))
