"""
HOTARU v2 - Main Application Router
The AI-Readable Web - GEO Audit & JSON-LD Generator
"""

import base64
import os

import streamlit as st

from version import BUILD_DATE, VERSION
from core.auth import AuthManager
from core.database import AuditDatabase
from core.i18n import get_current_lang, set_lang, t
from core.session_keys import (
    SESSION_AUTHENTICATED,
    SESSION_USER_EMAIL,
    get_current_user_email,
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

def get_render_leaf_tab():
    from modules.jsonld import render_leaf_tab
    return render_leaf_tab

def get_render_jsonld_analyzer_tab():
    from modules.jsonld import render_jsonld_analyzer_tab
    return render_jsonld_analyzer_tab

def get_render_eco_tab():
    from modules.eco import render_eco_tab
    return render_eco_tab


# =============================================================================
# CACHED DATABASE ACCESS
# =============================================================================
def get_cached_database():
    """Retourne AuditDatabase cachée dans session_state."""
    if "db_instance" not in st.session_state:
        st.session_state.db_instance = AuditDatabase()
    return st.session_state.db_instance


# =============================================================================
# MAIN
# =============================================================================
def main():
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
                email = st.text_input("EMAIL", placeholder="admin@hotaru.com")
                password = st.text_input("PASSWORD", type="password")
                submit = st.form_submit_button(t("login"), use_container_width=True)

                if submit:
                    auth = AuthManager()
                    if auth.login(email, password):
                        st.session_state[SESSION_AUTHENTICATED] = True
                        st.session_state[SESSION_USER_EMAIL] = email
                        st.rerun()
                    else:
                        st.error(t("login.error"))
        return

    # HEADER (logo + version + langue FR/EN)
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
    col_logo, col_ver, col_fr, col_en = st.columns([4, 2, 1, 1])
    with col_logo:
        st.markdown(
            f'<div class="hotaru-header-left">{header_left}</div>',
            unsafe_allow_html=True,
        )
    with col_ver:
        st.markdown(
            f'<div class="hotaru-header-right"><span class="hotaru-header-version">V {VERSION} // {BUILD_DATE}</span></div>',
            unsafe_allow_html=True,
        )
    lang = get_current_lang()
    with col_fr:
        if st.button("🇫🇷", key="lang_fr", help="Français", type="primary" if lang == "fr" else "secondary"):
            set_lang("fr")
            st.rerun()
    with col_en:
        if st.button("🇬🇧", key="lang_en", help="English", type="primary" if lang == "en" else "secondary"):
            set_lang("en")
            st.rerun()
    st.markdown('<div class="hotaru-header-divider"></div>', unsafe_allow_html=True)

    # Workspace (niveau LOGOUT) + LOGOUT
    db = get_cached_database()
    all_audits = db.load_user_audits(get_current_user_email() or "")
    uncat = t("workspace.uncategorized")
    def _norm_ws(w):
        s = str(w or "").strip()
        return uncat if not s or s in ("Non classé", "Uncategorized") else s
    ws_set = {_norm_ws(a.get("workspace")) for a in all_audits}
    ws_list = [t("workspace.new")] if not ws_set else sorted(ws_set) + [t("workspace.create")]
    c_ws, c_user = st.columns([2, 1])
    with c_ws:
        st.selectbox(
            t("workspace.label"),
            ws_list,
            key="audit_workspace_select",
            label_visibility="collapsed",
            help=t("workspace.help"),
        )
    with c_user:
        if st.button(t("logout"), use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # NAVIGATION — 4 onglets (Master et Leaf sont DANS JSON-LD)
    tab_home, tab_audit, tab_jsonld, tab_eco = st.tabs([
        t("nav.home"),
        t("nav.audit"),
        t("nav.jsonld"),
        t("nav.eco"),
    ])

    with tab_home:
        render_home = get_render_home()
        render_home()

    with tab_audit:
        sub_tab_geo, sub_tab_authority, sub_tab_scraping = st.tabs(
            [t("nav.audit_geo"), t("nav.authority"), t("nav.scraping")]
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
        sub_master, sub_leaf, sub_analyzer = st.tabs([
            t("nav.master"),
            t("nav.leaf"),
            t("nav.jsonld_analysis"),
        ])
        with sub_master:
            render_master_tab = get_render_master_tab()
            render_master_tab()
        with sub_leaf:
            render_leaf_tab = get_render_leaf_tab()
            render_leaf_tab()
        with sub_analyzer:
            render_jsonld_analyzer_tab = get_render_jsonld_analyzer_tab()
            render_jsonld_analyzer_tab()

    with tab_eco:
        render_eco_tab = get_render_eco_tab()
        render_eco_tab()

    # FOOTER
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
