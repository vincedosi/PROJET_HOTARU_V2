"""
HOTARU - SaaS Application
Japanese Zen / Flat Design

Main router with navigation and CSS injection.
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

    # Additional inline CSS for elements that need !important overrides
    st.markdown("""
        <style>
        /* Force white background everywhere */
        .stApp, .main, [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
        }

        /* Sidebar pure white */
        section[data-testid="stSidebar"] > div:first-child {
            background-color: #FFFFFF !important;
        }
        </style>
    """, unsafe_allow_html=True)


def render_logo():
    """Render the HOTARU logo in sidebar."""
    logo_path = Path("assets/logo.png")

    st.markdown("""
        <div style="
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2rem 1rem 1.5rem 1rem;
            border-bottom: 1px solid #000000;
            margin-bottom: 1.5rem;
        ">
    """, unsafe_allow_html=True)

    if logo_path.exists():
        st.image(str(logo_path), width=120)
    else:
        # Fallback text logo
        st.markdown("""
            <div style="
                font-size: 1.75rem;
                font-weight: 700;
                color: #000000;
                text-align: center;
                letter-spacing: 0.2em;
            ">
                <span style="color: #FFD700;">●</span> HOTARU
            </div>
            <div style="
                font-size: 0.7rem;
                color: #000000;
                text-align: center;
                opacity: 0.6;
                margin-top: 0.25rem;
            ">
                蛍 · Firefly
            </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_navigation():
    """Render the sidebar navigation menu."""
    # Initialize navigation state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    # Navigation menu items
    menu_items = [
        {'id': 'dashboard', 'icon': '🏠', 'label': 'Dashboard'},
        {'id': 'audit_geo', 'icon': '🔍', 'label': 'Audit GEO'},
        {'id': 'settings', 'icon': '⚙️', 'label': 'Réglages'},
    ]

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    for item in menu_items:
        is_active = st.session_state.current_page == item['id']

        # Active indicator style
        border_color = "#FFD700" if is_active else "transparent"
        font_weight = "600" if is_active else "400"

        col1, col2 = st.columns([0.15, 0.85])

        with col1:
            st.markdown(f"""
                <div style="
                    width: 3px;
                    height: 40px;
                    background-color: {border_color};
                    margin-left: -1rem;
                "></div>
            """, unsafe_allow_html=True)

        with col2:
            if st.button(
                f"{item['icon']}  {item['label']}",
                key=f"nav_{item['id']}",
                use_container_width=True
            ):
                st.session_state.current_page = item['id']
                st.rerun()


def render_user_profile():
    """Render the user profile section at the bottom of sidebar."""
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")

    if st.session_state.get('authenticated', False):
        user_email = st.session_state.get('user_email', 'user@example.com')
        user_name = user_email.split('@')[0].title()

        col1, col2 = st.columns([0.25, 0.75])

        with col1:
            # Avatar placeholder
            st.markdown(f"""
                <div style="
                    width: 36px;
                    height: 36px;
                    border-radius: 50%;
                    border: 1px solid #000000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 0.875rem;
                    font-weight: 600;
                    background-color: #FFFFFF;
                    color: #000000;
                ">
                    {user_name[0].upper()}
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div style="font-size: 0.875rem; font-weight: 500; color: #000000;">
                    {user_name}
                </div>
                <div style="font-size: 0.75rem; color: #000000; opacity: 0.6;">
                    {user_email}
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

        if st.button("Déconnexion", key="logout_btn", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.rerun()
    else:
        st.markdown("""
            <div style="
                font-size: 0.8rem;
                color: #000000;
                opacity: 0.6;
                text-align: center;
            ">
                Non connecté
            </div>
        """, unsafe_allow_html=True)


def render_login_page():
    """Render the minimalist login page."""
    # Center the login form
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        st.markdown("<div style='height: 15vh;'></div>", unsafe_allow_html=True)

        # Logo
        logo_path = Path("assets/logo.png")
        if logo_path.exists():
            st.image(str(logo_path), width=150, use_container_width=False)
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
                    # Import auth module
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
    page = st.session_state.get('current_page', 'dashboard')

    if page == 'dashboard':
        from modules.dashboard import render_dashboard
        render_dashboard()

    elif page == 'audit_geo':
        from modules.audit_geo import render_audit_geo
        render_audit_geo()

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
        # Show login page (no sidebar)
        render_login_page()
    else:
        # Show main application with sidebar
        with st.sidebar:
            render_logo()
            render_navigation()
            render_user_profile()

        # Main content area
        render_main_content()


if __name__ == "__main__":
    main()
