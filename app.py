"""
HOTARU V3 - APPLICATION SAAS
Navigation: Top Bar (Onglets Horizontaux)
Design: Zen Minimaliste (Blanc/Noir)
"""

import streamlit as st
import os

# --- 1. CONFIGURATION GLOBALE (OBLIGATOIRE EN PREMIER) ---
st.set_page_config(
    page_title="HOTARU",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"  # On cache volontairement la sidebar
)

# --- 2. FONCTION DE CHARGEMENT CSS ---
def load_css(file_name):
    """Charge le fichier CSS externe depuis le dossier assets."""
    try:
        with open(file_name, "r") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"⚠️ Fichier CSS introuvable : {file_name}")
        st.warning("Assurez-vous que le fichier 'style.css' est bien dans le dossier 'assets/'.")

# --- 3. COMPOSANT HEADER (LOGO + MENU) ---
def render_header():
    """Affiche le logo et le menu de navigation horizontal."""
    
    # Création des colonnes pour aligner Logo (Gauche) et Menu (Droite/Centre)
    col_logo, col_nav = st.columns([1, 4])
    
    with col_logo:
        # Logo Texte Zen
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
        
        # Récupération de l'onglet actif
        current_index = 0
        if "active_tab" in st.session_state and st.session_state.active_tab in options:
            current_index = options.index(st.session_state.active_tab)

        # Menu Horizontal (Plus robuste que la sidebar)
        selected = st.radio(
            "Navigation",
            options,
            index=current_index,
            horizontal=True,
            label_visibility="collapsed",
            key="top_nav_bar"
        )
        
    st.markdown("---") # Ligne de séparation fine sous le menu
    return selected

# --- 4. PAGE DE LOGIN ---
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
                # Simulation Auth (A connecter à ton AuthManager plus tard)
                if email and password:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.active_tab = "🔍 Audit GEO"
                    st.rerun()
                else:
                    st.error("Veuillez remplir les champs.")

# --- 5. ROUTEUR PRINCIPAL ---
def main():
    # Chargement du CSS externe
    load_css("assets/style.css")

    # Initialisation des États
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "🔍 Audit GEO"

    # LOGIQUE D'AFFICHAGE
    if not st.session_state.authenticated:
        render_login()
    else:
        # 1. AFFICHER LE HEADER (Toujours visible)
        selected_page = render_header()
        st.session_state.active_tab = selected_page

        # 2. AFFICHER LE CONTENU
        if selected_page == "📊 Dashboard":
            st.title("Tableau de bord")
            st.info("🚧 Module en construction. Cliquez sur 'Audit GEO'.")

        elif selected_page == "🔍 Audit GEO":
            # Import dynamique (pour éviter les erreurs si le fichier est cassé)
            try:
                from modules.audit_geo import render_audit_geo
                render_audit_geo()
            except ImportError:
                st.error("⚠️ Fichier 'modules/audit_geo.py' introuvable.")
                st.info("Demande à Claude de générer le module d'audit.")
            except Exception as e:
                st.error(f"Erreur dans le module Audit : {e}")

        elif selected_page == "📄 Rapports":
            st.title("Mes Rapports")
            st.write("Historique des audits sauvegardés.")

        elif selected_page == "⚙️ Config":
            st.subheader("Configuration")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Clé API Mistral")
                key = st.text_input("API Key", type="password", key="api_key_input")
                if st.button("Sauvegarder"):
                    st.session_state.mistral_api_key = key
                    st.success("Clé enregistrée !")
            with c2:
                st.caption("Session")
                if st.button("Se déconnecter"):
                    st.session_state.authenticated = False
                    st.rerun()

if __name__ == "__main__":
    main()
