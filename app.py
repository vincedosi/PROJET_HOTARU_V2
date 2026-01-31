"""
HOTARU V3 - APPLICATION SAAS (v0.9.0)
Navigation: Top Bar (Onglets Horizontaux)
Design: Zen Minimaliste
"""

import streamlit as st
import os

# --- 1. CONFIGURATION GLOBALE (OBLIGATOIRE EN PREMIER) ---
st.set_page_config(
    page_title="HOTARU",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"  # On cache la sidebar native
)

# --- 2. FONCTION DE CHARGEMENT CSS ---
def load_css(file_name):
    """Charge le fichier CSS externe depuis le dossier assets."""
    try:
        with open(file_name, "r") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        # Avertissement discret si le fichier manque, mais ne bloque pas l'app
        st.warning(f"⚠️ Fichier de style introuvable : {file_name}")

# --- 3. COMPOSANT HEADER (LOGO + MENU) ---
def render_header():
    """Affiche le logo et le menu de navigation horizontal."""
    
    # Structure : Logo à gauche (1), Menu à droite (4)
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
        # Liste des onglets
        options = ["📊 Dashboard", "🔍 Audit GEO", "📄 Rapports", "⚙️ Config"]
        
        # Gestion de l'état actif (Persistance)
        current_index = 0
        if "active_tab" in st.session_state and st.session_state.active_tab in options:
            current_index = options.index(st.session_state.active_tab)

        # Menu Radio Horizontal (Le coeur de la navigation)
        selected = st.radio(
            "Navigation",
            options,
            index=current_index,
            horizontal=True,
            label_visibility="collapsed",
            key="top_nav_bar"
        )
        
    st.markdown("---") # Séparateur fin
    return selected

# --- 4. PAGE DE LOGIN ---
def render_login():
    """Affiche le formulaire de connexion."""
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>Connexion</h1>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("Email", value="demo@hotaru.app")
            password = st.text_input("Mot de passe", type="password", value="demo")
            submit = st.form_submit_button("Entrer", use_container_width=True)
            
            if submit:
                # Simulation Auth (A connecter à une vraie BDD plus tard)
                if email and password:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.active_tab = "📊 Dashboard" # Redirection vers Dashboard
                    st.rerun()
                else:
                    st.error("Veuillez remplir les champs.")

# --- 5. ROUTEUR PRINCIPAL ---
def main():
    # 1. Charger le design
    load_css("assets/style.css")

    # 2. Initialiser la Session
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "📊 Dashboard"

    # 3. Logique de Routage
    if not st.session_state.authenticated:
        render_login()
    else:
        # A. Afficher le Header (Toujours visible)
        selected_page = render_header()
        st.session_state.active_tab = selected_page

        # B. Charger le Module correspondant
        if selected_page == "📊 Dashboard":
            # On appelle le nouveau module Dashboard
            from modules.dashboard import render_dashboard
            render_dashboard()

        elif selected_page == "🔍 Audit GEO":
            # On appelle le module Audit (Scraping + Graph)
            # Pas de try/except ici : on veut voir l'erreur si ça plante !
            from modules.audit_geo import render_audit_geo
            render_audit_geo()

        elif selected_page == "📄 Rapports":
            st.title("Mes Rapports")
            st.info("Historique complet des audits sauvegardés (À venir).")

        elif selected_page == "⚙️ Config":
            st.subheader("Configuration")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Clé API Mistral (IA)")
                key = st.text_input("API Key", type="password", key="api_key_input")
                if st.button("Sauvegarder la clé"):
                    st.session_state.mistral_api_key = key
                    st.success("Clé enregistrée !")
            with c2:
                st.caption("Compte Utilisateur")
                st.write(f"Connecté : **{st.session_state.user_email}**")
                if st.button("Se déconnecter"):
                    st.session_state.authenticated = False
                    st.rerun()

if __name__ == "__main__":
    main()
