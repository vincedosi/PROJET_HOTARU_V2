"""
HOTARU - Database Module
Google Sheets connection using gspread directly.
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from typing import Optional, Any, List, Dict


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


class DatabaseManager:
    """
    Database manager using Google Sheets as backend.
    Uses gspread directly for Streamlit Cloud compatibility.
    """

    def __init__(self):
        """Initialize the database manager."""
        self._client = None
        self._spreadsheet = None

    @property
    def client(self):
        """Get or create the gspread client."""
        if self._client is None:
            try:
                credentials_dict = dict(st.secrets.get("gcp_service_account", {}))

                if not credentials_dict:
                    st.error("Configuration manquante: gcp_service_account dans secrets")
                    return None

                credentials = Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=SCOPES
                )
                self._client = gspread.authorize(credentials)

            except Exception as e:
                st.error(f"Erreur connexion: {str(e)}")
                return None
        return self._client

    @property
    def spreadsheet(self):
        """Get or open the spreadsheet."""
        if self._spreadsheet is None:
            try:
                client = self.client
                if client is None:
                    return None

                spreadsheet_url = st.secrets.get("spreadsheet", {}).get("url", "")

                if spreadsheet_url:
                    self._spreadsheet = client.open_by_url(spreadsheet_url)
                else:
                    st.error("URL du spreadsheet non configurée")
                    return None

            except Exception as e:
                st.error(f"Erreur ouverture spreadsheet: {str(e)}")
                return None
        return self._spreadsheet

    def read_sheet(self, worksheet: str) -> Optional[pd.DataFrame]:
        """Read data from a worksheet."""
        try:
            sheet = self.spreadsheet
            if sheet is None:
                return None

            ws = sheet.worksheet(worksheet)
            data = ws.get_all_records()
            return pd.DataFrame(data)

        except gspread.exceptions.WorksheetNotFound:
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Erreur lecture '{worksheet}': {str(e)}")
            return None

    def get_user(self, email: str) -> Optional[Dict]:
        """Get a user by email."""
        try:
            df = self.read_sheet("users")
            if df is None or df.empty:
                return None

            user_row = df[df['email'] == email]
            if user_row.empty:
                return None

            return user_row.iloc[0].to_dict()
        except Exception:
            return None

    def create_user(self, email: str, password_hash: str) -> bool:
        """
        Create a new user.

        Args:
            email: User email
            password_hash: Hashed password

        Returns:
            True if successful
        """
        from datetime import datetime

        return self.append_row("users", {
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.now().isoformat(),
            "last_login": "",
            "role": "user"
        })


def get_db() -> DatabaseManager:
    """Get a database manager instance."""
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    return st.session_state.db_manager
