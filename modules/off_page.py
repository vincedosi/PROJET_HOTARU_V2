"""
HOTARU - Module Off-Page Reputation

Analyse rapide de la présence d'une marque sur les grandes plateformes
de discussion / autorité (Reddit, Quora, Wikipedia, LinkedIn, YouTube, etc.).
"""

from __future__ import annotations

import json
from typing import Dict, List
from urllib.parse import urlparse, urljoin

import networkx as nx
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup  # Optionnel si on veut enrichir plus tard
from pyvis.network import Network

try:
    # googlesearch-python
    from googlesearch import search

    HAS_GOOGLESEARCH = True
except Exception:
    HAS_GOOGLESEARCH = False


# --- CONFIGURATION DES SOURCES ---
SOURCE_CONFIG: Dict[str, Dict[str, str]] = {
    "reddit.com": {"label": "REDDIT", "color": "#FF4500"},
    "quora.com": {"label": "QUORA", "color": "#B92B27"},
    "wikipedia.org": {"label": "WIKIPEDIA", "color": "#000000"},
    "linkedin.com": {"label": "LINKEDIN", "color": "#0077B5"},
    "medium.com": {"label": "MEDIUM", "color": "#12100E"},
    "trustpilot.com": {"label": "TRUSTPILOT", "color": "#00B67A"},
    "youtube.com": {"label": "YOUTUBE", "color": "#FF0000"},
    "twitter.com": {"label": "X (TWITTER)", "color": "#1DA1F2"},
    "x.com": {"label": "X (TWITTER)", "color": "#000000"},
    "facebook.com": {"label": "FACEBOOK", "color": "#1877F2"},
    "instagram.com": {"label": "INSTAGRAM", "color": "#E1306C"},
    "tiktok.com": {"label": "TIKTOK", "color": "#000000"},
    "github.com": {"label": "GITHUB", "color": "#181717"},
    "stackoverflow.com": {"label": "STACKOVERFLOW", "color": "#F58025"},
    "glassdoor.com": {"label": "GLASSDOOR", "color": "#0CAA41"},
}


def render_interactive_graph(G: nx.Graph) -> None:
    """Moteur de rendu Pyvis strict Hotaru V3"""
    nt = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#0f172a")
    nt.from_nx(G)
    opts = {
        "nodes": {
            "font": {
                "face": "Inter, sans-serif",
                "size": 14,
                "strokeWidth": 3,
                "strokeColor": "#ffffff",
                "color": "#0f172a",
            },
            "borderWidth": 2,
            "borderWidthSelected": 3,
        },
        "edges": {
            "color": "#cbd5e1",
            "smooth": {"type": "dynamic", "roundness": 0.2},
            "width": 1.5,
        },
        "interaction": {
            "hover": True,
            "navigationButtons": True,
            "zoomView": True,
        },
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -100,
                "centralGravity": 0.05,
                "springLength": 150,
                "springConstant": 0.08,
                "avoidOverlap": 1,
            },
            "solver": "forceAtlas2Based",
            "stabilization": {"enabled": True, "iterations": 200},
        },
    }
    nt.set_options(json.dumps(opts))
    path = "temp_offpage_graph.html"
    nt.save_graph(path)
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    custom_code = """
    <style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap'); * { font-family: 'Inter', sans-serif !important; }</style>
    """
    components.html(html.replace("</body>", custom_code + "</body>"), height=750)


def build_reputation_graph(brand: str, mentions: List[Dict[str, str]]) -> nx.DiGraph:
    """Construit le graphe en étoile"""
    G = nx.DiGraph()
    # Noeud Central
    G.add_node(
        brand,
        label=brand.upper(),
        size=40,
        color="#0f172a",
        font={"color": "#ffffff", "size": 20},
        title="MARQUE CIBLE",
    )

    for m in mentions:
        color = SOURCE_CONFIG.get(m["domain_key"], {}).get("color", "#64748b")
        label = SOURCE_CONFIG.get(m["domain_key"], {}).get("label", "AUTRE")
        G.add_node(
            m["url"],
            label=label,
            size=20,
            color=color,
            title=f"{m['title']}\n{m['url']}",
        )
        G.add_edge(brand, m["url"], color="#cbd5e1")
    return G


def _detect_domain_key(url: str) -> str | None:
    """Retourne la clef de domaine normalisée à partir de l'URL."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return None
    for domain_key in SOURCE_CONFIG.keys():
        if host.endswith(domain_key):
            return domain_key
    return None


def _fetch_off_page_mentions(brand: str, max_results_per_source: int = 5) -> List[Dict[str, str]]:
    """Interroge Google pour chaque source et renvoie une liste de mentions."""
    if not HAS_GOOGLESEARCH:
        return []

    mentions: List[Dict[str, str]] = []
    seen_urls: set[str] = set()

    for domain in SOURCE_CONFIG.keys():
        query = f'"{brand}" site:{domain}'
        try:
            # Utilisation de googlesearch-python : generator d'URLs
            for url in search(query, num=5, stop=max_results_per_source, lang="fr"):
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                domain_key = _detect_domain_key(url) or domain
                title = url

                mentions.append(
                    {
                        "brand": brand,
                        "domain_key": domain_key,
                        "source": SOURCE_CONFIG.get(domain_key, {}).get("label", "AUTRE"),
                        "url": url,
                        "title": title,
                    }
                )
        except Exception as e:
            # On logge côté console pour debug, mais on continue
            print(f"[OFF_PAGE] Erreur recherche pour {domain}: {e}")
            continue

    return mentions


def render_off_page_audit() -> None:
    """Interface principale de l'audit Off-Page."""
    st.markdown(
        '<p class="section-title">02 / AUDIT EXTERNE</p>',
        unsafe_allow_html=True,
    )

    brand = st.text_input(
        "Nom de la marque",
        placeholder="Ex: BMW, Zapier, Hotaru...",
        label_visibility="collapsed",
        key="offpage_brand_input",
    )

    if not HAS_GOOGLESEARCH:
        st.error(
            "Le module `googlesearch-python` n'est pas installé. "
            "Installez-le avec `pip install googlesearch-python` pour lancer l'analyse."
        )
        return

    if "offpage_results" not in st.session_state:
        st.session_state["offpage_results"] = None
        st.session_state["offpage_brand"] = None

    if st.button(
        "LANCER L'ANALYSE OFF-PAGE",
        type="primary",
        use_container_width=True,
        key="offpage_launch_btn",
    ):
        if not brand or not brand.strip():
            st.warning("Veuillez saisir un nom de marque.")
        else:
            with st.spinner("Recherche des mentions externes..."):
                mentions = _fetch_off_page_mentions(brand.strip())
            st.session_state["offpage_results"] = mentions
            st.session_state["offpage_brand"] = brand.strip()

    mentions = st.session_state.get("offpage_results") or []
    current_brand = st.session_state.get("offpage_brand") or brand.strip()

    if not current_brand or not mentions:
        st.info(
            "Entrez un nom de marque et lancez l'analyse pour voir la carte Off-Page."
        )
        return

    tab_graph, tab_list = st.tabs(["VISUALISATION GRAPHIQUE", "LISTE DÉTAILLÉE"])

    with tab_graph:
        st.markdown(
            "<p class='label-caps'>Carte Off-Page — Plateformes d'autorité</p>",
            unsafe_allow_html=True,
        )
        G = build_reputation_graph(current_brand, mentions)
        render_interactive_graph(G)

    with tab_list:
        st.markdown(
            "<p class='label-caps'>Mentions externes détectées</p>",
            unsafe_allow_html=True,
        )
        if mentions:
            st.dataframe(
                [
                    {
                        "Source": m["source"],
                        "Domaine": m["domain_key"],
                        "URL": m["url"],
                    }
                    for m in mentions
                ],
                use_container_width=True,
            )
        else:
            st.write("Aucune mention détectée pour l'instant.")

        if st.button("SAUVEGARDER DATA (GOOGLE SHEETS)", use_container_width=True, key="offpage_save_btn"):
            payload = {"external_data": mentions}
            st.success(
                "Payload prêt pour envoi vers Google Sheets (colonne 'externe') :\n\n"
                + json.dumps(payload, indent=2, ensure_ascii=False)
            )

