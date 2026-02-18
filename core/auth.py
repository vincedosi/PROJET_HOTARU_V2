"""
HOTARU - Gestionnaire d'authentification basé sur Google Sheets.
Agnostique UI : utilise core.runtime pour secrets et session.
"""

import hashlib
import logging

import gspread
from google.oauth2.service_account import Credentials

from core.runtime import get_secrets, get_session
from core.session_keys import SESSION_USER_ROLE

logger = logging.getLogger(__name__)


class AuthManager:
    """Gestionnaire d'authentification basé sur Google Sheets"""

    def __init__(self, secrets: dict = None):
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        secrets = secrets or get_secrets()
        self.sheet_file = None

        try:
            gcp = secrets.get("gcp_service_account")
            if not gcp:
                raise ValueError("gcp_service_account manquant dans les secrets")
            self.creds = Credentials.from_service_account_info(gcp, scopes=self.scope)
            self.client = gspread.authorize(self.creds)

            sheet_url = secrets.get("sheet_url", "")
            if not sheet_url:
                raise ValueError("URL du Google Sheet manquante dans les secrets")

            self.sheet_file = self.client.open_by_url(sheet_url)

            try:
                self.users_sheet = self.sheet_file.worksheet("users")
            except Exception:
                self.users_sheet = self.sheet_file.add_worksheet(
                    title="users", rows=100, cols=5
                )
                self.users_sheet.append_row(
                    ["email", "password_hash", "created_at", "last_login", "role"]
                )
                admin_hash = self._hash_password("123")
                self.users_sheet.append_row([
                    "admin@hotaru.app", admin_hash, "2025-02-02", "", "admin"
                ])
        except Exception as e:
            logger.error("Erreur d'initialisation AuthManager : %s", e)
            self.sheet_file = None

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def login(self, email, password):
        """Vérifie les identifiants. Retourne True si OK. Met à jour la session (user_role)."""
        if not self.sheet_file:
            return False

        try:
            all_users = self.users_sheet.get_all_records()
            password_hash = self._hash_password(password)

            for user in all_users:
                if user['email'].lower().strip() == email.lower().strip():
                    stored_hash = str(user['password_hash']).strip()
                    if stored_hash == password_hash:
                        session = get_session()
                        session[SESSION_USER_ROLE] = user.get('role', 'admin')
                        try:
                            from datetime import datetime
                            row_index = all_users.index(user) + 2
                            self.users_sheet.update_cell(
                                row_index, 4,
                                datetime.now().strftime("%Y-%m-%d %H:%M")
                            )
                        except Exception:
                            pass
                        return True
                    return False
            return False
        except Exception as e:
            logger.error("Erreur de connexion : %s", e)
            raise

    def register(self, email, password, role="user"):
        """Crée un nouveau compte utilisateur (réservé aux admins)."""
        if not self.sheet_file:
            return False

        try:
            all_users = self.users_sheet.get_all_records()
            for user in all_users:
                if user['email'].lower() == email.lower():
                    raise ValueError("Cet email est déjà enregistré")

            password_hash = self._hash_password(password)
            from datetime import datetime
            self.users_sheet.append_row([
                email, password_hash,
                datetime.now().strftime("%Y-%m-%d"), "", role
            ])
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error("Erreur d'inscription : %s", e)
            raise

    def change_password(self, email, old_password, new_password):
        """Change le mot de passe. Retourne True si OK. Lève ValueError si ancien mot de passe incorrect."""
        if not self.sheet_file:
            return False

        try:
            all_users = self.users_sheet.get_all_values()
            old_hash = self._hash_password(old_password)
            new_hash = self._hash_password(new_password)

            for i, row in enumerate(all_users[1:], start=2):
                if row[0].lower() == email.lower():
                    if row[1] == old_hash:
                        self.users_sheet.update_cell(i, 2, new_hash)
                        return True
                    raise ValueError("Ancien mot de passe incorrect")
            return False
        except ValueError:
            raise
        except Exception as e:
            logger.error("Erreur de changement de mot de passe : %s", e)
            raise

    def auto_migrate_passwords(self):
        """Convertit les mots de passe en clair en hash (Admin uniquement)."""
        if not self.sheet_file:
            return False

        try:
            all_users = self.users_sheet.get_all_values()
            for i, row in enumerate(all_users[1:], start=2):
                password_field = row[1]
                if len(password_field) < 20:
                    new_hash = self._hash_password(password_field)
                    self.users_sheet.update_cell(i, 2, new_hash)
                    logger.info("Mot de passe hashé pour %s", row[0])
            return True
        except Exception as e:
            logger.error("Erreur de migration : %s", e)
            raise

    def list_users(self):
        """Liste tous les utilisateurs (admin backoffice)."""
        if not self.users_sheet:
            return []
        try:
            all_users = self.users_sheet.get_all_records()
            return [
                {"email": u.get("email", ""), "role": u.get("role", "user"),
                 "created_at": u.get("created_at", ""), "last_login": u.get("last_login", "")}
                for u in all_users
            ]
        except Exception as e:
            logger.error("Erreur list_users GSheet : %s", e)
            return []

    def delete_user(self, email: str) -> bool:
        """Supprime un utilisateur par email (admin backoffice)."""
        if not self.users_sheet:
            return False
        try:
            all_rows = self.users_sheet.get_all_values()
            for i, row in enumerate(all_rows[1:], start=2):
                if (row[0] or "").strip().lower() == (email or "").strip().lower():
                    self.users_sheet.delete_rows(i)
                    return True
            return False
        except Exception as e:
            logger.error("Erreur delete_user GSheet : %s", e)
            raise

    def update_user_role(self, email: str, role: str) -> bool:
        """Met à jour le rôle d'un utilisateur (admin backoffice)."""
        if not self.users_sheet:
            return False
        try:
            all_rows = self.users_sheet.get_all_values()
            for i, row in enumerate(all_rows[1:], start=2):
                if (row[0] or "").strip().lower() == (email or "").strip().lower():
                    self.users_sheet.update_cell(i, 5, (role or "user").strip())  # colonne role = 5 (F)
                    return True
            return False
        except Exception as e:
            logger.error("Erreur update_user_role GSheet : %s", e)
            raise
