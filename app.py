"""
HOTARU - SaaS Application
Japanese Zen / Flat Design

Main router with persistent SaaS navigation sidebar.
"""

import streamlit as st

# --- 1. CONFIGURATION (DOIT ÊTRE LA PREMIÈRE COMMANDE) ---
st.set_page_config(
    page_title="HOTARU",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded" # Force l'ouverture
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

        /* Elements de navigation */
        div[data-testid="stRadio"] > label {
            font-size: 14px;
            padding: 10px 0;
            cursor: pointer;
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

# --- 3. NAVIGATION (LA CORRECTION EST ICI) ---
def render_sidebar():
    """
    Render the sidebar and RETURN the selected page.
    This ensures the main content updates immediately.
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
        # On définit les options
        options = ["📊 Dashboard", "🔍 Audit GEO", "📄 Rapports", "⚙️ Parametres"]
        
        # On récupère l'index par défaut
        default_index = 0
        if "active_tab" in st.session_state and st.session_state.active_tab in options:
            default_index = options.index(st.session_state.active_tab)

        # Le Widget Radio
        selected = st.radio(
            "Navigation",
            options,
            index=default_index,
            label_visibility="collapsed",
            key="nav_radio"
        )

        # API VAULT (SECURITE)
        st.markdown("---")
        st.caption("🔐 API STATUS")
        if st.session_state.get('mistral_api_key'):
             st.success("Mistral Connecté", icon="🟢")
        else:
             st.warning("Mistral Manquant", icon="🔴")

        # USER FOOTER
        st.markdown("---")
        if st.session_state.get('user_email'):
            st.caption(f"👤 {st.session_state.user_email}")
            if st.button("Déconnexion", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_email = None
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
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            submit = st.form_submit_button("Entrer", use_container_width=True)
            
            if submit:
                # BYPASS TEMPORAIRE POUR TESTER LA NAVIGATION
                # Tu remettras ton auth.check plus tard
                if email and password: 
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.active_tab = "🔍 Audit GEO" # Force l'onglet par défaut
                    st.rerun()
                else:
                    st.error("Remplissez les champs")

# --- 5. MAIN ROUTER ---
def main():
    inject_custom_css()

    # Initialisation Session State
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # LOGIQUE DE ROUTAGE PRINCIPALE
    if not st.session_state.authenticated:
        render_login_page()
    else:
        # 1. D'ABORD ON AFFICHE LA SIDEBAR ET ON RECUPERE LE CHOIX
        selected_page = render_sidebar()
        
        # 2. ENSUITE ON AFFICHE LE CONTENU CORRESPONDANT
        # On met à jour le state pour la persistance
        st.session_state.active_tab = selected_page

        if selected_page == "📊 Dashboard":
            st.title("Tableau de bord")
            st.info("Module Dashboard en construction")
            
        elif selected_page == "🔍 Audit GEO":
            # On charge le module dynamiquement pour éviter les imports circulaires
            try:
                from modules.audit_geo import render_audit_geo
                render_audit_geo()
            except ImportError:
                st.error("Module 'modules/audit_geo.py' introuvable ou erreur de code.")
                st.warning("Vérifie que le fichier existe.")
                
        elif selected_page == "📄 Rapports":
            st.title("Mes Rapports")
            st.info("Historique des audits ici")
            
        elif selected_page == "⚙️ Parametres":
            from modules.settings import render_settings
            render_settings()

if __name__ == "__main__":
    main()
