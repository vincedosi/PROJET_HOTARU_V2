"""
HOTARU - SaaS Application
Japanese Zen / Flat Design

Main router with SaaS navigation sidebar.
"""

import streamlit as st
from pathlib import Path

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="HOTARU",
    page_icon="assets/logo.png" if Path("assets/logo.png").exists() else "✨",
    layout="wide",
    initial_sidebar_state="expanded"
)


def inject_custom_css():
    """Inject custom CSS for Japanese Zen design."""
    css_file = Path("assets/style.css")
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Additional inline CSS for SaaS navigation
    st.markdown("""
        <style>
        /* Force white background everywhere */
        .stApp, .main, [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
        }

        /* Sidebar pure white with fixed width */
        section[data-testid="stSidebar"] > div:first-child {
            background-color: #FFFFFF !important;
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* SaaS Navigation Styling */
        .nav-button {
            width: 100%;
            padding: 0.75rem 1rem;
            margin: 0.25rem 0;
            border: none;
            background: transparent;
            text-align: left;
            cursor: pointer;
            border-left: 3px solid transparent;
            transition: all 0.2s ease;
        }

        .nav-button:hover {
            background-color: #f5f5f5;
            border-left-color: #000000;
        }

        .nav-button.active {
            border-left-color: #FFD700;
            font-weight: 600;
        }

        /* API Key vault styling */
        .vault-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }

        .vault-ok { background-color: #22C55E; }
        .vault-missing { background-color: #EF4444; }
        </style>
    """, unsafe_allow_html=True)


def render_sidebar_logo():
    """Render the HOTARU logo in sidebar."""
    logo_path = Path("assets/logo.png")

    st.markdown("""
        <div style="
            padding: 1.5rem 1rem;
            border-bottom: 1px solid #000000;
            margin-bottom: 1rem;
            text-align: center;
        ">
    """, unsafe_allow_html=True)

    if logo_path.exists():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(str(logo_path), width=100)
    else:
        st.markdown("""
            <div style="
                font-size: 1.5rem;
                font-weight: 700;
                color: #000000;
                letter-spacing: 0.15em;
            ">
                <span style="color: #FFD700;">●</span> HOTARU
            </div>
            <div style="
                font-size: 0.65rem;
                color: #000000;
                opacity: 0.5;
                margin-top: 0.25rem;
            ">
                蛍 · SEO Audit Suite
            </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_saas_navigation():
    """Render the SaaS-style sidebar navigation."""
    # Initialize navigation state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'audit_geo'

    # Navigation items
    nav_items = [
        {'id': 'dashboard', 'icon': '📊', 'label': 'Dashboard'},
        {'id': 'audit_geo', 'icon': '🔍', 'label': 'Audit GEO'},
        {'id': 'reports', 'icon': '📄', 'label': 'Rapports'},
        {'id': 'settings', 'icon': '⚙️', 'label': 'Parametres'},
    ]

    st.markdown("<div style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

    for item in nav_items:
        is_active = st.session_state.current_page == item['id']

        # Visual indicator for active item
        if is_active:
            st.markdown(f"""
                <div style="
                    border-left: 3px solid #FFD700;
                    padding-left: 0.5rem;
                    margin: 0.25rem 0;
                ">
            """, unsafe_allow_html=True)

        if st.button(
            f"{item['icon']}  {item['label']}",
            key=f"nav_{item['id']}",
            use_container_width=True,
            type="secondary" if not is_active else "primary"
        ):
            st.session_state.current_page = item['id']
            st.rerun()

        if is_active:
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_api_vault():
    """Render the API Key Vault section in sidebar."""
    st.markdown("---")
    st.markdown("##### 🔐 API Vault")

    # Check if API key is configured
    has_api_key = bool(st.session_state.get('mistral_api_key', ''))

    if has_api_key:
        st.markdown("""
            <div style="
                padding: 0.5rem;
                background: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 0.8rem;
            ">
                <span style="color: #22C55E;">●</span> Mistral API connectee
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="
                padding: 0.5rem;
                background: #fff8f8;
                border: 1px solid #ffdddd;
                border-radius: 4px;
                font-size: 0.8rem;
            ">
                <span style="color: #EF4444;">●</span> API non configuree
            </div>
        """, unsafe_allow_html=True)

        if st.button("🔑 Configurer", key="sidebar_api_btn", use_container_width=True):
            st.session_state.show_api_modal = True
            st.session_state.current_page = 'settings'
            st.rerun()


def render_user_section():
    """Render user info at bottom of sidebar."""
    st.markdown("---")

    if st.session_state.get('authenticated', False):
        user_email = st.session_state.get('user_email', 'user@example.com')
        user_name = user_email.split('@')[0].title()

        col1, col2 = st.columns([1, 3])

        with col1:
            st.markdown(f"""
                <div style="
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    border: 1px solid #000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.8rem;
                    font-weight: 600;
                    background: #FFFFFF;
                ">
                    {user_name[0].upper()}
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div style="font-size: 0.85rem; font-weight: 500;">{user_name}</div>
                <div style="font-size: 0.7rem; opacity: 0.6;">{user_email}</div>
            """, unsafe_allow_html=True)

        if st.button("Deconnexion", key="logout_btn", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.rerun()
    else:
        st.markdown("""
            <div style="font-size: 0.8rem; opacity: 0.6; text-align: center;">
                Mode demo
            </div>
        """, unsafe_allow_html=True)


def render_login_page():
    """Render the minimalist login page."""
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)

        # Logo
        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), width=150)
        else:
            st.markdown("""
                <div style="text-align: center; margin-bottom: 3rem;">
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
                        color: #000000;
                        opacity: 0.5;
                        margin-top: 0.5rem;
                    ">
                        蛍 · Firefly Audit Suite
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

        # Login form
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input(
                "Email",
                placeholder="votre@email.com",
                key="login_email"
            )

            password = st.text_input(
                "Mot de passe",
                type="password",
                placeholder="••••••••",
                key="login_password"
            )

            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

            submitted = st.form_submit_button("Entrer", use_container_width=True)

            if submitted:
                if email and password:
                    from core.auth import AuthManager
                    auth = AuthManager()

                    if auth.authenticate(email, password):
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.rerun()
                    else:
                        st.error("Identifiants incorrects")
                else:
                    st.warning("Veuillez remplir tous les champs")


def render_main_content():
    """Render the main content based on current page."""
    page = st.session_state.get('current_page', 'audit_geo')

    if page == 'dashboard':
        from modules.dashboard import render_dashboard
        render_dashboard()

    elif page == 'audit_geo':
        from modules.audit_geo import render_audit_geo
        render_audit_geo()

    elif page == 'reports':
        from modules.reports import render_reports
        render_reports()

    elif page == 'settings':
        from modules.settings import render_settings
        render_settings()


def main():
    """Main application entry point."""
    # Inject custom CSS
    inject_custom_css()

    # Check authentication status
    is_authenticated = st.session_state.get('authenticated', False)

    if not is_authenticated:
        render_login_page()
    else:
        # Show main application with SaaS sidebar
        with st.sidebar:
            render_sidebar_logo()
            render_saas_navigation()
            render_api_vault()
            render_user_section()

        # Main content area
        render_main_content()


if __name__ == "__main__":
    main()
