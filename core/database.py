import streamlit as st
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

class AuditDatabase:
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        self.creds = None
        self.client = None
        self.sheet = None
        
        if "gcp_service_account" not in st.secrets:
            st.error("Secrets GCP manquants.")
            return

        try:
            self.creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=self.scopes)
            self.client = gspread.authorize(self.creds)
            
            # Récupération URL
            url = st.secrets.get("sheet_url") or st.secrets.get("url")
            if url:
                self.sheet = self.client.open_by_url(url)
        except Exception as e:
            st.error(f"Erreur connexion GSheets : {e}")

    def get_or_create_worksheet(self, name="audits"):
        if not self.sheet: return None
        try:
            return self.sheet.worksheet(name)
        except:
            ws = self.sheet.add_worksheet(title=name, rows=1000, cols=10)
            ws.append_row(["audit_id", "user_email", "date", "site_url", "nb_pages", "json_data"])
            return ws

    def save_audit(self, user_email, site_url, full_payload, stats):
        """Sauvegarde le payload JSON complet pour le versioning."""
        if not self.sheet: return False
        try:
            ws = self.get_or_create_worksheet("audits")
            audit_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
            # On stocke tout (résultats scrap + clusters) dans une seule cellule JSON
            ws.append_row([
                audit_id,
                user_email,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                site_url,
                stats.get('total_urls', 0),
                json.dumps(full_payload)
            ])
            return True
        except Exception as e:
            st.error(f"Erreur Save: {e}")
            return False

    def load_user_audits(self, user_email, is_admin=False):
        """Filtre les données selon le rôle."""
        if not self.sheet: return []
        try:
            ws = self.get_or_create_worksheet("audits")
            records = ws.get_all_records()
            if is_admin:
                return records
            return [r for r in records if r.get('user_email') == user_email]
        except:
            return []
