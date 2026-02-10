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

    @st.cache_data(ttl=300)
    def load_user_audits(self, user_email):
        """Charge uniquement les audits de l'utilisateur connecté (isolation SaaS).
        Résultat cachés 5 minutes par email utilisateur."""
        if not self.sheet:
            return []

        try:
            all_rows = self.sheet.get_all_values()
            if len(all_rows) < 2:
                return []

            data_rows = all_rows[1:]
            user_audits = []
            email_normalized = (user_email or "").strip().lower()

            for row in data_rows:
                if len(row) < 2:
                    continue
                # Isolation SaaS : ne retourner que les lignes de cet utilisateur
                row_email = (row[1] or "").strip().lower()
                if row_email != email_normalized:
                    continue

                workspace_value = row[2] if len(row) > 2 else ""
                master_json = row[9] if len(row) > 9 else ""

                audit = {
                    "audit_id": row[0],
                    "user_email": row[1],
                    "workspace": workspace_value.strip() if workspace_value.strip() else "Non classé",
                    "date": row[3] if len(row) > 3 else "",
                    "site_url": row[4] if len(row) > 4 else "",
                    "nb_pages": row[5] if len(row) > 5 else 0,
                    "data_compressed": row[6] if len(row) > 6 else "",
                    "nom_site": row[7] if len(row) > 7 else "Site Inconnu",
                    "master_json": master_json,
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

    def save_master_for_audit(self, user_email, workspace, site_url, master_json):
        """
        Sauvegarde le JSON-LD Master dans la colonne J ('master') de l'onglet audits
        pour la ligne correspondant à (user_email, workspace, site_url).
        """
        if not self.sheet:
            st.error("Impossible de sauvegarder le MASTER : connexion BDD échouée")
            return False

        try:
            all_rows = self.sheet.get_all_values()
            if len(all_rows) < 2:
                st.error("Aucun audit existant pour enregistrer le MASTER.")
                return False

            email_normalized = (user_email or "").strip().lower()
            ws_normalized = (workspace or "").strip()
            url_normalized = (site_url or "").strip()

            for idx, row in enumerate(all_rows[1:], start=2):
                if len(row) < 5:
                    continue
                row_email = (row[1] or "").strip().lower()
                row_ws = (row[2] or "").strip()
                row_url = (row[4] or "").strip()

                if (
                    row_email == email_normalized
                    and row_ws == ws_normalized
                    and row_url == url_normalized
                ):
                    # Colonne J = index 10 (1-based)
                    self.sheet.update_cell(idx, 10, master_json)
                    return True

            st.error("Aucune ligne d'audit correspondante trouvée pour ce MASTER.")
            return False
        except Exception as e:
            st.error(f"Erreur de sauvegarde MASTER GSheet : {e}")
            return False
