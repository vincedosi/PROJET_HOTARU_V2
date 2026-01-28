"""
HOTARU - Authentication Module
Handles user authentication via Google Sheets database.
"""

import streamlit as st
import hashlib
from typing import Optional, Tuple
from core.database import DatabaseManager


class AuthManager:
    """
    Authentication manager using Google Sheets as backend.

    User data is stored in a Google Sheet with columns:
    - email: User email (unique identifier)
    - password_hash: SHA-256 hashed password
    - created_at: Account creation timestamp
    - last_login: Last login timestamp
    - role: User role (admin, user, etc.)
    """

    USERS_SHEET_NAME = "users"

    def __init__(self):
        """Initialize the authentication manager."""
        self.db = DatabaseManager()

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, email: str, password: str) -> bool:
        """
        Authenticate a user with email and password.

        Args:
            email: User email address
            password: Plain text password

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Get users data from Google Sheets
            users_df = self.db.read_sheet(self.USERS_SHEET_NAME)

            if users_df is None or users_df.empty:
                # No users in database - for development, allow any login
                # In production, this should return False
                st.warning("Mode développement: Base de données utilisateurs vide")
                return True

            # Find user by email
            user = users_df[users_df['email'].str.lower() == email.lower()]

            if user.empty:
                return False

            # Verify password
            password_hash = self._hash_password(password)
            stored_hash = user.iloc[0].get('password_hash', '')

            if password_hash == stored_hash:
                # Update last login timestamp
                self._update_last_login(email)
                return True

            return False

        except Exception as e:
            st.error(f"Erreur d'authentification: {str(e)}")
            # In development mode, allow login on error
            # Remove this in production!
            return True

    def _update_last_login(self, email: str) -> None:
        """Update the last login timestamp for a user."""
        try:
            from datetime import datetime
            self.db.update_cell(
                self.USERS_SHEET_NAME,
                'email',
                email,
                'last_login',
                datetime.now().isoformat()
            )
        except Exception:
            pass  # Non-critical operation

    def register_user(
        self,
        email: str,
        password: str,
        role: str = "user"
    ) -> Tuple[bool, str]:
        """
        Register a new user.

        Args:
            email: User email address
            password: Plain text password
            role: User role (default: "user")

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if user already exists
            users_df = self.db.read_sheet(self.USERS_SHEET_NAME)

            if users_df is not None and not users_df.empty:
                if email.lower() in users_df['email'].str.lower().values:
                    return False, "Un compte existe déjà avec cet email"

            # Create new user record
            from datetime import datetime
            new_user = {
                'email': email.lower(),
                'password_hash': self._hash_password(password),
                'created_at': datetime.now().isoformat(),
                'last_login': None,
                'role': role
            }

            # Add to database
            success = self.db.append_row(self.USERS_SHEET_NAME, new_user)

            if success:
                return True, "Compte créé avec succès"
            else:
                return False, "Erreur lors de la création du compte"

        except Exception as e:
            return False, f"Erreur: {str(e)}"

    def change_password(
        self,
        email: str,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Change a user's password.

        Args:
            email: User email address
            old_password: Current password
            new_password: New password

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Verify old password first
        if not self.authenticate(email, old_password):
            return False, "Mot de passe actuel incorrect"

        try:
            # Update password hash
            new_hash = self._hash_password(new_password)
            success = self.db.update_cell(
                self.USERS_SHEET_NAME,
                'email',
                email,
                'password_hash',
                new_hash
            )

            if success:
                return True, "Mot de passe modifié avec succès"
            else:
                return False, "Erreur lors de la modification"

        except Exception as e:
            return False, f"Erreur: {str(e)}"

    def get_user_info(self, email: str) -> Optional[dict]:
        """
        Get user information by email.

        Args:
            email: User email address

        Returns:
            User info dict or None if not found
        """
        try:
            users_df = self.db.read_sheet(self.USERS_SHEET_NAME)

            if users_df is None or users_df.empty:
                return None

            user = users_df[users_df['email'].str.lower() == email.lower()]

            if user.empty:
                return None

            user_data = user.iloc[0].to_dict()
            # Remove sensitive data
            user_data.pop('password_hash', None)

            return user_data

        except Exception:
            return None

    def is_admin(self, email: str) -> bool:
        """Check if a user has admin role."""
        user_info = self.get_user_info(email)
        return user_info and user_info.get('role') == 'admin'


def require_auth(func):
    """
    Decorator to require authentication for a function.

    Usage:
        @require_auth
        def my_protected_function():
            pass
    """
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated', False):
            st.error("Vous devez être connecté pour accéder à cette page")
            st.stop()
        return func(*args, **kwargs)
    return wrapper


def require_admin(func):
    """
    Decorator to require admin role for a function.

    Usage:
        @require_admin
        def my_admin_function():
            pass
    """
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated', False):
            st.error("Vous devez être connecté pour accéder à cette page")
            st.stop()

        email = st.session_state.get('user_email')
        auth = AuthManager()

        if not auth.is_admin(email):
            st.error("Accès réservé aux administrateurs")
            st.stop()

        return func(*args, **kwargs)
    return wrapper
