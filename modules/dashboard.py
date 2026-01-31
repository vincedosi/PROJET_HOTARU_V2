import streamlit as st
import json, zlib, base64
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

class AuditDatabase:
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        try:
            creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=self.scopes)
            self.client = gspread.authorize(creds)
            url = st.secrets.get("sheet_url") or st.secrets.get("url")
            self.sheet = self.client.open_by_url(url)
        except Exception as e: st.error(f"Erreur GSheets: {e}")

    def get_or_create_worksheet(self, name="audits"):
        if not self.sheet: return None
        try: return self.sheet.worksheet(name)
        except:
            # Création avec 7 colonnes
            ws = self.sheet.add_worksheet(title=name, rows=1000, cols=7)
            ws.append_row(["audit_id", "user_email", "workspace", "date", "site_url", "nb_pages", "data_compressed"])
            return ws

    def save_audit(self, user_email, workspace, site_url, full_payload):
        if not self.sheet: return False
        try:
            ws = self.get_or_create_worksheet("audits")
            json_data = json.dumps(full_payload)
            compressed = zlib.compress(json_data.encode('utf-8'))
            safe_string = base64.b64encode(compressed).decode('utf-8')
            
            ws.append_row([
                datetime.now().strftime('%Y%m%d%H%M%S'),
                user_email.strip().lower(),
                workspace.strip(), # Nouvelle colonne Workspace
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                site_url,
                len(full_payload.get('results', [])),
                safe_string
            ])
            return True
        except Exception as e:
            st.error(f"Erreur Save: {e}")
            return False

    def load_user_audits(self, user_email, is_admin=False):
        if not self.sheet: return []
        try:
            ws = self.get_or_create_worksheet("audits")
            records = ws.get_all_records()
            return records if is_admin else [r for r in records if r.get('user_email') == user_email]
        except: return []
