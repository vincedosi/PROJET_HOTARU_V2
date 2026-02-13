"""
HOTARU - Clés de session (SaaS).
Centralise les noms de clés pour cohérence et évolution multi-tenant.
Agnostique UI : utilise core.runtime.get_session().
"""

from core.runtime import get_session

# Authentification
SESSION_AUTHENTICATED = "authenticated"
SESSION_USER_EMAIL = "user_email"
SESSION_USER_ROLE = "user_role"

# Rôle admin (stats globales, gestion utilisateurs)
ROLE_ADMIN = "admin"
ROLE_USER = "user"


def get_current_user_email():
    """Retourne l'email de l'utilisateur connecté (ou None)."""
    return get_session().get(SESSION_USER_EMAIL)


def is_authenticated():
    """Indique si la session est authentifiée."""
    return get_session().get(SESSION_AUTHENTICATED, False)


def is_admin():
    """Indique si l'utilisateur a le rôle admin."""
    return get_session().get(SESSION_USER_ROLE, ROLE_USER) == ROLE_ADMIN
