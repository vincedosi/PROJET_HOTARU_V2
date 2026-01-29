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

    def __init__(self, spreadsheet_url: Optional[str] = None):
        """
        Initialize the database manager.

        Args:
            spreadsheet_url: Optional Google Sheets URL.
        """
        self.spreadsheet_url = spreadsheet_url or st.secrets.get("spreadsheet", {}).get("url", "")
        self._client = None
        self._spreadsheet = None

    @property
    def client(self):
        """Get or create the gspread client."""
        if self._client is None:
            try:
                # Get credentials from Streamlit secrets
                credentials_dict = st.secrets.get("gcp_service_account", {})

                if not credentials_dict:
                    st.error("Configuration manquante: gcp_service_account")
                    return None

                credentials = Credentials.from_service_account_info(
                    dict(credentials_dict),
                    scopes=SCOPES
                )
                self._client = gspread.authorize(credentials)

            except Exception as e:
                st.error(f"Erreur de connexion Google Sheets: {str(e)}")
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

                # Get spreadsheet URL from secrets
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

    def read_sheet(
        self,
        worksheet: str,
        ttl: int = 300
    ) -> Optional[pd.DataFrame]:
        """
        Read data from a worksheet.

        Args:
            worksheet: Name of the worksheet to read
            ttl: Cache time-to-live in seconds (not used with gspread)

        Returns:
            DataFrame with sheet data or None on error
        """
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
            st.error(f"Erreur lecture feuille '{worksheet}': {str(e)}")
            return None

    def write_sheet(
        self,
        worksheet: str,
        data: pd.DataFrame
    ) -> bool:
        """
        Write data to a worksheet (overwrites existing data).

        Args:
            worksheet: Name of the worksheet
            data: DataFrame to write

        Returns:
            True if successful, False otherwise
        """
        try:
            sheet = self.spreadsheet
            if sheet is None:
                return False

            try:
                ws = sheet.worksheet(worksheet)
            except gspread.exceptions.WorksheetNotFound:
                ws = sheet.add_worksheet(title=worksheet, rows=100, cols=20)

            # Clear and update
            ws.clear()

            if not data.empty:
                # Write header and data
                ws.update([data.columns.tolist()] + data.values.tolist())
            else:
                # Write only header
                ws.update([data.columns.tolist()])

            return True

        except Exception as e:
            st.error(f"Erreur écriture feuille '{worksheet}': {str(e)}")
            return False

    def append_row(
        self,
        worksheet: str,
        row_data: Dict[str, Any]
    ) -> bool:
        """
        Append a single row to a worksheet.

        Args:
            worksheet: Name of the worksheet
            row_data: Dictionary with column names as keys

        Returns:
            True if successful, False otherwise
        """
        try:
            sheet = self.spreadsheet
            if sheet is None:
                return False

            ws = sheet.worksheet(worksheet)

            # Get headers
            headers = ws.row_values(1)

            # Create row in correct order
            row = [row_data.get(h, "") for h in headers]

            ws.append_row(row)
            return True

        except Exception as e:
            st.error(f"Erreur ajout ligne: {str(e)}")
            return False

    def get_user(self, email: str) -> Optional[Dict]:
        """
        Get a user by email.

        Args:
            email: User email

        Returns:
            User dict or None if not found
        """
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
    """
    Get a database manager instance.

    Returns:
        DatabaseManager instance
    """
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    return st.session_state.db_manager


def init_database():
    """
    Initialize the database with required worksheets.
    """
    db = get_db()

    # Users worksheet
    users_columns = ['email', 'password_hash', 'created_at', 'last_login', 'role']

    try:
        df = db.read_sheet('users')
        if df is None or df.empty:
            db.write_sheet('users', pd.DataFrame(columns=users_columns))
    except Exception:
        pass
