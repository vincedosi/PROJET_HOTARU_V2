# =============================================================================
# JSON-LD Analyzer - Phase 1 : Clustering DOM
# Analyse de sites pour regrouper les pages par structure similaire.
# Compatible avec les résultats SmartScraper (sans modifier core/scraping.py).
# =============================================================================

import re
import json
import os
import time
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
MISTRAL_RETRY = 2


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
        except requests.exceptions.Timeout as e:
            last_error = "timeout"
            if attempt < MISTRAL_RETRY:
                time.sleep(1)
        except requests.exceptions.RequestException as e:
            last_error = str(e)[:100] if e else "erreur réseau"
            break
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
    return None


# =============================================================================
# Étape 4 : Graphe interactif (pyvis + networkx)
# =============================================================================

# Palette de couleurs pour les nœuds cluster (chaque cluster = couleur distincte)
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

    # Event listener pour clics : cluster → URL param pour panneau ; URL → nouvel onglet
    click_handler = """
    <script>
        (function() {
            function attachClickHandler() {
                if (typeof network !== 'undefined') {
                    network.on("click", function(params) {
                        if (params.nodes.length > 0) {
                            var nodeId = params.nodes[0];
                            if (String(nodeId).startsWith('cluster_')) {
                                var clusterIndex = parseInt(String(nodeId).replace('cluster_', ''), 10);
                                try {
                                    var url = new URL(window.parent.location.href);
                                    url.searchParams.set('jsonld_cluster', clusterIndex);
                                    window.parent.location.href = url.toString();
                                } catch (e) { console.log('Update URL:', e); }
                            } else if (String(nodeId).startsWith('http')) {
                                window.open(nodeId, '_blank');
                            }
                        }
                    });
                }
            }
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() { setTimeout(attachClickHandler, 300); });
            } else {
                setTimeout(attachClickHandler, 300);
            }
        })();
    </script>
    """
    html = html.replace("</body>", click_handler + "</body>")
    return html


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

    with st.expander("Charger des données sauvegardées depuis Google Sheets"):
        from core.database import AuditDatabase
        from core.session_keys import get_current_user_email

        user_email = get_current_user_email() or ""
        db = AuditDatabase()
        sites = db.list_jsonld_sites(user_email) if user_email and db.client else []

        if not sites:
            st.caption("Aucune donnée sauvegardée pour votre compte. Lancez une analyse puis sauvegardez dans Google Sheets.")
        else:
            opt_labels = [f"{s['site_url']} — {s['workspace']}" for s in sites]
            sel_idx = st.selectbox("Sélectionner un site sauvegardé", range(len(opt_labels)), format_func=lambda i: opt_labels[i], key="jsonld_load_site")
            if st.button("CHARGER DEPUIS GOOGLE SHEETS", type="secondary", use_container_width=True, key="jsonld_load_btn"):
                s = sites[sel_idx]
                models = db.load_jsonld_models(user_email, site_url=s["site_url"])
                models = [m for m in models if (m.get("workspace") or "").strip() == (s.get("workspace") or "").strip()]
                if not models:
                    st.warning("Aucun modèle trouvé pour ce site et espace de travail.")
                else:
                    domain = urlparse(s["site_url"]).netloc or "site"
                    cluster_labels = []
                    cluster_urls = []
                    cluster_dom = []
                    cluster_jsonld = []
                    total_pages = 0
                    for m in models:
                        cluster_labels.append({"model_name": m.get("model_name") or "Cluster", "schema_type": m.get("recommended_schema") or "WebPage"})
                        urls_str = m.get("sample_urls") or "[]"
                        try:
                            urls = json.loads(urls_str) if isinstance(urls_str, str) else urls_str
                        except json.JSONDecodeError:
                            try:
                                raw = __import__("base64").b64decode(urls_str)
                                urls = json.loads(__import__("zlib").decompress(raw).decode())
                            except Exception:
                                urls = []
                        cluster_urls.append(urls if isinstance(urls, list) else [])
                        cluster_dom.append(db._decompress_from_sheet(m.get("dom_structure") or "") or {})
                        cluster_jsonld.append(db._decompress_from_sheet(m.get("existing_jsonld") or ""))
                        total_pages += m.get("page_count", 0)
                    st.session_state["jsonld_analyzer_results"] = {
                        "site_url": s["site_url"],
                        "domain": domain,
                        "total_pages": total_pages,
                        "cluster_labels": cluster_labels,
                        "cluster_urls": cluster_urls,
                        "cluster_dom_structures": cluster_dom,
                        "cluster_jsonld": cluster_jsonld,
                        "logs": [],
                        "loaded_from_sheet": True,
                    }
                    st.success("Données chargées.")
                    st.rerun()

    url_input = st.text_input(
        "URL du site à analyser",
        placeholder="https://www.example.com",
        key="jsonld_analyzer_url",
        help="URL de la page d'accueil ou d'un point d'entrée du site.",
    )
    max_pages = st.slider(
        "Nombre de pages à crawler",
        min_value=50,
        max_value=500,
        value=150,
        step=10,
        key="jsonld_analyzer_max_pages",
        help="Temps estimé : ~1-2 s/page (mode requests). Clustering < 30 s pour 500 pages.",
    )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        launch = st.button("LANCER L'ANALYSE", type="primary", use_container_width=True, key="jsonld_analyzer_btn")
    with col_btn2:
        if "jsonld_analyzer_results" in st.session_state and st.button("EFFACER LES RÉSULTATS", use_container_width=True, key="jsonld_clear_btn"):
            del st.session_state["jsonld_analyzer_results"]
            st.rerun()

    if launch:
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
            err_msg = str(e)[:300] if e else "Erreur inconnue"
            st.error(f"Erreur lors du crawl : {err_msg}")
            st.caption("Vérifiez l'URL, la connexion réseau et que le site est accessible.")
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
            mistral_fail_count = 0
            for i, cluster_indices in enumerate(clusters):
                with st.spinner(f"Nommage Mistral — cluster {i + 1}/{len(clusters)}..."):
                    out = name_cluster_with_mistral(mistral_key, res, cluster_indices)
                if out:
                    cluster_labels.append(out)
                else:
                    cluster_labels.append({"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"})
                    mistral_fail_count += 1
            if mistral_fail_count > 0:
                st.warning(f"Nommage Mistral : {mistral_fail_count} cluster(s) sans nom (timeout ou API occupée). Réessayez.")
        else:
            cluster_labels = [
                {"model_name": f"Cluster {i + 1}", "schema_type": "—"}
                for i in range(len(clusters))
            ]
            st.info("Clé API Mistral absente : nommage automatique désactivé. Configurez `st.secrets['mistral']['api_key']` pour activer.")

        domain = urlparse(url).netloc or "site"
        site_url = url
        cluster_urls = [[res[idx]["url"] for idx in indices] for indices in clusters]
        # DOM + JSON-LD par cluster (première page) pour le graphe et le panneau
        cluster_dom_structures = []
        cluster_jsonld = []
        for indices in clusters:
            page = res[indices[0]]
            dom = page.get("dom_structure") or extract_dom_structure(page.get("html_content") or "")
            cluster_dom_structures.append(dom)
            jld = page.get("json_ld") or []
            cluster_jsonld.append(jld[0] if jld else None)
        st.session_state["jsonld_analyzer_results"] = {
            "site_url": site_url,
            "domain": domain,
            "total_pages": len(res),
            "cluster_labels": cluster_labels,
            "cluster_urls": cluster_urls,
            "cluster_dom_structures": cluster_dom_structures,
            "cluster_jsonld": cluster_jsonld,
            "logs": logs,
        }
        st.rerun()

    # Affichage des résultats (depuis session_state, persistant après rerun)
    if "jsonld_analyzer_results" in st.session_state:
        import streamlit.components.v1 as components

        data = st.session_state["jsonld_analyzer_results"]
        domain = data["domain"]
        total_pages = data["total_pages"]
        cluster_labels = data["cluster_labels"]
        cluster_urls = data["cluster_urls"]
        cluster_dom = data.get("cluster_dom_structures", [])
        cluster_jsonld = data.get("cluster_jsonld", [])
        logs = data.get("logs", [])
        num_clusters = len(cluster_labels)

        st.markdown("---")
        st.markdown("##### Vue d'ensemble")
        st.markdown(f"- **Site :** {domain}")
        st.markdown(f"- **Pages analysées :** {total_pages}")
        st.markdown(f"- **Modèles détectés :** {num_clusters}")
        if num_clusters == 0:
            st.warning("Aucun cluster détecté. Le site pourrait avoir une structure très homogène.")
        elif num_clusters > 25:
            st.caption("Conseil : un grand nombre de clusters peut indiquer une structure de site très variée ou un seuil de similarité à ajuster.")

        st.markdown("---")
        if num_clusters == 0:
            st.info("Lancez une nouvelle analyse avec une URL différente ou un nombre de pages plus élevé.")
        else:
            tab_graphe, tab_tableau, tab_export = st.tabs(["GRAPHE", "TABLEAU", "EXPORT"])

        if num_clusters > 0:
            with tab_graphe:
                st.markdown("##### Graphe interactif des clusters")
                st.caption("Cliquez sur un cluster (nœud coloré) pour afficher les détails. Cliquez sur une URL pour l'ouvrir dans un nouvel onglet.")

                html_graph = build_jsonld_graph_html(domain, cluster_labels, cluster_urls)
                components.html(html_graph, height=620)

                st.markdown("---")
                st.markdown("##### Détails du cluster")

                # Déterminer le cluster à afficher : query param (clic graphe) > session_state > 0
                selected_cluster_idx = None
                try:
                    qp = getattr(st, "query_params", None)
                    if qp is not None and "jsonld_cluster" in qp:
                        selected_cluster_idx = int(qp["jsonld_cluster"])
                        if selected_cluster_idx >= num_clusters:
                            selected_cluster_idx = 0
                        st.session_state["jsonld_selected_cluster"] = selected_cluster_idx
                except (ValueError, TypeError, KeyError):
                    pass
                if selected_cluster_idx is None:
                    if "jsonld_selected_cluster" in st.session_state:
                        selected_cluster_idx = st.session_state["jsonld_selected_cluster"]
                    else:
                        selected_cluster_idx = 0

                options = [
                    f"{i + 1}. {(cluster_labels[i].get('model_name') or '').strip() or f'Cluster {i + 1}'} ({len(cluster_urls[i])} p.)"
                    for i in range(num_clusters)
                ]
                default_idx = selected_cluster_idx if selected_cluster_idx is not None and selected_cluster_idx < len(options) else 0
                sel = st.selectbox(
                    "Ou sélectionner manuellement :",
                    options,
                    index=default_idx,
                    key="jsonld_cluster_select",
                )
                if sel:
                    idx = options.index(sel)
                    st.session_state["jsonld_selected_cluster"] = idx
                    label = cluster_labels[idx] if idx < len(cluster_labels) else {}
                    name = (label.get("model_name") or "").strip() or f"Cluster {idx + 1}"
                    schema_type = (label.get("schema_type") or "").strip() or "—"
                    urls_in_cluster = cluster_urls[idx] if idx < len(cluster_urls) else []
                    pattern = get_cluster_url_pattern(urls_in_cluster)

                    st.markdown(f"**Modèle :** {name}")
                    st.markdown(f"**Schema.org :** `{schema_type}`")
                    st.markdown(f"**Pattern URL :** `{pattern}`")
                    st.markdown(f"**Nombre de pages :** {len(urls_in_cluster)}")

                    col_dom, col_json = st.columns(2)
                    with col_dom:
                        st.markdown("**Structure DOM type :**")
                        dom = cluster_dom[idx] if idx < len(cluster_dom) else {}
                        if dom:
                            st.json(dom)
                        else:
                            st.caption("Structure DOM non disponible.")

                    with col_json:
                        st.markdown("**JSON-LD existant :**")
                        jld = cluster_jsonld[idx] if idx < len(cluster_jsonld) else None
                        if jld:
                            st.json(jld)
                        else:
                            st.warning("Aucun JSON-LD détecté sur ces pages.")

                    st.markdown("**Exemples d'URLs :**")
                    for u in urls_in_cluster[:5]:
                        st.markdown(f"- [{u}]({u})")
                    if len(urls_in_cluster) > 5:
                        st.caption(f"... et {len(urls_in_cluster) - 5} autre(s) URL(s).")

            with tab_tableau:
                tab_labels = []
                for i in range(num_clusters):
                    label = cluster_labels[i] if i < len(cluster_labels) else {"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"}
                    name = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
                    n = len(cluster_urls[i]) if i < len(cluster_urls) else 0
                    tab_labels.append(f"{i + 1}. {name} ({n} p.)")

                cluster_tabs = st.tabs(tab_labels)

                for i, tab in enumerate(cluster_tabs):
                    with tab:
                        label = cluster_labels[i] if i < len(cluster_labels) else {"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"}
                        urls_in_cluster = cluster_urls[i] if i < len(cluster_urls) else []
                        pattern = get_cluster_url_pattern(urls_in_cluster)
                        sample = urls_in_cluster[:5]
                        name = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
                        schema_type = (label.get("schema_type") or "").strip() or "—"

                        st.markdown(f"**Modèle :** {name}")
                        st.markdown(f"**Type Schema.org :** `{schema_type}`")
                        st.markdown(f"**Pattern URL :** `{pattern}`")
                        st.markdown("**Exemples d'URLs :**")
                        for u in sample:
                            st.code(u, language=None)
                        if len(urls_in_cluster) > 5:
                            st.caption(f"... et {len(urls_in_cluster) - 5} autre(s) page(s).")

            with tab_export:
                from core.database import AuditDatabase
                from core.session_keys import get_current_user_email

                st.markdown("##### Charger depuis Google Sheets")
                _user_email = get_current_user_email() or ""
                _db = AuditDatabase()
                _sites = _db.list_jsonld_sites(_user_email) if _user_email and _db.client else []
                if _sites:
                    _opt_labels = [f"{s['site_url']} — {s['workspace']}" for s in _sites]
                    _sel_idx = st.selectbox("Site sauvegardé", range(len(_opt_labels)), format_func=lambda i: _opt_labels[i], key="jsonld_load_export")
                    if st.button("CHARGER DEPUIS GOOGLE SHEETS", use_container_width=True, key="jsonld_load_export_btn"):
                        _s = _sites[_sel_idx]
                        _models = _db.load_jsonld_models(_user_email, site_url=_s["site_url"])
                        _models = [m for m in _models if (m.get("workspace") or "").strip() == (_s.get("workspace") or "").strip()]
                        if _models:
                            _domain = urlparse(_s["site_url"]).netloc or "site"
                            _labels = []
                            _urls = []
                            _doms = []
                            _jlds = []
                            for m in _models:
                                _labels.append({"model_name": m.get("model_name") or "Cluster", "schema_type": m.get("recommended_schema") or "WebPage"})
                                _us = m.get("sample_urls") or "[]"
                                try:
                                    _u = json.loads(_us) if isinstance(_us, str) else _us
                                except json.JSONDecodeError:
                                    try:
                                        _u = json.loads(__import__("zlib").decompress(__import__("base64").b64decode(_us)).decode())
                                    except Exception:
                                        _u = []
                                _urls.append(_u if isinstance(_u, list) else [])
                                _doms.append(_db._decompress_from_sheet(m.get("dom_structure") or "") or {})
                                _jlds.append(_db._decompress_from_sheet(m.get("existing_jsonld") or ""))
                            st.session_state["jsonld_analyzer_results"] = {
                                "site_url": _s["site_url"], "domain": _domain,
                                "total_pages": sum(m.get("page_count", 0) for m in _models),
                                "cluster_labels": _labels, "cluster_urls": _urls,
                                "cluster_dom_structures": _doms, "cluster_jsonld": _jlds,
                                "logs": [], "loaded_from_sheet": True,
                            }
                            st.success("Données chargées.")
                            st.rerun()
                        else:
                            st.warning("Aucun modèle pour ce site et espace.")
                else:
                    st.caption("Aucune donnée sauvegardée.")
                st.markdown("##### Sauvegarde Google Sheets")
                site_url = data.get("site_url") or f"https://{domain}"
                workspace = st.session_state.get("audit_workspace_select", "Non classé") or "Non classé"
                if workspace == "+ Creer Nouveau":
                    workspace = "Non classé"

                models_data = []
                for i in range(num_clusters):
                    label = cluster_labels[i] if i < len(cluster_labels) else {}
                    urls_in_cluster = cluster_urls[i] if i < len(cluster_urls) else []
                    pattern = get_cluster_url_pattern(urls_in_cluster)
                    models_data.append({
                        "model_name": (label.get("model_name") or "").strip() or f"Cluster {i + 1}",
                        "schema_type": (label.get("schema_type") or "").strip() or "WebPage",
                        "page_count": len(urls_in_cluster),
                        "url_pattern": pattern,
                        "sample_urls": urls_in_cluster[:5],
                        "dom_structure": cluster_dom[i] if i < len(cluster_dom) else None,
                        "existing_jsonld": cluster_jsonld[i] if i < len(cluster_jsonld) else None,
                        "optimized_jsonld": None,
                    })

                if st.button("SAUVEGARDER DANS GOOGLE SHEETS", type="primary", use_container_width=True, key="jsonld_save_btn"):
                    user_email = get_current_user_email() or ""
                    db = AuditDatabase()
                    if db.save_jsonld_models(user_email, site_url, workspace, models_data):
                        st.success("Modèles JSON-LD enregistrés dans l'onglet 'jsonld' du Google Sheet.")
                        try:
                            st.toast("Sauvegarde réussie", icon="✅")
                        except Exception:
                            pass
                    else:
                        st.error("Échec de la sauvegarde. Vérifiez la configuration GCP (secrets) et l'URL du Sheet.")

                st.markdown("##### Téléchargement JSON")
                payload = {
                    "site_url": site_url,
                    "analyzed_at": __import__("datetime").datetime.now().isoformat() + "Z",
                    "total_pages": total_pages,
                    "models": models_data,
                }
                json_str = json.dumps(payload, ensure_ascii=False, indent=2)
                st.download_button(
                    "Télécharger le JSON complet",
                    data=json_str,
                    file_name=f"jsonld_models_{domain.replace('.', '_')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="jsonld_download_btn",
                )

        if logs:
            with st.expander("Logs de crawl"):
                st.text("\n".join(logs[-150:]))
