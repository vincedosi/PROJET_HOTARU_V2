"""
HOTARU - Authentification via Supabase (PostgreSQL).
Même interface que core.auth.AuthManager ; lit les secrets via core.runtime.get_secrets().
Secrets Streamlit : backend = "supabase", supabase_url, supabase_service_role_key.
"""

import hashlib
import logging
from datetime import datetime

from core.runtime import get_secrets, get_session
from core.session_keys import SESSION_USER_ROLE

logger = logging.getLogger(__name__)


class AuthManager:
    """Gestionnaire d'authentification basé sur Supabase (table users)."""

    def __init__(self, secrets: dict = None):
        self.sheet_file = None  # pour compatibilité avec app qui peut tester getattr(db, "sheet_file")
        self.client = None
        secrets = secrets or get_secrets()
        url = secrets.get("supabase_url", "").strip()
        key = secrets.get("supabase_service_role_key", "").strip() or secrets.get("supabase_key", "").strip()
        if not url or not key:
            logger.error("supabase_url ou supabase_service_role_key manquant dans les secrets")
            return
        try:
            from supabase import create_client
            self.client = create_client(url, key)
        except Exception as e:
            logger.error("Erreur d'initialisation AuthManager Supabase : %s", e)
            self.client = None

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def login(self, email, password):
        if not self.client:
            return False
        try:
            email_norm = (email or "").strip().lower()
            r = self.client.table("users").select("*").eq("email", email_norm).execute()
            if not r.data or len(r.data) == 0:
                return False
            user = r.data[0]
            stored_hash = (user.get("password_hash") or "").strip()
            if stored_hash != self._hash_password(password):
                return False
            session = get_session()
            session[SESSION_USER_ROLE] = user.get("role") or "admin"
            try:
                self.client.table("users").update({
                    "last_login": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }).eq("id", user["id"]).execute()
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error("Erreur de connexion Supabase : %s", e)
            raise

    def register(self, email, password, role="user"):
        if not self.client:
            return False
        try:
            email_norm = (email or "").strip().lower()
            r = self.client.table("users").select("id").eq("email", email_norm).execute()
            if r.data and len(r.data) > 0:
                raise ValueError("Cet email est déjà enregistré")
            self.client.table("users").insert({
                "email": email_norm,
                "password_hash": self._hash_password(password),
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "last_login": "",
                "role": role,
            }).execute()
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error("Erreur d'inscription Supabase : %s", e)
            raise

    def change_password(self, email, old_password, new_password):
        if not self.client:
            return False
        try:
            email_norm = (email or "").strip().lower()
            r = self.client.table("users").select("*").eq("email", email_norm).execute()
            if not r.data or len(r.data) == 0:
                return False
            user = r.data[0]
            if (user.get("password_hash") or "").strip() != self._hash_password(old_password):
                raise ValueError("Ancien mot de passe incorrect")
            self.client.table("users").update({
                "password_hash": self._hash_password(new_password),
            }).eq("id", user["id"]).execute()
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error("Erreur de changement de mot de passe : %s", e)
            raise

    def auto_migrate_passwords(self):
        if not self.client:
            return False
        try:
            r = self.client.table("users").select("id", "email", "password_hash").execute()
            for user in r.data or []:
                pw = (user.get("password_hash") or "").strip()
                if len(pw) < 20:
                    self.client.table("users").update({
                        "password_hash": self._hash_password(pw),
                    }).eq("id", user["id"]).execute()
                    logger.info("Mot de passe hashé pour %s", user.get("email"))
            return True
        except Exception as e:
            logger.error("Erreur de migration Supabase : %s", e)
            raise
