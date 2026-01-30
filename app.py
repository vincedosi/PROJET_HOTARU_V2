"""
HOTARU - SaaS Application
Japanese Zen / Flat Design

Main router with persistent SaaS navigation sidebar.
"""

import streamlit as st
from pathlib import Path

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="HOTARU",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)


def inject_custom_css():
    """Inject custom CSS for Japanese Zen design."""
    st.markdown("""
        <style>
        /* Force white background everywhere */
        .stApp, .main, [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #000000;
        }

        section[data-testid="stSidebar"] > div:first-child {
            background-color: #FFFFFF !important;
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Radio button styling for nav */
        div[data-testid="stRadio"] > label {
            font-weight: 500;
        }

        /* Button styling - black border */
        .stButton > button {
            border: 1px solid #000000 !important;
            border-radius: 4px !important;
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }

        .stButton > button:hover {
            background-color: #f5f5f5 !important;
            border-color: #FFD700 !important;
        }

        /* Progress bar */
        .stProgress > div > div {
            background-color: #FFD700 !important;
        }
        </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render the persistent sidebar navigation."""
    # Logo section
    st.markdown("""
        <div style="
            text-align: center;
            padding: 1rem 0;
            border-bottom: 1px solid #e0e0e0;
            margin-bottom: 1rem;
        ">
            <div style="
                font-size: 1.5rem;
                font-weight: 700;
                color: #000000;
                letter-spacing: 0.1em;
            ">
                <span style="color: #FFD700;">●</span> HOTARU
            </div>
            <div style="
                font-size: 0.7rem;
                color: #666666;
                margin-top: 0.25rem;
            ">
                蛍 · SEO Audit Suite
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Navigation using radio buttons (most reliable for state)
    st.markdown("##### Navigation")

    # Initialize active tab
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "🔍 Audit GEO"

    selected = st.radio(
        "Menu",
        options=["📊 Dashboard", "🔍 Audit GEO", "📄 Rapports", "⚙️ Parametres"],
        index=["📊 Dashboard", "🔍 Audit GEO", "📄 Rapports", "⚙️ Parametres"].index(st.session_state.active_tab),
        key="nav_radio",
        label_visibility="collapsed"
    )

    # Update session state
    st.session_state.active_tab = selected

    # API Vault section
    st.markdown("---")
    st.markdown("##### 🔐 API Mistral")

    has_api_key = bool(st.session_state.get('mistral_api_key', ''))

    if has_api_key:
        st.success("Connectee", icon="✅")
    else:
        st.warning("Non configuree", icon="⚠️")
        api_key = st.text_input(
            "Cle API",
            type="password",
            placeholder="Entrez votre cle...",
            key="sidebar_api_input"
        )
        if st.button("Enregistrer", key="save_api_sidebar"):
            if api_key:
                st.session_state.mistral_api_key = api_key
                st.rerun()

    # User section
    st.markdown("---")
    if st.session_state.get('authenticated', False):
        user_email = st.session_state.get('user_email', 'demo@hotaru.app')
        st.markdown(f"**{user_email.split('@')[0].title()}**")
        st.caption(user_email)

        if st.button("Deconnexion", key="logout_btn", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.rerun()


def render_login_page():
    """Render the minimalist login page."""
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)

        # Logo
        st.markdown("""
            <div style="text-align: center; margin-bottom: 2rem;">
                <div style="
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: #000000;
                    letter-spacing: 0.2em;
                ">
                    <span style="color: #FFD700;">●</span> HOTARU
                </div>
                <div style="
                    font-size: 0.8rem;
                    color: #666666;
                    margin-top: 0.5rem;
                ">
                    蛍 · Firefly Audit Suite
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Login form
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="votre@email.com")
            password = st.text_input("Mot de passe", type="password", placeholder="••••••••")

            submitted = st.form_submit_button("Entrer", use_container_width=True)

            if submitted:
                if email and password:
                    try:
                        from core.auth import AuthManager
                        auth = AuthManager()
                        if auth.authenticate(email, password):
                            st.session_state.authenticated = True
                            st.session_state.user_email = email
                            st.rerun()
                        else:
                            st.error("Identifiants incorrects")
                    except Exception as e:
                        st.error(f"Erreur connexion: {str(e)}")
                else:
                    st.warning("Veuillez remplir tous les champs")


def render_main_content():
    """Render the main content based on active tab."""
    tab = st.session_state.get('active_tab', '🔍 Audit GEO')

    if tab == "📊 Dashboard":
        from modules.dashboard import render_dashboard
        render_dashboard()

    elif tab == "🔍 Audit GEO":
        from modules.audit_geo import render_audit_geo
        render_audit_geo()

    elif tab == "📄 Rapports":
        from modules.reports import render_reports
        render_reports()

    elif tab == "⚙️ Parametres":
        from modules.settings import render_settings
        render_settings()


def main():
    """Main application entry point."""
    # Inject custom CSS
    inject_custom_css()

    # Check authentication
    is_authenticated = st.session_state.get('authenticated', False)

    if not is_authenticated:
        render_login_page()
    else:
        # ALWAYS show sidebar when authenticated
        with st.sidebar:
            render_sidebar()

        # Main content
        render_main_content()


if __name__ == "__main__":
    main()
