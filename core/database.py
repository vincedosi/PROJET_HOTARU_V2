"""
HOTARU v2 - Audit Database (Google Sheets Backend)
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import time
import datetime
import zlib
import base64


class AuditDatabase:
    def __init__(self):
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        try:
            self.creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=self.scope
            )
            self.client = gspread.authorize(self.creds)
        except Exception as e:
            st.error(f"Erreur de configuration Secrets (GCP): {e}")
            self.client = None
            self.sheet_file = None
            self.sheet = None
            return

        try:
            sheet_url = st.secrets.get("sheet_url", "")
            if not sheet_url:
                st.error("URL du Google Sheet manquante dans les secrets Streamlit")
                self.sheet = None
                return

            self.sheet_file = self.client.open_by_url(sheet_url)

            try:
                self.sheet = self.sheet_file.worksheet("audits")
            except Exception:
                self.sheet = self.sheet_file.sheet1

        except Exception as e:
            st.error(f"Impossible d'ouvrir le GSheet. Erreur: {e}")
            self.sheet = None

    def load_user_audits(self, user_email):
        if not self.sheet:
            return []

        try:
            all_rows = self.sheet.get_all_values()
            if len(all_rows) < 2:
                return []

            data_rows = all_rows[1:]
            user_audits = []

            for row in data_rows:
                if len(row) < 2:
                    continue

                workspace_value = row[2] if len(row) > 2 else ""

                audit = {
                    "audit_id": row[0],
                    "user_email": row[1],
                    "workspace": workspace_value.strip() if workspace_value.strip() else "Non classé",
                    "date": row[3] if len(row) > 3 else "",
                    "site_url": row[4] if len(row) > 4 else "",
                    "nb_pages": row[5] if len(row) > 5 else 0,
                    "data_compressed": row[6] if len(row) > 6 else "",
                    "nom_site": row[7] if len(row) > 7 else "Site Inconnu",
                }
                user_audits.append(audit)

            return user_audits

        except Exception as e:
            st.error(f"Erreur lors de la lecture des audits : {e}")
            return []

    def save_audit(self, user_email, workspace, site_url, nom_site, json_data):
        if not self.sheet:
            st.error("Impossible de sauvegarder : connexion BDD échouée")
            return False

        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            audit_id = f"{int(time.time())}"

            json_str = json.dumps(json_data)
            compressed = base64.b64encode(
                zlib.compress(json_str.encode("utf-8"))
            ).decode("ascii")

            final_ws = workspace if workspace and workspace.strip() else "Non classé"

            new_row = [
                audit_id,
                user_email,
                final_ws,
                date_str,
                site_url,
                len(json_data.get("results", [])),
                compressed,
                nom_site,
            ]

            self.sheet.append_row(new_row)
            return True

        except Exception as e:
            st.error(f"Erreur de sauvegarde GSheet : {e}")
            return False
