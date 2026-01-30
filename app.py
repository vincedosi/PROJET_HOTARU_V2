"""
HOTARU - SaaS Application
NAVIGATION TOP-BAR (Onglets)
Pour résoudre définitivement le problème de sidebar.
"""

import streamlit as st

# --- 1. CONFIGURATION (Première ligne obligatoire) ---
st.set_page_config(
    page_title="HOTARU",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed" # On cache la sidebar volontairement
)

# --- 2. CSS ZEN (DESIGN SYSTEM) ---
def inject_custom_css():
    st.markdown("""
        <style>
        /* Fond Blanc Partout */
        .stApp, .main, [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
        }

        /* Masquer la sidebar native et le bouton hamburger */
        [data-testid="stSidebar"] { display: none; }
        [data-testid="collapsedControl"] { display: none; }
        
        /* Style du Menu Horizontal (Onglets Radio) */
        div[role="radiogroup"] {
            display: flex;
            flex-direction: row;
            justify-content: center;
            width: 100%;
            background-color: #ffffff;
            border-bottom: 1px solid #000000;
            padding-bottom: 10px;
        }
        
        div[data-testid="stRadio"] > label {
            background-color: #ffffff;
            padding: 10px 20px;
            border-radius: 5px;
            margin: 0 5px;
            cursor: pointer;
            border: 1px solid transparent;
            font-weight: 500;
        }

        /* Cacher les éléments déco Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Boutons Zen */
        .stButton > button {
            border: 1px solid #000000 !important;
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border-radius: 0px !important;
        }
        .stButton > button:hover {
            background-color: #f0f0f0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 3. EN-TÊTE & NAVIGATION ---
def render_header():
    """Affiche le Logo et le Menu de Navigation en haut."""
    
    # 1. LOGO CENTRÉ
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="text-align: center; padding-top: 1rem; padding-bottom: 0.5rem;">
                <h1 style="color: black; margin:0; font-size: 2rem;">
                    <span style="color: #FFD700;">●</span> HOTARU
                </h1>
                <p style="color: #666; font-size: 0.8rem; margin:0;">Architecture & SEO Intelligence</p>
            </div>
        """, unsafe_allow_html=True)

    # 2. NAVIGATION HORIZONTALE (Au lieu de la sidebar)
    st.write("") # Spacer
    
    # Options du menu
    options = ["📊 Dashboard", "🔍 Audit GEO", "📄 Rapports", "⚙️ Config"]
    
    # Icônes pour faire joli
    icons = {"📊 Dashboard": "bar-chart", "🔍 Audit GEO": "search", "📄 Rapports": "file-text", "⚙️ Config": "gear"}
    
    # On utilise un st.radio horizontal centré
    # C'est le moyen le plus robuste de naviguer
    col_nav1, col_nav2, col_nav3 = st.columns([1, 4, 1])
    with col_nav2:
        selected = st.radio(
            "Menu",
            options,
            index=0 if "active_tab" not in st.session_state else options.index(st.session_state.active_tab),
            horizontal=True,
            label_visibility="collapsed",
            key="top_nav"
        )
    
    st.markdown("---") # Ligne de séparation
    return selected

# --- 4. PAGE DE CONNEXION ---
def render_login_page():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: black;'>Connexion</h2>", unsafe_allow_html=True)
        
        with st.form("login"):
            email = st.text_input("Email", value="demo@hotaru.app")
            password = st.text_input("Mot de passe", type="password", value="demo")
            submit = st.form_submit_button("Entrer", use_container_width=True)
            
            if submit:
                # Bypass temporaire pour que tu puisses entrer
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.active_tab = "🔍 Audit GEO"
                st.rerun()

# --- 5. ROUTEUR PRINCIPAL ---
def main():
    inject_custom_css()

    # Init Session
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "🔍 Audit GEO"

    # LOGIQUE
    if not st.session_state.authenticated:
        render_login_page()
    else:
        # AFFICHER HEADER + NAV (Toujours visible)
        selected_page = render_header()
        st.session_state.active_tab = selected_page

        # ROUTAGE CONTENU
        if selected_page == "📊 Dashboard":
            st.info("🚧 Dashboard en construction - Passez à l'onglet Audit")
            
        elif selected_page == "🔍 Audit GEO":
            try:
                from modules.audit_geo import render_audit_geo
                render_audit_geo()
            except ImportError:
                st.error("⚠️ Fichier 'modules/audit_geo.py' introuvable.")
                st.code("Vérifie que le dossier 'modules' existe bien.")
            except Exception as e:
                st.error(f"Erreur dans le module : {e}")
                
        elif selected_page == "📄 Rapports":
            st.write("Historique des rapports (Vide pour l'instant)")
            
        elif selected_page == "⚙️ Config":
            # Petit panneau de config rapide
            st.subheader("Configuration Rapide")
            
            # Gestion Clé API simplifiée
            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("Clé API Mistral")
                key_input = st.text_input("Clé", type="password", key="settings_key_input")
                if st.button("Sauvegarder Clé"):
                    st.session_state.mistral_api_key = key_input
                    st.success("Clé enregistrée !")
            
            with col_b:
                st.caption("Compte")
                if st.button("Déconnexion"):
                    st.session_state.authenticated = False
                    st.rerun()

if __name__ == "__main__":
    main()
