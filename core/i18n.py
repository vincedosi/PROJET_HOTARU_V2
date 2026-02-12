"""
HOTARU - Internationalisation (FR / EN).
Français par défaut.
"""

import streamlit as st

SESSION_LANG = "lang"
DEFAULT_LANG = "fr"

# Traductions principales (navigation, header, workspace)
TRANSLATIONS = {
    "fr": {
        "nav.home": "Home",
        "nav.audit": "Audit",
        "nav.jsonld": "JSON-LD",
        "nav.eco": "Eco-Score",
        "nav.audit_geo": "Audit GEO",
        "nav.authority": "Authority Score",
        "nav.scraping": "Scraping",
        "nav.master": "Master",
        "nav.jsonld_analysis": "Analyse JSON-LD",
        "workspace.label": "Projets (Workspace)",
        "workspace.help": "Choisissez le projet / workspace pour filtrer les audits.",
        "workspace.new": "Nouveau",
        "workspace.create": "+ Créer Nouveau",
        "workspace.uncategorized": "Non classé",
        "login": "LOGIN",
        "logout": "LOGOUT",
        "login.error": "Identifiants invalides.",
    },
    "en": {
        "nav.home": "Home",
        "nav.audit": "Audit",
        "nav.jsonld": "JSON-LD",
        "nav.eco": "Eco-Score",
        "nav.audit_geo": "GEO Audit",
        "nav.authority": "Authority Score",
        "nav.scraping": "Scraping",
        "nav.master": "Master",
        "nav.jsonld_analysis": "JSON-LD Analysis",
        "workspace.label": "Projects (Workspace)",
        "workspace.help": "Choose the project / workspace to filter audits.",
        "workspace.new": "New",
        "workspace.create": "+ Create New",
        "workspace.uncategorized": "Uncategorized",
        "login": "LOGIN",
        "logout": "LOGOUT",
        "login.error": "Invalid credentials.",
    },
}


def get_current_lang():
    """Retourne la langue active (fr ou en). Français par défaut."""
    return st.session_state.get(SESSION_LANG, DEFAULT_LANG)


def set_lang(lang: str):
    """Définit la langue (fr ou en)."""
    if lang in ("fr", "en"):
        st.session_state[SESSION_LANG] = lang


def t(key: str) -> str:
    """Retourne la chaîne traduite pour la clé donnée."""
    lang = get_current_lang()
    d = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
    return d.get(key, key)
