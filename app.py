"""
HOTARU - SaaS Application
Japanese Zen / Flat Design

Main router with persistent SaaS navigation sidebar.
FIX: Sidebar rendering structure and State Management.
"""

import streamlit as st

# --- 1. CONFIGURATION (DOIT IMPERATIVEMENT ÊTRE LA PREMIERE LIGNE) ---
st.set_page_config(
    page_title="HOTARU",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS ZEN (DESIGN SYSTEM) ---
def inject_custom_css():
    st.markdown("""
        <style>
        /* Force white background everywhere */
        .stApp, .main, [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
        }

        /* Sidebar styling - Blanc pur et bordure fine */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #e0e0e0;
        }
        
        /* Force text color to black in sidebar */
        section[data-testid="stSidebar"] * {
            color: #000000 !important;
        }

        /* Elements de navigation */
        div[data-testid="stRadio"] > label {
            font-size: 14px;
            padding: 10px 0;
            cursor: pointer;
            color: #000000 !important;
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Buttons Zen */
        .stButton > button {
            border: 1px solid #000000 !important;
            border-radius: 4px !important;
            background-color: #FFFFFF !important;
            color: #000000 !important;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            background-color: #f0f0f0 !important;
            border-color: #000000 !important;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 3. NAVIGATION ROBUSTE ---
def render_sidebar():
    """
    Render the sidebar and RETURN the selected page immediately.
    """
    with st.sidebar:
        # LOGO AREA
        st.markdown("""
            <div style="text-align: center; padding: 1rem 0; margin-bottom: 2rem;">
                <div style="font-size: 1.8rem; font-weight: 700; letter-spacing: 0.1em;">
                    <span style="color: #FFD700;">●</span> HOTARU
                </div>
                <div style="font-size: 0.7rem; color: #666; margin-top: 5px;">
                    蛍 · SEO Audit Suite
                </div>
            </div>
            <hr style="margin: 0 0 20px 0; border: none; border-bottom: 1px solid #eee;">
        """, unsafe_allow_html=True)

        # MENU NAVIGATION
        options = ["📊 Dashboard", "🔍 Audit GEO", "📄 Rapports", "⚙️ Parametres"]
        
        # Gestion de l'état actif
        default_index = 0
        if "active_tab" in st.session_state and st.session_state.active_tab in options:
            default_index = options.index(st.session_state.active_tab)

        # Widget de Navigation
        selected = st.radio(
            "Navigation",
            options,
            index=default_index,
            label_visibility="collapsed",
            key="nav_radio"
        )

        # API STATUS
        st.markdown("---")
        st.caption("🔐 API MISTRAL")
        if st.session_state.get('mistral_api_key'):
             st.success("Connecté", icon="🟢")
        else:
             st.warning("Non Configuré", icon="⚠️")

        # USER FOOTER
        st.markdown("---")
        if st.session_state.get('user_email'):
            st.caption(f"👤 {st.session_state.user_email}")
            if st.button("Déconnexion", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_email = None
                st.session_state.active_tab = "🔍 Audit GEO"
                st.rerun()

        return selected

# --- 4. LOGIN PAGE ---
def render_login_page():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.title("HOTARU 3.0")
        st.markdown("Connectez-vous pour accéder à la suite GEO.")
        
        with st.form("login"):
            # Valeurs par défaut pour tester vite (à retirer en prod)
            email = st.text_input("Email", value="demo@hotaru.app")
            password = st.text_input("Mot de passe", type="password", value="demo")
            submit = st.form_submit_button("Entrer", use_container_width=True)
            
            if submit:
                # Simulation Auth réussie
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.active_tab = "🔍 Audit GEO"
                st.rerun()

# --- 5. MAIN ROUTER ---
def main():
    inject_custom_css()

    # Initialisation de l'état d'authentification
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # ROUTAGE PRINCIPAL
    if not st.session_state.authenticated:
        render_login_page()
    else:
        # 1. On affiche la sidebar et on récupère le choix
        selected_page = render_sidebar()
        
        # 2. On met à jour l'état
        st.session_state.active_tab = selected_page

        # 3. On affiche la page correspondante
        if selected_page == "📊 Dashboard":
            st.title("Tableau de bord")
            st.info("Statistiques globales à venir.")
            
        elif selected_page == "🔍 Audit GEO":
            # Import dynamique pour éviter les erreurs circulaires
            try:
                from modules.audit_geo import render_audit_geo
                render_audit_geo()
            except ImportError:
                st.error("Module 'modules/audit_geo.py' introuvable.")
            except Exception as e:
                st.error(f"Erreur dans le module Audit: {e}")
                
        elif selected_page == "📄 Rapports":
            st.title("Mes Rapports")
            st.info("Historique des audits sauvegardés.")
            
        elif selected_page == "⚙️ Parametres":
            try:
                from modules.settings import render_settings
                render_settings()
            except:
                st.warning("Module Paramètres en construction")

if __name__ == "__main__":
    main()
