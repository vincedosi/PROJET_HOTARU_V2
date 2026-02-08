"""
HOTARU v2 - Main Application Router
The AI-Readable Web - GEO Audit & JSON-LD Generator
"""

import os
import streamlit as st

from core.auth import AuthManager
from core.session_keys import (
    SESSION_AUTHENTICATED,
    SESSION_USER_EMAIL,
    SESSION_USER_ROLE,
    ROLE_USER,
)
from modules.home import render_home
from modules.audit_geo import render_audit_geo
from modules.authority_score import render_authority_score
from modules.master import render_master_tab
from modules.leaf import render_leaf_tab

# =============================================================================
# VERSION
# =============================================================================
VERSION = "3.0.1"
BUILD_DATE = "2026-02-08"

# =============================================================================
# CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="Hotaru Strategic",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_styles():
    css_path = "assets/style.css"
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


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
            st.markdown(
                '<div style="display:flex;align-items:center;gap:12px;margin-bottom:32px;">'
                '<div class="hotaru-header-logo">H</div>'
                '<span class="hotaru-header-brand">HOTARU</span>'
                '</div>',
                unsafe_allow_html=True,
            )

            with st.form("login_form"):
                email = st.text_input("EMAIL", placeholder="admin@hotaru.com")
                password = st.text_input("PASSWORD", type="password")
                submit = st.form_submit_button("LOGIN", use_container_width=True)

                if submit:
                    auth = AuthManager()
                    if auth.login(email, password):
                        st.session_state[SESSION_AUTHENTICATED] = True
                        st.session_state[SESSION_USER_EMAIL] = email
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
        return

    # HEADER
    st.markdown(
        f'<div class="hotaru-header">'
        f'<div class="hotaru-header-left">'
        f'<div class="hotaru-header-logo">H</div>'
        f'<span class="hotaru-header-brand">HOTARU</span>'
        f'</div>'
        f'<div class="hotaru-header-right">'
        f'<span class="hotaru-header-version">V {VERSION} // {BUILD_DATE}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    c_spacer, c_user = st.columns([6, 1])
    with c_user:
        if st.button("LOGOUT", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # NAVIGATION
    tab_home, tab_audit, tab_authority, tab_master, tab_leaf = st.tabs(
        ["Home", "Audit", "Authority Score", "Master", "Leaf"]
    )

    with tab_home:
        render_home()

    with tab_audit:
        render_audit_geo()

    with tab_authority:
        render_authority_score()

    with tab_master:
        render_master_tab()

    with tab_leaf:
        render_leaf_tab()

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
