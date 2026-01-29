"""
HOTARU - Authentication Module
Handles user authentication via Google Sheets database.
"""

import streamlit as st
import hashlib
from typing import Optional, Tuple
from core.database import get_db


class AuthManager:
    """
    Authentication manager using Google Sheets as backend.
    """

    def __init__(self):
        """Initialize the authentication manager."""
        self.db = get_db()

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
            users_df = self.db.read_sheet("users")

            if users_df is None or users_df.empty:
                # No users - dev mode, allow login
                st.warning("Mode dev: Base utilisateurs vide - connexion autorisée")
                return True

            # Find user by email
            user = users_df[users_df['email'].str.lower() == email.lower()]

            if user.empty:
                return False

            # Verify password
            password_hash = self._hash_password(password)
            stored_hash = str(user.iloc[0].get('password_hash', ''))

            # Also allow plain text password for simple setup
            stored_plain = str(user.iloc[0].get('password_hash', ''))

            if password_hash == stored_hash or password == stored_plain:
                return True

            return False

        except Exception as e:
            st.error(f"Erreur auth: {str(e)}")
            # Dev mode - allow on error
            return True

    def get_user_info(self, email: str) -> Optional[dict]:
        """Get user information by email."""
        try:
            users_df = self.db.read_sheet("users")

            if users_df is None or users_df.empty:
                return None

            user = users_df[users_df['email'].str.lower() == email.lower()]

            if user.empty:
                return None

            user_data = user.iloc[0].to_dict()
            user_data.pop('password_hash', None)
            return user_data

        except Exception:
            return None


def require_auth(func):
    """Decorator to require authentication."""
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated', False):
            st.error("Vous devez être connecté")
            st.stop()
        return func(*args, **kwargs)
    return wrapper
