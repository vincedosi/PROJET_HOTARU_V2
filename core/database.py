"""
HOTARU - Database Module
Google Sheets connection and operations using st.connection (gsheets).
"""

import streamlit as st
import pandas as pd
from typing import Optional, Any, List, Dict
from pathlib import Path

# PLACER VOTRE FICHIER service_account.json À LA RACINE DU PROJET
# Le chemin par défaut est: ./service_account.json
SERVICE_ACCOUNT_FILE = "service_account.json"


class DatabaseManager:
    """
    Database manager using Google Sheets as backend.

    This class provides CRUD operations for Google Sheets,
    using Streamlit's st.connection with gsheets connector.
    """

    def __init__(self, spreadsheet_url: Optional[str] = None):
        """
        Initialize the database manager.

        Args:
            spreadsheet_url: Optional Google Sheets URL.
                            If not provided, uses the one from secrets.toml
        """
        self.spreadsheet_url = spreadsheet_url
        self._connection = None

    @property
    def connection(self):
        """Get or create the Google Sheets connection."""
        if self._connection is None:
            try:
                self._connection = st.connection("gsheets", type="GSheetsConnection")
            except Exception as e:
                st.error(f"Erreur de connexion Google Sheets: {str(e)}")
                st.info("Vérifiez que le fichier service_account.json est présent")
                return None
        return self._connection

    def read_sheet(
        self,
        worksheet: str,
        usecols: Optional[List[int]] = None,
        ttl: int = 300
    ) -> Optional[pd.DataFrame]:
        """
        Read data from a worksheet.

        Args:
            worksheet: Name of the worksheet to read
            usecols: Optional list of column indices to read
            ttl: Cache time-to-live in seconds (default: 5 minutes)

        Returns:
            DataFrame with sheet data or None on error
        """
        try:
            conn = self.connection
            if conn is None:
                return None

            df = conn.read(
                worksheet=worksheet,
                usecols=usecols,
                ttl=ttl
            )
            return df

        except Exception as e:
            # Sheet might not exist
            if "not found" in str(e).lower():
                return pd.DataFrame()
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
            conn = self.connection
            if conn is None:
                return False

            conn.update(
                worksheet=worksheet,
                data=data
            )
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
            # Read existing data
            existing_df = self.read_sheet(worksheet, ttl=0)

            if existing_df is None:
                existing_df = pd.DataFrame()

            # Create new row DataFrame
            new_row = pd.DataFrame([row_data])

            # Append
            if existing_df.empty:
                updated_df = new_row
            else:
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)

            # Write back
            return self.write_sheet(worksheet, updated_df)

        except Exception as e:
            st.error(f"Erreur ajout ligne: {str(e)}")
            return False

    def update_cell(
        self,
        worksheet: str,
        key_column: str,
        key_value: Any,
        update_column: str,
        update_value: Any
    ) -> bool:
        """
        Update a specific cell in a worksheet.

        Args:
            worksheet: Name of the worksheet
            key_column: Column to search for the row
            key_value: Value to match in key_column
            update_column: Column to update
            update_value: New value for the cell

        Returns:
            True if successful, False otherwise
        """
        try:
            df = self.read_sheet(worksheet, ttl=0)

            if df is None or df.empty:
                return False

            # Find and update the row
            mask = df[key_column] == key_value
            if not mask.any():
                return False

            df.loc[mask, update_column] = update_value

            return self.write_sheet(worksheet, df)

        except Exception as e:
            st.error(f"Erreur mise à jour cellule: {str(e)}")
            return False

    def delete_row(
        self,
        worksheet: str,
        key_column: str,
        key_value: Any
    ) -> bool:
        """
        Delete a row from a worksheet.

        Args:
            worksheet: Name of the worksheet
            key_column: Column to search for the row
            key_value: Value to match in key_column

        Returns:
            True if successful, False otherwise
        """
        try:
            df = self.read_sheet(worksheet, ttl=0)

            if df is None or df.empty:
                return False

            # Remove matching rows
            df = df[df[key_column] != key_value]

            return self.write_sheet(worksheet, df)

        except Exception as e:
            st.error(f"Erreur suppression ligne: {str(e)}")
            return False

    def create_worksheet(
        self,
        worksheet: str,
        columns: List[str]
    ) -> bool:
        """
        Create a new worksheet with specified columns.

        Args:
            worksheet: Name of the new worksheet
            columns: List of column names

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create empty DataFrame with columns
            df = pd.DataFrame(columns=columns)
            return self.write_sheet(worksheet, df)

        except Exception as e:
            st.error(f"Erreur création feuille: {str(e)}")
            return False

    def query(
        self,
        worksheet: str,
        filters: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        """
        Query a worksheet with filters.

        Args:
            worksheet: Name of the worksheet
            filters: Dictionary of column:value pairs to filter by

        Returns:
            Filtered DataFrame or None on error
        """
        try:
            df = self.read_sheet(worksheet)

            if df is None or df.empty:
                return df

            # Apply filters
            mask = pd.Series([True] * len(df))
            for column, value in filters.items():
                if column in df.columns:
                    mask &= (df[column] == value)

            return df[mask]

        except Exception as e:
            st.error(f"Erreur requête: {str(e)}")
            return None


def get_db() -> DatabaseManager:
    """
    Get a database manager instance.

    Uses Streamlit caching to reuse the connection.

    Returns:
        DatabaseManager instance
    """
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    return st.session_state.db_manager


def init_database():
    """
    Initialize the database with required worksheets.

    Creates the following worksheets if they don't exist:
    - users: User accounts
    - audits: Audit history
    - settings: Application settings
    """
    db = get_db()

    # Users worksheet
    users_columns = [
        'email',
        'password_hash',
        'created_at',
        'last_login',
        'role'
    ]
    db.create_worksheet('users', users_columns)

    # Audits worksheet
    audits_columns = [
        'id',
        'user_email',
        'url',
        'created_at',
        'status',
        'results_json'
    ]
    db.create_worksheet('audits', audits_columns)

    # Settings worksheet
    settings_columns = [
        'key',
        'value',
        'updated_at'
    ]
    db.create_worksheet('settings', settings_columns)
