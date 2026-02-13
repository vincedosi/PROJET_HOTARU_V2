"""
HOTARU - Runtime context (agnostique UI).
Permet à core/ et modules/ de fonctionner sans Streamlit.
L'app Streamlit appelle init() au démarrage avec st.secrets et st.session_state.
L'API peut appeler init() avec des secrets env et un dict pour la session.
"""

_secrets: dict = {}
_session: dict = {}


def init(secrets: dict = None, session: dict = None):
    """Injecte les secrets et la session (appelé par app.py ou api)."""
    global _secrets, _session
    _secrets = secrets or {}
    _session = session or {}


def get_secrets() -> dict:
    return _secrets


def get_session() -> dict:
    return _session


def get_secret(path: str, default=None):
    """Récupère un secret par chemin (ex: 'mistral.api_key' ou 'gcp_service_account')."""
    keys = path.replace("[", ".").replace("]", "").split(".")
    val = _secrets
    for k in keys:
        val = val.get(k, default) if isinstance(val, dict) else default
        if val is default:
            return default
    return val
