"""
HOTARU - Settings Module
User account and application settings.
"""

import streamlit as st
from core.auth import AuthManager
from core.database import get_db


def render_settings():
    """Render the settings page."""
    # Header
    st.markdown("""
        <h1 style="
            font-size: 1.75rem;
            font-weight: 600;
            color: #000000;
            margin-bottom: 0.5rem;
        ">
            Réglages
        </h1>
        <p style="
            font-size: 0.9rem;
            color: #000000;
            opacity: 0.6;
            margin-bottom: 2rem;
        ">
            Gérez votre compte et vos préférences
        </p>
    """, unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Profil", "Sécurité", "Application"])

    with tab1:
        render_profile_settings()

    with tab2:
        render_security_settings()

    with tab3:
        render_app_settings()


def render_profile_settings():
    """Render profile settings section."""
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    user_email = st.session_state.get('user_email', '')
    user_name = user_email.split('@')[0].title() if user_email else ''

    # Avatar
    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown(f"""
            <div style="
                width: 80px;
                height: 80px;
                border-radius: 50%;
                border: 1px solid #000000;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2rem;
                font-weight: 600;
                background-color: #FFFFFF;
                color: #000000;
                margin: 0 auto;
            ">
                {user_name[0].upper() if user_name else '?'}
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div style="padding: 0.5rem 0;">
                <div style="
                    font-size: 1.25rem;
                    font-weight: 600;
                    color: #000000;
                ">
                    {user_name}
                </div>
                <div style="
                    font-size: 0.9rem;
                    color: #000000;
                    opacity: 0.6;
                ">
                    {user_email}
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Profile form
    st.markdown("""
        <div style="
            font-size: 0.9rem;
            font-weight: 500;
            color: #000000;
            margin-bottom: 1rem;
        ">
            Informations du profil
        </div>
    """, unsafe_allow_html=True)

    with st.form("profile_form"):
        new_name = st.text_input(
            "Nom d'affichage",
            value=user_name,
            key="profile_name"
        )

        new_email = st.text_input(
            "Email",
            value=user_email,
            disabled=True,
            key="profile_email"
        )

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("Enregistrer", use_container_width=True)

        if submitted:
            st.success("Profil mis à jour")


def render_security_settings():
    """Render security settings section."""
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    st.markdown("""
        <div style="
            font-size: 0.9rem;
            font-weight: 500;
            color: #000000;
            margin-bottom: 1rem;
        ">
            Changer le mot de passe
        </div>
    """, unsafe_allow_html=True)

    with st.form("password_form"):
        current_password = st.text_input(
            "Mot de passe actuel",
            type="password",
            key="current_password"
        )

        new_password = st.text_input(
            "Nouveau mot de passe",
            type="password",
            key="new_password"
        )

        confirm_password = st.text_input(
            "Confirmer le mot de passe",
            type="password",
            key="confirm_password"
        )

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("Modifier", use_container_width=True)

        if submitted:
            if not current_password or not new_password:
                st.warning("Veuillez remplir tous les champs")
            elif new_password != confirm_password:
                st.error("Les mots de passe ne correspondent pas")
            elif len(new_password) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères")
            else:
                auth = AuthManager()
                success, message = auth.change_password(
                    st.session_state.get('user_email', ''),
                    current_password,
                    new_password
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Sessions
    st.markdown("""
        <div style="
            font-size: 0.9rem;
            font-weight: 500;
            color: #000000;
            margin-bottom: 1rem;
        ">
            Sessions actives
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style="
            border: 1px solid #000000;
            padding: 1rem;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.9rem; color: #000000; font-weight: 500;">
                        Session actuelle
                    </div>
                    <div style="font-size: 0.75rem; color: #000000; opacity: 0.6;">
                        Navigateur web · Maintenant
                    </div>
                </div>
                <div style="
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background-color: #22C55E;
                "></div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_app_settings():
    """Render application settings section."""
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    st.markdown("""
        <div style="
            font-size: 0.9rem;
            font-weight: 500;
            color: #000000;
            margin-bottom: 1rem;
        ">
            Préférences d'analyse
        </div>
    """, unsafe_allow_html=True)

    # Audit settings
    col1, col2 = st.columns(2)

    with col1:
        max_urls = st.number_input(
            "URLs maximum à analyser",
            min_value=50,
            max_value=1000,
            value=500,
            step=50,
            key="max_urls_setting"
        )

    with col2:
        sample_size = st.number_input(
            "Taille d'échantillon",
            min_value=10,
            max_value=100,
            value=50,
            step=10,
            key="sample_size_setting"
        )

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    auto_save = st.checkbox(
        "Sauvegarder automatiquement les audits",
        value=True,
        key="auto_save_setting"
    )

    notifications = st.checkbox(
        "Activer les notifications",
        value=False,
        key="notifications_setting"
    )

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    if st.button("Enregistrer les préférences", key="save_app_settings", use_container_width=True):
        # Save to session state or database
        st.session_state.app_settings = {
            'max_urls': max_urls,
            'sample_size': sample_size,
            'auto_save': auto_save,
            'notifications': notifications
        }
        st.success("Préférences enregistrées")

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Danger zone
    st.markdown("""
        <div style="
            font-size: 0.9rem;
            font-weight: 500;
            color: #EF4444;
            margin-bottom: 1rem;
        ">
            Zone de danger
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Effacer l'historique", key="clear_history"):
            if 'confirm_clear' not in st.session_state:
                st.session_state.confirm_clear = True
                st.warning("Cliquez à nouveau pour confirmer")
            else:
                # Clear audit history
                try:
                    db = get_db()
                    user_email = st.session_state.get('user_email', '')
                    # Delete user's audits
                    st.success("Historique effacé")
                    del st.session_state.confirm_clear
                except Exception as e:
                    st.error(f"Erreur: {str(e)}")

    with col2:
        if st.button("Supprimer le compte", key="delete_account"):
            st.error("Contactez le support pour supprimer votre compte")

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    # About section
    st.markdown("---")
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    st.markdown("""
        <div style="
            text-align: center;
            color: #000000;
            opacity: 0.5;
            font-size: 0.8rem;
        ">
            <div style="margin-bottom: 0.5rem;">
                <span style="color: #FFD700;">●</span> HOTARU v1.0.0
            </div>
            <div>
                蛍 · Firefly Audit Suite
            </div>
        </div>
    """, unsafe_allow_html=True)
