"""
HOTARU v2 - Main Application Router
The AI-Readable Web - GEO Audit & JSON-LD Generator
"""

import os
import streamlit as st

from core.auth import AuthManager
from modules.home import render_home
from modules.audit_geo import render_audit_geo
from modules.master import render_master_tab
from modules.leaf import render_leaf_tab

# =============================================================================
# VERSION
# =============================================================================
VERSION = "3.0.0"
BUILD_DATE = "2026-02-06"

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

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # LOGIN
    if not st.session_state.authenticated:
        _, col_login, _ = st.columns([1, 1.2, 1])
        with col_login:
            st.markdown("<div style='padding-top: 80px;'></div>", unsafe_allow_html=True)
            if os.path.exists("assets/logo.png"):
                st.image("assets/logo.png", use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)

            with st.form("login_form"):
                email = st.text_input("EMAIL", placeholder="admin@hotaru.com")
                password = st.text_input("PASSWORD", type="password")
                submit = st.form_submit_button("LOGIN", use_container_width=True)

                if submit:
                    auth = AuthManager()
                    if auth.login(email, password):
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
        return

    # HEADER
    c_logo, c_version, _, c_user = st.columns([2, 2, 3, 1])
    with c_logo:
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=140)
    with c_version:
        st.markdown(
            f"<div style='padding-top: 15px; color: #64748b; font-size: 0.85rem;'>"
            f"v{VERSION} | {BUILD_DATE}</div>",
            unsafe_allow_html=True,
        )
    with c_user:
        if st.button("LOGOUT", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # NAVIGATION
    tab_home, tab_audit, tab_master, tab_leaf = st.tabs(
        ["HOME", "AUDIT", "MASTER", "LEAF"]
    )

    with tab_home:
        render_home()

    with tab_audit:
        render_audit_geo()

    with tab_master:
        render_master_tab()

    with tab_leaf:
        render_leaf_tab()

    # FOOTER
    st.divider()
    st.caption(f"Hotaru Strategic v{VERSION} | {BUILD_DATE}")


if __name__ == "__main__":
    main()
