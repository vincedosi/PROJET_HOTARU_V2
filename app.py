"""
HOTARU - Main Application (v0.9.9)
Système de Navigation SaaS avec Gestion des Rôles
"""

import streamlit as st
from modules.audit_geo import render_audit_geo

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="HOTARU | Stratégie GEO",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. GESTION DU LOGIN & DES RÔLES ---
def check_auth():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_role = "user"

    if not st.session_state.authenticated:
        render_login()
        st.stop()

def render_login():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>Connexion HOTARU</h1>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("Email Professionnel", value="admin@hotaru.app")
            password = st.text_input("Mot de passe", type="password", value="demo")
            submit = st.form_submit_button("Se connecter", use_container_width=True)
            
            if submit:
                # --- LOGIQUE ADMIN ---
                # Ajoute ton email ici pour avoir les droits Admin
                admins = ["admin@hotaru.app", "vincent.sidoli@gmail.com"]
                
                st.session_state.authenticated = True
                st.session_state.user_email = email
                
                if email in admins:
                    st.session_state.user_role = "admin"
                else:
                    st.session_state.user_role = "user"
                
                st.rerun()

# --- 3. HEADER DE NAVIGATION ---
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
        # On définit les onglets disponibles
        tabs = ["📊 Dashboard", "🔍 Audit GEO", "📄 Rapports", "⚙️ Config"]
        
        # On récupère l'onglet actif ou on met l'Audit par défaut
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "🔍 Audit GEO"
            
        current_index = tabs.index(st.session_state.active_tab)

        selected = st.radio(
            "Navigation",
            tabs,
            index=current_index,
            horizontal=True,
            label_visibility="collapsed",
            key="main_nav"
        )
        st.session_state.active_tab = selected
    
    st.markdown("---")

# --- 4. CORPS DE L'APPLICATION ---
def main():
    check_auth()
    render_header()
    
    # Navigation vers les modules
    page = st.session_state.active_tab

    if page == "📊 Dashboard":
        st.title("Tableau de bord")
        st.info("Statistiques globales des audits en cours.")
        # Futur : from modules.dashboard import render_dashboard

    elif page == "🔍 Audit GEO":
        # On appelle le module d'audit que nous avons mis à jour
        render_audit_geo()

    elif page == "📄 Rapports":
        st.title("Rapports & Exports")
        st.write(f"Connecté en tant que : **{st.session_state.user_role.upper()}**")
        st.info("Génération de rapports PDF et exports CSV.")

    elif page == "⚙️ Config":
        st.subheader("Paramètres du compte")
        st.write(f"Email : {st.session_state.user_email}")
        st.write(f"Droits : {st.session_state.user_role}")
        
        if st.button("Se déconnecter", type="secondary"):
            st.session_state.authenticated = False
            st.rerun()

if __name__ == "__main__":
    main()
