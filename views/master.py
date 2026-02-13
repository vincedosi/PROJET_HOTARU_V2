"""
HOTARU v3 - Module MASTER DATA
Interface Brutaliste Monochrome pour l'enrichissement et l'édition des données d'entité.
"""

import os
import json
import difflib
from typing import Dict, List, Tuple

import requests
import streamlit as st
from bs4 import BeautifulSoup

from core.scraping import fetch_page
from core.database import AuditDatabase
from core.session_keys import get_current_user_email
from engine.master_handler import MasterDataHandler, MasterData, WikidataAPI
from engine.template_builder import TemplateBuilder


def _get_mistral_key():
    try:
        return st.secrets["mistral"]["api_key"]
    except Exception:
        return ""


def _ensure_search_state() -> None:
    """Initialise les listes de résultats de recherche dans la session."""
    if "master_wiki_results" not in st.session_state:
        st.session_state.master_wiki_results: List[Dict] = []
    if "master_insee_results" not in st.session_state:
        st.session_state.master_insee_results: List[Dict] = []


def _search_wikidata_candidates(query: str) -> List[Dict]:
    """Recherche d'entités sur Wikidata (mode liste de candidats)."""
    raw = WikidataAPI.search_entity(query, limit=10)
    results: List[Dict] = []
    for item in raw:
        results.append(
            {
                "id": item.get("id"),
                "label": item.get("label", item.get("id", "")),
                "desc": item.get("description", "Pas de description"),
            }
        )
    return results


def _search_insee_candidates(query: str) -> List[Dict]:
    """Recherche d'entreprises via l'API publique INSEE / Entreprises."""
    try:
        r = requests.get(
            "https://recherche-entreprises.api.gouv.fr/search",
            params={"q": query, "per_page": 10},
            timeout=10,
        )
        r.raise_for_status()
        payload = r.json()
        results = payload.get("results", [])
        formatted: List[Dict] = []
        for item in results:
            siege = item.get("siege", {}) or {}
            formatted.append(
                {
                    "siren": item.get("siren", ""),
                    "name": item.get("nom_complet", ""),
                    "address": " ".join(
                        part
                        for part in [
                            siege.get("adresse", ""),
                            siege.get("code_postal", ""),
                            siege.get("commune", ""),
                        ]
                        if part
                    ).strip(),
                    "active": item.get("etat_administratif") == "A",
                }
            )
        return formatted
    except Exception as e:  # pragma: no cover - réseau extérieur
        st.warning(f"Erreur INSEE: {e}")
        return []


def extract_jsonld_from_url(url: str, timeout: int = 15) -> str:
    """
    Récupère le JSON-LD d'une page web donnée.

    Utilise la même logique de requêtes que le scraper (fetch_page)
    puis parse le premier <script type="application/ld+json"> trouvé.
    Retourne une chaîne JSON jolie (indentée) prête pour affichage / diff.
    """
    # Normalisation simple de l'URL
    url = url.strip()
    if not url:
        raise ValueError("URL vide.")

    try:
        raw_html = fetch_page(url, timeout=timeout)
    except requests.RequestException as e:  # type: ignore[no-untyped-call]
        raise RuntimeError(f"Erreur réseau lors de la récupération de la page: {e}")

    soup = BeautifulSoup(raw_html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")
    if not scripts:
        raise RuntimeError("Aucun script JSON-LD (<script type=\"application/ld+json\">) trouvé sur cette page.")

    # On prend le premier script JSON-LD non vide
    content = ""
    for tag in scripts:
        if tag.string and tag.string.strip():
            content = tag.string.strip()
            break
        text = tag.get_text(strip=True)
        if text:
            content = text
            break

    if not content:
        raise RuntimeError("Balise JSON-LD trouvée mais vide.")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON-LD invalide sur la page: {e}")

    pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
    return pretty


def _find_organization_node(data: object) -> Dict:
    """Cherche récursivement un noeud Organization / LocalBusiness dans un JSON-LD."""
    if isinstance(data, dict):
        t = data.get("@type")
        types: List[str] = []
        if isinstance(t, str) and t:
            types = [t]
        elif isinstance(t, list):
            types = [str(x) for x in t]

        if any(tt in ("Organization", "LocalBusiness", "Corporation") for tt in types):
            return data

        # Parcourir récursivement les sous-objets
        for v in data.values():
            found = _find_organization_node(v)
            if found:
                return found

    elif isinstance(data, list):
        for item in data:
            found = _find_organization_node(item)
            if found:
                return found

    return {}


def extract_org_fields_from_jsonld(json_text: str) -> Dict[str, str]:
    """
    Extrait les champs pertinents d'un JSON-LD (Organization) pour pré-remplir Master.

    Retourne un dict plat avec des clés alignées sur MasterData :
    - brand_name, legal_name, description, site_url, logo_url,
      phone, email, street, city, zip_code, region, country,
      linkedin_url, twitter_url, facebook_url, instagram_url, youtube_url.
    """
    try:
        data = json.loads(json_text)
    except Exception:
        return {}

    node = _find_organization_node(data)
    if not node:
        return {}

    out: Dict[str, str] = {}

    out["brand_name"] = str(node.get("name", "")).strip()
    out["legal_name"] = str(node.get("legalName", "")).strip()
    out["description"] = str(node.get("description", "")).strip()
    out["site_url"] = str(node.get("url", "")).strip()

    logo = node.get("logo")
    logo_url = ""
    if isinstance(logo, str):
        logo_url = logo
    elif isinstance(logo, dict):
        logo_url = str(logo.get("url", "")).strip()
    out["logo_url"] = logo_url

    out["phone"] = str(node.get("telephone", "")).strip()
    out["email"] = str(node.get("email", "")).strip()

    addr = node.get("address") or {}
    if isinstance(addr, dict):
        out["street"] = str(addr.get("streetAddress", "")).strip()
        out["city"] = str(addr.get("addressLocality", "")).strip()
        out["zip_code"] = str(addr.get("postalCode", "")).strip()
        out["region"] = str(addr.get("addressRegion", "")).strip()
        country = addr.get("addressCountry", "")
        if isinstance(country, dict):
            out["country"] = str(country.get("name", "")).strip()
        else:
            out["country"] = str(country).strip()

    # Déduction des réseaux sociaux à partir de sameAs
    same_as = node.get("sameAs") or []
    if isinstance(same_as, str):
        same_as = [same_as]

    for url in same_as:
        u = str(url).lower()
        if "linkedin.com" in u and "linkedin_url" not in out:
            out["linkedin_url"] = url
        elif ("twitter.com" in u or "x.com" in u) and "twitter_url" not in out:
            out["twitter_url"] = url
        elif "facebook.com" in u and "facebook_url" not in out:
            out["facebook_url"] = url
        elif "instagram.com" in u and "instagram_url" not in out:
            out["instagram_url"] = url
        elif "youtube.com" in u and "youtube_url" not in out:
            out["youtube_url"] = url

    return {k: v for k, v in out.items() if v}


def hydrate_master_from_org(master: MasterData, org_fields: Dict[str, str]) -> List[str]:
    """
    Injecte dans MasterData les champs issus du JSON-LD client (sans écraser l'existant).

    Retourne la liste des champs effectivement mis à jour.
    """
    updated: List[str] = []
    if not org_fields:
        return updated

    for key, value in org_fields.items():
        if hasattr(master, key) and value:
            current = getattr(master, key, "")
            if not current:
                setattr(master, key, value)
                updated.append(key)
    return updated
def _escape_html(text: str) -> str:
    """Échappe les caractères HTML pour un rendu sûr."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def build_json_diff_blocks(client_json: str, hotaru_json: str) -> Tuple[str, str]:
    """
    Construit deux blocs HTML (<pre>...) pour un diff visuel côte à côte.

    - client_json : JSON-LD extrait du site client (gauche)
    - hotaru_json : JSON-LD généré par HOTARU (droite)

    Convention de couleurs :
    - Lignes identiques : fond gris léger
    - Lignes présentes uniquement chez HOTARU : fond vert clair + gras
    - Lignes présentes uniquement chez le client : fond rouge clair
    """
    client_lines = client_json.splitlines()
    hotaru_lines = hotaru_json.splitlines()

    sm = difflib.SequenceMatcher(a=client_lines, b=hotaru_lines)

    left_segments: List[Tuple[str, str]] = []
    right_segments: List[Tuple[str, str]] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for i in range(i1, i2):
                left_segments.append(("equal", client_lines[i]))
            for j in range(j1, j2):
                right_segments.append(("equal", hotaru_lines[j]))
        elif tag == "replace":
            for i in range(i1, i2):
                left_segments.append(("removed", client_lines[i]))
            for j in range(j1, j2):
                right_segments.append(("added", hotaru_lines[j]))
        elif tag == "delete":
            for i in range(i1, i2):
                left_segments.append(("removed", client_lines[i]))
        elif tag == "insert":
            for j in range(j1, j2):
                right_segments.append(("added", hotaru_lines[j]))

    def _build_pre_html(segments: List[Tuple[str, str]]) -> str:
        pre_style = (
            "font-family:'SF Mono','Fira Code','Consolas',monospace;"
            "font-size:0.8rem;"
            "padding:12px;"
            "background:#FFFFFF;"
            "border:1px solid rgba(0,0,0,0.12);"
            "white-space:pre;"
            "overflow-x:auto;"
        )
        html = [f'<pre style="{pre_style}">']
        for idx, (kind, line) in enumerate(segments, start=1):
            base = "display:block;padding:2px 4px;margin-bottom:1px;"
            if kind == "equal":
                # Lignes identiques : neutre / gris clair
                style = base + "background:#f5f5f5;color:#111111;"
            elif kind == "added":
                # Ajout HOTARU (vert)
                style = base + "background:#e6ffed;color:#166534;font-weight:600;"
            elif kind == "removed":
                # Présent uniquement chez le client (rouge)
                style = base + "background:#fef2f2;color:#b91c1c;"
            else:
                style = base

            # Numéro de ligne à gauche
            ln = (
                f'<span style="display:inline-block;width:32px;'
                f'text-align:right;margin-right:8px;color:#9ca3af;">{idx}</span>'
            )

            escaped = _escape_html(line)
            html.append(f'<span style="{style}">{ln}{escaped}</span>')
        html.append("</pre>")
        return "\n".join(html)

    left_html = _build_pre_html(left_segments)
    right_html = _build_pre_html(right_segments)
    return left_html, right_html


def render_master_tab():
    """Onglet MASTER - Interface Brutaliste avec champs editables"""

    if "master_data" not in st.session_state:
        st.session_state.master_data = None

    # Sélecteur de MASTER sauvegardés (depuis l'onglet audits)
    db = AuditDatabase()
    saved_audits = db.load_user_audits(get_current_user_email() or "")
    saved_masters = [
        a for a in saved_audits if (a.get("master_json") or "").strip()
    ]

    # Header
    st.markdown('<h1 class="zen-title">MASTER DATA</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="zen-subtitle">PERMANENT ENTITY DATA // JSON-LD FOUNDATION</p>',
        unsafe_allow_html=True,
    )

    # Sous-onglets : Données / Méthodologie
    tab_donnees, tab_methodo = st.tabs(["Données", "Méthodologie"])
    with tab_donnees:
        # Bandeau de sélection/chargement des MASTER existants
        if saved_masters:
            options = {
                f"{a.get('nom_site','Site')} // {a.get('site_url','')} ({a.get('date','')})": a
                for a in saved_masters
            }
            c1, c2 = st.columns([3, 1])
            choice = c1.selectbox(
                "Charger un MASTER existant (depuis audits)",
                list(options.keys()),
                index=0,
                key="master_load_select",
            )
            if c2.button("CHARGER MASTER", use_container_width=True, key="load_master_btn"):
                selected = options[choice]
                st.session_state.jsonld_master = selected.get("master_json", "")
                st.success("MASTER chargé depuis l'onglet audits. Vous pouvez l'utiliser pour l'AUDIT & GAP ANALYSIS.")

        _render_master_data_content()
    with tab_methodo:
        from views.methodologie_blocks import render_methodologie_for_module
        render_methodologie_for_module("master")


def _render_master_data_content():
    """Contenu de l'onglet Données (Master)."""
    _ensure_search_state()
    # =========================================================================
    # ETAPE 1 : RECHERCHE & ENRICHISSEMENT
    # =========================================================================

    st.markdown(
        '<p class="section-title">01 / IDENTIFICATION & ENRICHISSEMENT</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-container">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        company_name = st.text_input(
            "ENTITY NAME",
            placeholder="ENTITY NAME",
            key="company_search",
        )

    with col2:
        qid_manual = st.text_input(
            "WIKIDATA QID",
            placeholder="Q-IDENTIFIER",
            key="qid_search",
        )

    with col3:
        siren_manual = st.text_input(
            "SIRET",
            placeholder="ID NUMBER",
            key="siren_search",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    # Recherche d'entités (Wikidata + INSEE) pour laisser l'utilisateur choisir
    with col_btn1:
        if st.button("SEARCH ENTITIES", use_container_width=True, key="search_btn"):
            if company_name or qid_manual or siren_manual:
                query = company_name or qid_manual or siren_manual
                with st.spinner("Recherche Wikidata / INSEE..."):
                    st.session_state.master_wiki_results = _search_wikidata_candidates(
                        query
                    )
                    st.session_state.master_insee_results = _search_insee_candidates(
                        query
                    )
            else:
                st.error("Entrez au moins un critère")

    with col_btn2:
        if st.button(
            "MISTRAL ENRICH",
            use_container_width=True,
            key="enrich_btn",
            type="primary",
            disabled=not st.session_state.master_data,
        ):
            mistral_key = _get_mistral_key()
            if mistral_key and st.session_state.master_data and st.session_state.master_data.qid:
                with st.spinner("Mistral enrichit les données..."):
                    handler = MasterDataHandler()
                    st.session_state.master_data = handler.auto_complete_with_mistral(
                        st.session_state.master_data, mistral_key
                    )
                    st.rerun()
            else:
                st.error("Clé Mistral ou QID manquant")

    # Résultats de recherche (Wikidata / INSEE) et sélection utilisateur
    if st.session_state.master_wiki_results or st.session_state.master_insee_results:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### Wikidata")
            if st.session_state.master_wiki_results:
                for item in st.session_state.master_wiki_results:
                    label = item.get("label", "")
                    desc = item.get("desc", "")
                    button_label = f"🆔 {label}\n{desc}"
                    if st.button(
                        button_label,
                        key=f"master_wiki_{item.get('id','')}",
                        use_container_width=True,
                    ):
                        # Enrichir directement MasterData à partir du QID sélectionné
                        handler = MasterDataHandler()
                        st.session_state.master_data = handler.auto_enrich(
                            search_query=label,
                            qid=item.get("id", ""),
                            siren=None,
                        )
                        st.session_state.master_wiki_results = []
                        st.session_state.master_insee_results = []
                        st.rerun()
            else:
                st.info("Aucun résultat Wikidata.")

        with c2:
            st.markdown("#### INSEE / SIREN")
            if st.session_state.master_insee_results:
                for idx, item in enumerate(st.session_state.master_insee_results):
                    statut = "🟢" if item.get("active") else "🔴"
                    name = item.get("name", "")
                    addr = item.get("address", "")
                    label = f"{statut} {name}\n{addr}"
                    key = f"master_insee_{item.get('siren','')}_{idx}"
                    if st.button(label, key=key, use_container_width=True):
                        siren = item.get("siren", "")
                        handler = MasterDataHandler()
                        st.session_state.master_data = handler.auto_enrich(
                            search_query=name or None,
                            qid=None,
                            siren=siren or None,
                        )
                        st.session_state.master_wiki_results = []
                        st.session_state.master_insee_results = []
                        st.rerun()
            else:
                st.info("Aucun résultat INSEE.")

    st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # ETAPE 2 : EDITION DES DONNEES
    # =========================================================================

    if not st.session_state.master_data:
        return

    master = st.session_state.master_data

    st.markdown("<br>", unsafe_allow_html=True)

    # Status + Metrics row
    col_status, col_m1, col_m2, col_m3 = st.columns([1.2, 1, 1, 1])

    with col_status:
        status_map = {
            "complete": ("status-complete", "COMPLET"),
            "partial": ("status-partial", "PARTIEL"),
            "failed": ("status-failed", "ECHEC"),
        }
        cls, txt = status_map.get(master.status, ("status-partial", "PARTIEL"))
        st.markdown(
            f'<span class="status-badge {cls}">STATUS: {txt}</span>',
            unsafe_allow_html=True,
        )

        if master.errors:
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown(
                '<div style="border:1px solid rgba(0,0,0,0.12);padding:12px;">'
                '<span class="label-caps">LOGS / ERRORS</span>',
                unsafe_allow_html=True,
            )
            for error in master.errors:
                st.markdown(
                    f'<div style="font-size:0.75rem;color:rgba(0,0,0,0.55);margin-top:4px;">{error}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)

    key_fields = [master.brand_name, master.qid, master.site_url]
    social_fields = [
        master.wikipedia_url, master.linkedin_url, master.twitter_url,
        master.facebook_url, master.instagram_url, master.youtube_url,
    ]
    contact_fields = [master.phone, master.email, master.street, master.city]

    for col, (count, label) in zip(
        [col_m1, col_m2, col_m3],
        [
            (len([f for f in key_fields if f]), "KEY FIELDS"),
            (len([f for f in social_fields if f]), "SOCIAL NETS"),
            (len([f for f in contact_fields if f]), "CONTACT DATA"),
        ],
    ):
        with col:
            st.markdown(
                f'<div class="zen-metric">'
                f'<div class="zen-metric-value">{count:02d}</div>'
                f'<div class="zen-metric-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    st.markdown(
        '<p class="section-title">02 / FIELD MANAGEMENT</p>',
        unsafe_allow_html=True,
    )

    # IDENTITE
    st.markdown(
        '<div class="section-container" style="padding:0;margin-bottom:24px;">'
        '<div class="section-header">IDENTITY</div>'
        '<div style="padding:24px;">',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        master.brand_name = st.text_input(
            "TRADE NAME", value=master.brand_name, key="edit_brand"
        )
        master.legal_name = st.text_input(
            "LEGAL NAME", value=master.legal_name, key="edit_legal"
        )
        org_types = [
            "Corporation", "LocalBusiness", "EducationalOrganization",
            "GovernmentOrganization", "NGO",
        ]
        idx = org_types.index(master.org_type) if master.org_type in org_types else 0
        master.org_type = st.selectbox(
            "ORGANIZATION TYPE", org_types, index=idx, key="edit_type"
        )

    with col2:
        master.description = st.text_area(
            "DESCRIPTION", value=master.description, height=100, key="edit_desc"
        )
        master.slogan = st.text_input(
            "SLOGAN", value=master.slogan, key="edit_slogan"
        )

    st.markdown('</div></div>', unsafe_allow_html=True)

    # IDENTIFIANTS
    st.markdown(
        '<div class="section-container" style="padding:0;margin-bottom:24px;">'
        '<div class="section-header">IDENTIFIERS</div>'
        '<div style="padding:24px;">',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("WIKIDATA", value=master.qid, disabled=True, key="view_qid")
        master.siren = st.text_input("SIREN", value=master.siren, key="edit_siren")
    with col2:
        master.siret = st.text_input("SIRET", value=master.siret, key="edit_siret")
        master.lei = st.text_input("LEI", value=master.lei, key="edit_lei")
    with col3:
        master.site_url = st.text_input(
            "WEBSITE", value=master.site_url, key="edit_site"
        )
        master.ticker_symbol = st.text_input(
            "TICKER", value=master.ticker_symbol, key="edit_ticker"
        )

    st.markdown('</div></div>', unsafe_allow_html=True)

    # RESEAUX SOCIAUX
    st.markdown(
        '<div class="section-container" style="padding:0;margin-bottom:24px;">'
        '<div class="section-header">SOCIAL PRESENCE</div>'
        '<div style="padding:24px;">',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        master.linkedin_url = st.text_input(
            "LINKEDIN", value=master.linkedin_url, key="edit_linkedin"
        )
        master.twitter_url = st.text_input(
            "X / TWITTER", value=master.twitter_url, key="edit_twitter"
        )
        master.facebook_url = st.text_input(
            "FACEBOOK", value=master.facebook_url, key="edit_facebook"
        )
    with col2:
        master.youtube_url = st.text_input(
            "YOUTUBE", value=master.youtube_url, key="edit_youtube"
        )
        master.tiktok_url = st.text_input(
            "TIKTOK", value=master.tiktok_url, key="edit_tiktok"
        )
        master.instagram_url = st.text_input(
            "INSTAGRAM", value=master.instagram_url, key="edit_instagram"
        )

    st.markdown('</div></div>', unsafe_allow_html=True)

    # VISUELS
    st.markdown(
        '<div class="section-container" style="padding:0;margin-bottom:24px;">'
        '<div class="section-header">VISUAL ASSETS</div>'
        '<div style="padding:24px;">',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        master.logo_url = st.text_input(
            "LOGO URL", value=master.logo_url, key="edit_logo"
        )
    with col2:
        if master.logo_url:
            try:
                st.image(master.logo_url, width=150)
            except Exception:
                st.caption("Impossible de charger l'image")
        else:
            if st.button("PREVIEW", use_container_width=True, key="preview_logo"):
                pass

    st.markdown('</div></div>', unsafe_allow_html=True)

    # CORPORATE
    tab_corp, tab_addr = st.tabs(["OPTIONAL CORPORATE DATA", "ADDRESS & CONTACT"])
    with tab_corp:
        col1, col2, col3 = st.columns(3)
        with col1:
            master.founding_date = st.text_input(
                "DATE DE CREATION", value=master.founding_date,
                placeholder="YYYY-MM-DD", key="edit_founding"
            )
            master.num_employees = st.text_input(
                "NOMBRE D'EMPLOYES", value=master.num_employees, key="edit_employees"
            )
        with col2:
            master.founder_name = st.text_input(
                "FONDATEUR", value=master.founder_name, key="edit_founder"
            )
            master.parent_org = st.text_input(
                "ORGANISATION MERE", value=master.parent_org, key="edit_parent"
            )
        with col3:
            master.annual_revenue = st.text_input(
                "CHIFFRE D'AFFAIRES", value=master.annual_revenue, key="edit_revenue"
            )
            master.stock_exchange = st.text_input(
                "BOURSE", value=master.stock_exchange, key="edit_exchange"
            )

    with tab_addr:
        # ADRESSE & CONTACT
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                '<div class="section-container" style="padding:0;margin-bottom:24px;">'
                '<div class="section-header">ADDRESS</div>'
                '<div style="padding:24px;">',
                unsafe_allow_html=True,
            )
            master.street = st.text_input("RUE", value=master.street, key="edit_street")
            col_city, col_zip = st.columns([2, 1])
            master.city = col_city.text_input("VILLE", value=master.city, key="edit_city")
            master.zip_code = col_zip.text_input(
                "CODE POSTAL", value=master.zip_code, key="edit_zip"
            )
            master.region = st.text_input(
                "REGION", value=master.region, key="edit_region"
            )
            master.country = st.text_input(
                "PAYS", value=master.country, key="edit_country"
            )
            st.markdown('</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown(
                '<div class="section-container" style="padding:0;margin-bottom:24px;">'
                '<div class="section-header">CONTACT</div>'
                '<div style="padding:24px;">',
                unsafe_allow_html=True,
            )
            master.phone = st.text_input(
                "TELEPHONE", value=master.phone,
                placeholder="+33 1 23 45 67 89", key="edit_phone"
            )
            master.email = st.text_input(
                "EMAIL", value=master.email,
                placeholder="contact@exemple.fr", key="edit_email"
            )
            master.fax = st.text_input("FAX", value=master.fax, key="edit_fax")
            master.wikipedia_url = st.text_input(
                "WIKIPEDIA", value=master.wikipedia_url, key="edit_wiki"
            )
            st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    # =====================================================================
    # ETAPE 3 : GENERATION JSON-LD
    # =====================================================================

    st.markdown(
        '<p class="section-title">03 / COMPILATION</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        if st.button(
            "GENERER LE JSON-LD",
            type="primary",
            use_container_width=True,
            key="generate_btn",
        ):
            with st.spinner("Generation en cours..."):
                builder = TemplateBuilder()
                jsonld_master = builder.generate_jsonld(
                    master_data=master, dynamic_data=None, page_data=None
                )
                st.session_state.jsonld_master = jsonld_master
                st.success("JSON-LD Master genere")
                st.rerun()

    if "jsonld_master" in st.session_state and st.session_state.jsonld_master:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-container">', unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])

        with col1:
            st.code(
                st.session_state.jsonld_master, language="json", line_numbers=True
            )

        with col2:
            st.download_button(
                label="TELECHARGER",
                data=st.session_state.jsonld_master,
                file_name=f"master_{master.brand_name.lower().replace(' ', '_')}.json",
                mime="application/ld+json",
                use_container_width=True,
            )

            st.metric("LIGNES", len(st.session_state.jsonld_master.split("\n")))
            st.metric("TAILLE", f"{len(st.session_state.jsonld_master)} chars")

            # Sauvegarde dans Google Sheet (colonne J 'master')
            if st.button("ENREGISTRER DANS AUDITS", use_container_width=True, key="save_master_to_audits"):
                db = AuditDatabase()
                user_email = get_current_user_email() or ""
                workspace = st.session_state.get("current_ws", "Non classé")
                site_url = st.session_state.get("target_url", "").strip()
                if not site_url:
                    st.error("Impossible de sauvegarder : aucune URL de site (target_url) en mémoire.")
                else:
                    ok = db.save_master_for_audit(
                        user_email=user_email,
                        workspace=workspace,
                        site_url=site_url,
                        master_json=st.session_state.jsonld_master,
                    )
                    if ok:
                        st.success("MASTER enregistré dans l'onglet audits (colonne J).")

            if st.button("NOUVEAU", use_container_width=True, key="reset_btn"):
                st.session_state.master_data = None
                st.session_state.pop("jsonld_master", None)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # =====================================================================
    # ETAPE 4 : AUDIT & GAP ANALYSIS
    # =====================================================================

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-title">04 / AUDIT & GAP ANALYSIS</p>',
        unsafe_allow_html=True,
    )

    # Légende visuelle (identique / ajouté / manquant)
    st.markdown(
        """
<div style="font-size:0.7rem;margin-bottom:12px;display:flex;gap:12px;align-items:center;">
  <span class="label-caps" style="margin-bottom:0;">Legend</span>
  <span style="padding:2px 6px;background:#f5f5f5;border:1px solid rgba(0,0,0,0.12);">
    Lignes identiques
  </span>
  <span style="padding:2px 6px;background:#e6ffed;border:1px solid rgba(0,0,0,0.12);">
    Ajouts HOTARU
  </span>
  <span style="padding:2px 6px;background:#fef2f2;border:1px solid rgba(0,0,0,0.12);">
    Présent uniquement sur le site client
  </span>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-container" style="padding:24px;">',
        unsafe_allow_html=True,
    )

    url_client = st.text_input(
        "URL DU SITE CLIENT",
        placeholder="https://www.exemple.com/page",
        key="audit_gap_url",
    )

    compare_clicked = st.button(
        "EXTRAIRE & COMPARER", use_container_width=True, key="audit_gap_btn"
    )

    if compare_clicked:
        if not url_client:
            st.error("Merci de renseigner une URL du site client.")
        elif "jsonld_master" not in st.session_state or not st.session_state.jsonld_master:
            st.error(
                "Générez d'abord le JSON-LD Master dans la section 03 / COMPILATION."
            )
        else:
            try:
                with st.spinner("Extraction du JSON-LD du site client..."):
                    client_json = extract_jsonld_from_url(url_client)
                hotaru_json = st.session_state.jsonld_master
                left_html, right_html = build_json_diff_blocks(client_json, hotaru_json)
                st.session_state["audit_gap_client_html"] = left_html
                st.session_state["audit_gap_hotaru_html"] = right_html
                st.session_state["audit_gap_client_json_raw"] = client_json
            except Exception as e:  # pragma: no cover - robustesse réseau / parsing
                st.error(f"Erreur lors de l'audit JSON-LD: {e}")

    client_html = st.session_state.get("audit_gap_client_html")
    hotaru_html = st.session_state.get("audit_gap_hotaru_html")

    if client_html and hotaru_html:
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown(
                '<div class="label-caps">JSON-LD / SITE CLIENT</div>',
                unsafe_allow_html=True,
            )
            st.markdown(client_html, unsafe_allow_html=True)

        with col_right:
            st.markdown(
                '<div class="label-caps">JSON-LD / HOTARU MASTER</div>',
                unsafe_allow_html=True,
            )
            st.markdown(hotaru_html, unsafe_allow_html=True)

        # Bouton pour utiliser le JSON-LD client afin de compléter MASTER
        if st.button(
            "UTILISER LE JSON-LD CLIENT POUR REMPLIR MASTER",
            use_container_width=True,
            key="hydrate_master_from_client_jsonld",
        ):
            raw_client_json = st.session_state.get("audit_gap_client_json_raw", "")
            if not raw_client_json:
                st.error("Aucun JSON-LD client en mémoire. Relancez l'extraction.")
            else:
                try:
                    org_fields = extract_org_fields_from_jsonld(raw_client_json)
                    if not org_fields:
                        st.error(
                            "Aucun noeud Organization trouvé dans le JSON-LD client."
                        )
                    else:
                        if not st.session_state.master_data:
                            st.session_state.master_data = MasterData()
                        updated = hydrate_master_from_org(
                            st.session_state.master_data, org_fields
                        )
                        if updated:
                            st.success(
                                "Champs mis à jour depuis le JSON-LD client : "
                                + ", ".join(updated)
                            )
                            st.rerun()
                        else:
                            st.info(
                                "Aucun champ MASTER n'a été mis à jour (déjà remplis ou valeurs vides)."
                            )
                except Exception as e:  # pragma: no cover
                    st.error(f"Erreur lors de l'hydratation MASTER: {e}")

    st.markdown("</div>", unsafe_allow_html=True)