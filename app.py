"""
HOTARU v2 - Main Application Router
The AI-Readable Web - GEO Audit & JSON-LD Generator
"""

import subprocess
import sys

# Auto-install Playwright Chromium si absent (ex. Streamlit Cloud)
subprocess.run(
    [sys.executable, "-m", "playwright", "install", "chromium"],
    capture_output=True,
    check=False,
)

import base64
import os

import streamlit as st

from version import BUILD_DATE, VERSION
from core.runtime import init as core_init, get_secrets
from core.session_keys import (
    SESSION_AUTHENTICATED,
    SESSION_USER_EMAIL,
    get_current_user_email,
    is_admin,
)

# VERSION et BUILD_DATE : définis dans version.py (mis à jour à chaque push/PR)

# =============================================================================
# CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="Hotaru Strategic",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def load_styles():
    css_path = "assets/style.css"
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_resource
def get_logo_base64():
    """Logo pour le header (assets/logo.png) en base64."""
    path = "assets/logo.png"
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# =============================================================================
# LAZY LOADING MODULE RENDERERS
# =============================================================================
def get_render_home():
    from modules.home import render_home
    return render_home

def get_render_audit_geo():
    from modules.audit import render_audit_geo
    return render_audit_geo

def get_render_authority_score():
    from modules.audit import render_authority_score
    return render_authority_score

def get_render_scraping_debug_tab():
    from modules.audit import render_scraping_debug_tab
    return render_scraping_debug_tab

def get_render_master_tab():
    from modules.jsonld import render_master_tab
    return render_master_tab

def get_render_jsonld_analyzer_tab():
    from modules.jsonld import render_jsonld_analyzer_tab
    return render_jsonld_analyzer_tab

def get_render_master_tab_for_jsonld():
    from modules.jsonld import render_master_tab_for_jsonld
    return render_master_tab_for_jsonld

def get_render_jsonld_fusion_intelligente():
    from modules.jsonld import render_jsonld_fusion_intelligente
    return render_jsonld_fusion_intelligente

def get_render_eco_tab():
    from modules.eco import render_eco_tab
    return render_eco_tab


# =============================================================================
# CACHED DATABASE ACCESS
# =============================================================================
def get_cached_database():
    """Retourne AuditDatabase selon le choix fait à la connexion (Google Sheets ou Supabase)."""
    backend = st.session_state.get("auth_backend", "sheets")
    if "db_instance" not in st.session_state or st.session_state.get("db_backend") != backend:
        if backend == "supabase":
            from core.database_supabase import AuditDatabase
        else:
            from core.database import AuditDatabase
        st.session_state.db_instance = AuditDatabase()
        st.session_state.db_backend = backend
    return st.session_state.db_instance


def get_cached_auth():
    """Retourne AuthManager (Sheets ou Supabase) pour le backoffice."""
    backend = st.session_state.get("auth_backend", "sheets")
    if backend == "supabase":
        from core.auth_supabase import AuthManager
    else:
        from core.auth import AuthManager
    return AuthManager()


# =============================================================================
# GLOBAL SAVE (barre SaaS — bouton SAUVEGARDER)
# =============================================================================
# Clés conservées pour l'audit (sans html_content) afin de tenir dans les cellules GSheet (~90k).
_LIGHT_PAGE_KEYS = (
    "url", "title", "description", "h1", "h2_count", "has_structured_data",
    "response_time", "last_modified",
)


def _light_page(p):
    """Une page allégée pour la sauvegarde (graphe + journal + score partiel)."""
    if not isinstance(p, dict):
        return p
    out = {}
    for k in _LIGHT_PAGE_KEYS:
        if k not in p:
            continue
        v = p[k]
        if k in ("description", "h1") and isinstance(v, str) and len(v) > 400:
            v = v[:400]
        if k == "title" and isinstance(v, str) and len(v) > 300:
            v = v[:300]
        out[k] = v
    return out


def _do_global_save(session_state, db, user_email: str, workspace: str):
    """Sauvegarde l'état courant (audit GEO et/ou JSON-LD) dans unified_saves (Sheets ou Supabase)."""
    if not getattr(db, "sheet_file", None) and not getattr(db, "client", None):
        st.error("Connexion indisponible (vérifiez Google Sheet ou Supabase).")
        return
    target_url = (session_state.get("target_url") or "").strip()
    results = session_state.get("results") or []
    clusters = session_state.get("clusters") or []
    nom_site = (session_state.get("target_url") or "Site").replace("https://", "").replace("http://", "").split("/")[0][:200] or "Site"
    if not target_url:
        st.warning("Aucune URL de site en mémoire. Lancez un audit ou chargez une sauvegarde puis VALIDER.")
        return
    # Version allégée pour tenir dans les cellules GSheet (~90k) — sinon JSON tronqué au rechargement.
    max_saved = 180
    crawl_data = [_light_page(p) for p in (results[:max_saved] if results else [])]
    clusters_light = []
    for c in clusters:
        if isinstance(c, dict):
            samples = (c.get("samples") or [])[:50]
            clusters_light.append({
                "name": (c.get("name") or "")[:80],
                "count": c.get("count", len(samples)),
                "samples": [_light_page(p) for p in samples],
            })
        else:
            clusters_light.append(c)
    geo_data = {
        "clusters": clusters_light,
        "geo_infra": session_state.get("geo_infra", {}),
        "geo_score": session_state.get("geo_score", 0),
        "stats": session_state.get("crawl_stats", {}),
        "start_urls": session_state.get("start_urls", [target_url])[:5],
        "ai_accessibility": session_state.get("ai_accessibility", {}),
        "filtered_log": session_state.get("filtered_log", []),
        "duplicate_log": session_state.get("duplicate_log", []),
        "graph_show_ai_score": session_state.get("geo_graph_ai_toggle", False),
        "geo_ai_report": session_state.get("geo_ai_report", ""),
        "mistral_robots_raw": session_state.get("geo_robots_txt_raw", ""),
        "mistral_robots_found": session_state.get("geo_robots_txt_found", False),
        "mistral_robots_code": session_state.get("mistral_robots_code", ""),
        "mistral_robots_analysis": session_state.get("mistral_robots_analysis", ""),
        "mistral_llms_raw": session_state.get("geo_llms_txt_raw", ""),
        "mistral_llms_found": session_state.get("geo_llms_txt_found", False),
        "mistral_llms_code": session_state.get("mistral_llms_code", ""),
    }
    jsonld_data = None
    if session_state.get("jsonld_analyzer_results"):
        from services.jsonld_diff import extract_modified_fields
        num_clusters = len(session_state["jsonld_analyzer_results"].get("cluster_labels", []))
        models_data = []
        for i in range(num_clusters):
            opt = session_state.get(f"optimized_jsonld_{i}")
            validated = session_state.get(f"jsonld_validated_{i}", False)
            labels = session_state["jsonld_analyzer_results"].get("cluster_labels", [])
            urls = session_state["jsonld_analyzer_results"].get("cluster_urls", [])
            dom = session_state["jsonld_analyzer_results"].get("cluster_dom_structures", [])
            jld = session_state["jsonld_analyzer_results"].get("cluster_jsonld", [])
            label = labels[i] if i < len(labels) else {}
            existing = jld[i] if i < len(jld) else None
            delta = extract_modified_fields(existing, opt) if opt else None
            models_data.append({
                "model_name": label.get("model_name", "Cluster"),
                "schema_type": label.get("schema_type", "WebPage"),
                "page_count": len(urls[i]) if i < len(urls) else 0,
                "sample_urls": urls[i] if i < len(urls) else [],
                "dom_structure": dom[i] if i < len(dom) else {},
                "existing_jsonld": existing,
                "optimized_jsonld": opt,
                "optimized_jsonld_delta": delta,
                "validated": validated,
            })
        if models_data:
            jsonld_data = models_data
    master_json = (session_state.get("jsonld_master") or "").strip() or None
    master_data_obj = session_state.get("master_data")
    if master_data_obj is not None:
        try:
            from dataclasses import asdict
            master_data_dict = asdict(master_data_obj)
            import json as _json
            geo_data["master_data_serialized"] = _json.dumps(master_data_dict, ensure_ascii=False, default=str)
        except Exception:
            pass
    try:
        db.save_unified(
            user_email,
            workspace or "Non classé",
            target_url,
            nom_site,
            crawl_data=crawl_data,
            geo_data=geo_data,
            jsonld_data=jsonld_data,
            master_json=master_json,
        )
        st.toast("Sauvegarde enregistrée dans unified_saves.")
        from core.runtime import get_session
        s = get_session()
        s["audit_cache_version"] = s.get("audit_cache_version", 0) + 1
    except Exception as e:
        st.error("Erreur lors de la sauvegarde: " + str(e)[:150])


# =============================================================================
# MAIN
# =============================================================================
def _secrets_to_dict(s):
    """Convertit st.secrets en dict pour core (agnostique Streamlit)."""
    if s is None:
        return {}
    try:
        d = {}
        for k in s.keys():
            try:
                v = s[k]
                d[k] = _secrets_to_dict(v) if hasattr(v, "keys") and not isinstance(v, str) else v
            except Exception:
                pass
        return d
    except Exception:
        return {}


def main():
    core_init(secrets=_secrets_to_dict(st.secrets), session=st.session_state)
    load_styles()

    if SESSION_AUTHENTICATED not in st.session_state:
        st.session_state[SESSION_AUTHENTICATED] = False

    # LOGIN
    if not st.session_state[SESSION_AUTHENTICATED]:
        _, col_login, _ = st.columns([1, 1.2, 1])
        with col_login:
            st.markdown("<div style='padding-top: 80px;'></div>", unsafe_allow_html=True)
            logo_b64 = get_logo_base64()
            if logo_b64:
                st.markdown(
                    '<div class="hotaru-header-left" style="margin-bottom:32px;">'
                    f'<img src="data:image/png;base64,{logo_b64}" class="hotaru-header-logo-img" alt="Hotaru" />'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="hotaru-header-left" style="margin-bottom:32px;">'
                    '<span class="hotaru-header-brand">HOTARU</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )

            with st.form("login_form"):
                # Choix du mode de connexion (Google Sheets ou Supabase)
                connexion_avec = st.radio(
                    "Connexion avec",
                    options=["Google Sheets", "Supabase"],
                    index=0,
                    key="login_backend",
                    horizontal=True,
                    label_visibility="visible",
                )
                backend = "supabase" if connexion_avec == "Supabase" else "sheets"
                email = st.text_input("EMAIL", placeholder="admin@hotaru.com")
                password = st.text_input("PASSWORD", type="password")
                submit = st.form_submit_button("CONNEXION", use_container_width=True)

                if submit:
                    with st.spinner("Connexion en cours..."):
                        try:
                            if backend == "supabase":
                                from core.auth_supabase import AuthManager
                            else:
                                from core.auth import AuthManager
                            auth = AuthManager()
                            if auth.login(email, password):
                                st.session_state[SESSION_AUTHENTICATED] = True
                                st.session_state[SESSION_USER_EMAIL] = email
                                st.session_state["auth_backend"] = backend
                                st.rerun()
                            else:
                                st.error("Identifiants invalides.")
                        except Exception as e:
                            st.error(str(e))
        return

    # HEADER (logo + version)
    logo_b64 = get_logo_base64()
    if logo_b64:
        header_left = (
            f'<img src="data:image/png;base64,{logo_b64}" class="hotaru-header-logo-img" alt="Hotaru" />'
        )
    else:
        header_left = (
            '<div class="hotaru-header-logo">H</div>'
            '<span class="hotaru-header-brand">HOTARU</span>'
        )
    st.markdown(
        f'<div class="hotaru-header-left">{header_left}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="hotaru-header-divider"></div>', unsafe_allow_html=True)

    # ========== BARRE SAAS : Workspace + Sauvegarde (Valider) + Sauvegarder + Déconnexion ==========
    user_email = get_current_user_email() or ""
    db = get_cached_database()
    # Sur Streamlit Cloud la session peut perdre auth_backend : si on a un user mais pas de client Supabase et pas de sheet, forcer Supabase si configuré
    if user_email and not getattr(db, "client", None) and not getattr(db, "sheet_file", None):
        supabase = get_secrets().get("supabase") or {}
        if (supabase.get("supabase_url") or get_secrets().get("supabase_url")) and (supabase.get("supabase_service_role_key") or supabase.get("supabase_key") or get_secrets().get("supabase_service_role_key") or get_secrets().get("supabase_key")):
            if "db_instance" in st.session_state:
                del st.session_state["db_instance"]
            if "db_backend" in st.session_state:
                del st.session_state["db_backend"]
            st.session_state["auth_backend"] = "supabase"
            db = get_cached_database()

    def _norm_ws(w):
        s = str(w or "").strip()
        return "Non classé" if not s or s in ("Non classé", "Uncategorized") else s

    unified_list = []
    if getattr(db, "sheet_file", None) or getattr(db, "client", None):
        unified_list = db.list_unified_saves(user_email, workspace=None) or []
        if not is_admin() and hasattr(db, "get_user_workspaces"):
            allowed = db.get_user_workspaces(user_email)
            if allowed:
                allowed_set = {_norm_ws(x) for x in allowed}
                unified_list = [u for u in unified_list if _norm_ws(u.get("workspace")) in allowed_set]
    ws_set = {_norm_ws(u.get("workspace")) for u in unified_list}
    if hasattr(db, "list_all_workspaces"):
        try:
            for w in db.list_all_workspaces():
                ws_set.add(_norm_ws(w))
        except Exception:
            pass
    ws_set.discard("Non classé")
    ws_list = ["Nouveau"] if not ws_set else sorted(ws_set) + ["+ Créer Nouveau"]
    if st.session_state.get("audit_workspace_select") not in ws_list:
        st.session_state["audit_workspace_select"] = ws_list[0]
    selected_ws = st.session_state.get("audit_workspace_select", "Nouveau")
    if selected_ws in ("+ Créer Nouveau", "+ Creer Nouveau"):
        selected_ws = "Non classé"
    saves_in_ws = [u for u in unified_list if _norm_ws(u.get("workspace")) == selected_ws]
    save_options = ["— Aucune —"] + [
        f"{u.get('nom_site') or 'Sauvegarde'} ({u.get('created_at')})"
        for u in saves_in_ws
    ]
    save_to_id = {"— Aucune —": None}
    for u in saves_in_ws:
        label = f"{u.get('nom_site') or 'Sauvegarde'} ({u.get('created_at')})"
        save_to_id[label] = u.get("save_id")
    if st.session_state.get("header_save_select") not in save_options:
        st.session_state["header_save_select"] = save_options[0]

    row1_col_ws, row1_col_logout = st.columns([3, 1])
    with row1_col_ws:
        st.selectbox(
            "Choix du workspace",
            ws_list,
            key="audit_workspace_select",
            label_visibility="visible",
            help="Projet / workspace pour filtrer les sauvegardes.",
        )
    with row1_col_logout:
        if st.button("DÉCONNEXION", use_container_width=True, key="header_logout"):
            st.session_state.clear()
            st.rerun()

    row2_col_save, row2_valider, row2_sauvegarder = st.columns([3, 1, 1])
    with row2_col_save:
        st.selectbox(
            "Choix de la sauvegarde",
            save_options,
            key="header_save_select",
            label_visibility="visible",
            help="Sélectionnez une sauvegarde puis cliquez Valider pour la charger.",
        )
    with row2_valider:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        valider_clicked = st.button("VALIDER", use_container_width=True, type="primary", key="header_valider")
    with row2_sauvegarder:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        sauvegarder_clicked = st.button("SAUVEGARDER", use_container_width=True, key="header_sauvegarder")

    if valider_clicked:
        chosen_label = st.session_state.get("header_save_select", "— Aucune —")
        save_id = save_to_id.get(chosen_label)
        if save_id and user_email:
            loaded = db.load_unified(save_id, user_email)
            if loaded:
                selected_ws_loaded = loaded.get("workspace", selected_ws)
                crawl_data = loaded.get("crawl_data") or []
                geo_data = loaded.get("geo_data") or {}
                st.session_state.update({
                    "results": crawl_data,
                    "clusters": geo_data.get("clusters", []),
                    "target_url": loaded.get("site_url", ""),
                    "geo_infra": geo_data.get("geo_infra", {}),
                    "geo_score": geo_data.get("geo_score", 0),
                    "current_ws": selected_ws_loaded,
                    "crawl_stats": geo_data.get("stats", {}),
                    "filtered_log": geo_data.get("filtered_log", []),
                    "duplicate_log": geo_data.get("duplicate_log", []),
                    "ai_accessibility": geo_data.get("ai_accessibility", {}),
                    "start_urls": geo_data.get("start_urls", [loaded.get("site_url", "")]),
                    "geo_graph_ai_toggle": geo_data.get("graph_show_ai_score", False),
                    "geo_ai_report": geo_data.get("geo_ai_report", ""),
                    "geo_robots_txt_raw": geo_data.get("mistral_robots_raw", ""),
                    "geo_robots_txt_found": geo_data.get("mistral_robots_found", False),
                    "mistral_robots_code": geo_data.get("mistral_robots_code", ""),
                    "mistral_robots_analysis": geo_data.get("mistral_robots_analysis", ""),
                    "geo_llms_txt_raw": geo_data.get("mistral_llms_raw", ""),
                    "geo_llms_txt_found": geo_data.get("mistral_llms_found", False),
                    "mistral_llms_code": geo_data.get("mistral_llms_code", ""),
                })
                jsonld_data = loaded.get("jsonld_data") or []
                if jsonld_data:
                    try:
                        from urllib.parse import urlparse
                        site_url = loaded.get("site_url", "")
                        domain = urlparse(site_url).netloc or "site"
                        cluster_labels = []
                        cluster_urls = []
                        cluster_dom = []
                        cluster_jsonld = []
                        for m in jsonld_data:
                            cluster_labels.append({
                                "model_name": m.get("model_name") or "Cluster",
                                "schema_type": m.get("schema_type") or m.get("recommended_schema") or "WebPage",
                            })
                            urls = m.get("sample_urls") or []
                            cluster_urls.append(urls if isinstance(urls, list) else [])
                            cluster_dom.append(m.get("dom_structure") or {})
                            cluster_jsonld.append(m.get("existing_jsonld"))
                        st.session_state["jsonld_analyzer_results"] = {
                            "site_url": site_url, "domain": domain,
                            "total_pages": sum(m.get("page_count", 0) for m in jsonld_data),
                            "cluster_labels": cluster_labels, "cluster_urls": cluster_urls,
                            "cluster_dom_structures": cluster_dom, "cluster_jsonld": cluster_jsonld,
                            "logs": [], "loaded_from_sheet": True,
                        }
                        for k in list(st.session_state.keys()):
                            if k.startswith(("optimized_jsonld_", "jsonld_prompt_", "jsonld_validated_")):
                                del st.session_state[k]
                        for i, m in enumerate(jsonld_data):
                            opt = m.get("optimized_jsonld")
                            if opt is not None and isinstance(opt, dict):
                                st.session_state[f"optimized_jsonld_{i}"] = opt
                            if m.get("validated"):
                                st.session_state[f"jsonld_validated_{i}"] = True
                    except Exception as jld_err:
                        import logging
                        logging.getLogger(__name__).error("Erreur restauration JSON-LD: %s", jld_err, exc_info=True)
                        st.warning("JSON-LD partiellement restauré.")
                master_json_val = loaded.get("master_json") or ""
                if master_json_val:
                    st.session_state["jsonld_master"] = master_json_val
                master_data_ser = geo_data.get("master_data_serialized")
                if master_data_ser:
                    try:
                        import json as _json
                        from engine.master_handler import MasterData
                        md_dict = _json.loads(master_data_ser)
                        st.session_state["master_data"] = MasterData(**{
                            k: v for k, v in md_dict.items()
                            if k in MasterData.__dataclass_fields__
                        })
                    except Exception as md_err:
                        import logging
                        logging.getLogger(__name__).warning("Restauration master_data partielle: %s", md_err)
                if loaded.get("crawl_data"):
                    st.session_state["jsonld_analyzer_crawl_results"] = loaded["crawl_data"]
                st.session_state["global_loaded_save_id"] = save_id
                st.toast("Sauvegarde chargée.")
                st.rerun()
            else:
                st.error("Sauvegarde introuvable ou accès refusé.")
        else:
            st.info("Sélectionnez une sauvegarde dans la liste.")

    if sauvegarder_clicked:
        _do_global_save(st.session_state, db, user_email, selected_ws)

    st.markdown('<div class="hotaru-header-divider"></div>', unsafe_allow_html=True)

    # NAVIGATION — 4 onglets + Backoffice (admin uniquement)
    tab_names = ["Accueil", "Audit", "JSON-LD", "Eco-Score"]
    if is_admin():
        tab_names.append("Backoffice")
    all_tabs = st.tabs(tab_names)
    tab_home, tab_audit, tab_jsonld, tab_eco = all_tabs[0], all_tabs[1], all_tabs[2], all_tabs[3]

    with tab_home:
        render_home = get_render_home()
        render_home()

    with tab_audit:
        sub_tab_geo, sub_tab_authority, sub_tab_scraping = st.tabs(
            ["Audit GEO", "Authority Score", "Scraping"]
        )
        with sub_tab_geo:
            render_audit_geo = get_render_audit_geo()
            render_audit_geo()
        with sub_tab_authority:
            render_authority_score = get_render_authority_score()
            render_authority_score()
        with sub_tab_scraping:
            render_scraping_debug_tab = get_render_scraping_debug_tab()
            render_scraping_debug_tab()

    with tab_jsonld:
        sub_vue_ensemble, sub_master, sub_leaf = st.tabs([
            "VUE ENSEMBLE",
            "MASTER",
            "LEAF",
        ])
        with sub_vue_ensemble:
            render_jsonld_analyzer_tab = get_render_jsonld_analyzer_tab()
            render_jsonld_analyzer_tab()
        with sub_master:
            render_master_tab_for_jsonld = get_render_master_tab_for_jsonld()
            render_master_tab_for_jsonld()
        with sub_leaf:
            render_jsonld_fusion_intelligente = get_render_jsonld_fusion_intelligente()
            render_jsonld_fusion_intelligente()

    with tab_eco:
        render_eco_tab = get_render_eco_tab()
        render_eco_tab()

    if is_admin():
        with all_tabs[4]:
            from views.backoffice import render_backoffice_tab
            render_backoffice_tab(get_cached_auth(), get_cached_database())

    # FOOTER (BUILD = date/heure du push, dans version.py)
    st.markdown(
        f'<div class="hotaru-footer">'
        f'<span>HOTARU ENTITY FORGE V2</span>'
        f'<span>|</span>'
        f'<span>VERSION {VERSION}</span>'
        f'<span>|</span>'
        f'<span>BUILD {BUILD_DATE}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
