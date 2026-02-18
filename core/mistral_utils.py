"""
HOTARU — Accès centralisé à la clé API Mistral.
Utilisable depuis views/, services/, modules/ et api/.
"""

from core.runtime import get_secret


def get_mistral_key() -> str:
    """Retourne la clé API Mistral ou chaîne vide si absente."""
    return get_secret("mistral.api_key", "") or ""
