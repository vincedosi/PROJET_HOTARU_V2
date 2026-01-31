"""
HOTARU V3 - APPLICATION SAAS (v0.9.8 - DEMO READY)
Navigation: Top Bar
Feature: Structure Zen + Switch GEO Score IA
"""

import streamlit as st
import os

# --- 1. CONFIGURATION GLOBALE ---
st.set_page_config(
    page_title="HOTARU",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS ---
def load_css(file_name):
    try:
        with open(file_name, "r") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

# --- 3. HEADER ---
def render_header():
    col_logo, col_nav = st.columns([1, 4])
    with col_logo:
        st.markdown("""
            <div style="padding-top: 10px;">
                <h2 style="margin:0; font-size:1.8rem; color:black; font-weight:700;">
                    <span style="color:#FFD700;">●</span> HOTARU
                </h2>
            </div>
        """, unsafe_allow_html=True)

    with col_nav:
        options = ["📊 Dashboard", "🔍 Audit GEO", "📄 Rapports", "⚙️ Config"]
        current_index = 0
        if "active_tab" in st.session_state and st.session_state.active_tab in options:
            current_index = options.index(st.session_state.active_tab)

        selected = st.radio(
            "Navigation",
            options,
            index=current_index,
            horizontal=True,
            label_visibility="collapsed",
            key="top_nav_bar"
        )
    st.markdown("---") 
    return selected

# --- 4. LOGIN ---
def render_login():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>Connexion</h1>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("Email", value="demo@hotaru.app")
            password = st.text_input("Mot de passe", type="password", value="demo")
            submit = st.form_submit_button("Entrer", use_container_width=True)
            
            if submit:
                if email and password:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.active_tab = "🔍 Audit GEO"
                    st.rerun()
                else:
                    st.error("Veuillez remplir les champs.")

# --- 5. MAIN ---
def main():
    load_css("assets/style.css")

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "🔍 Audit GEO"

    if not st.session_state.authenticated:
        render_login()
    else:
        selected_page = render_header()
        st.session_state.active_tab = selected_page

        if selected_page == "📊 Dashboard":
            from modules.dashboard import render_dashboard
            render_dashboard()

        elif selected_page == "🔍 Audit GEO":
            from modules.audit_geo import render_audit_geo
            render_audit_geo()

        elif selected_page == "📄 Rapports":
            st.title("Mes Rapports")
            st.info("Historique complet des audits sauvegardés.")

        elif selected_page == "⚙️ Config":
            st.subheader("Configuration")
            if st.button("Se déconnecter"):
                st.session_state.authenticated = False
                st.rerun()

if __name__ == "__main__":
    main()
