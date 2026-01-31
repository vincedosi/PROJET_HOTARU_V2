import streamlit as st
import json
import zlib
import base64
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

class AuditDatabase:
    # ... (Garder l'init identique) ...
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        try:
            self.creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=self.scopes)
            self.client = gspread.authorize(self.creds)
            url = st.secrets.get("sheet_url") or st.secrets.get("url")
            if url: self.sheet = self.client.open_by_url(url)
        except Exception as e: st.error(f"Erreur GSheets: {e}")

    def get_or_create_worksheet(self, name="audits"):
        if not self.sheet: return None
        try: return self.sheet.worksheet(name)
        except:
            ws = self.sheet.add_worksheet(title=name, rows=1000, cols=10)
            ws.append_row(["audit_id", "user_email", "date", "site_url", "nb_pages", "data_compressed"])
            return ws

    def save_audit(self, user_email, site_url, full_payload, stats):
        if not self.sheet: return False
        try:
            ws = self.get_or_create_worksheet("audits")
            
            # --- COMPRESSION MAGIQUE ---
            # 1. On transforme en JSON
            json_data = json.dumps(full_payload)
            # 2. On compresse (binaire)
            compressed = zlib.compress(json_data.encode('utf-8'))
            # 3. On encode en texte (base64) pour que GSheets l'accepte
            safe_string = base64.b64encode(compressed).decode('utf-8')
            
            if len(safe_string) > 48000:
                st.warning("⚠️ Audit trop volumineux, réduction auto aux 50 premières pages.")
                # Option de secours si même compressé c'est trop gros
                full_payload['results'] = full_payload['results'][:50]
                return self.save_audit(user_email, site_url, full_payload, stats)

            ws.append_row([
                f"{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_email,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                site_url,
                stats.get('total_urls', 0),
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
            filtered = records if is_admin else [r for r in records if r.get('user_email') == user_email]
            
            # --- DECOMPRESSION ---
            for r in filtered:
                try:
                    raw_b64 = r.get('data_compressed') or r.get('json_data')
                    if raw_b64.startswith('{'): # C'est l'ancien format JSON
                        r['json_data'] = json.loads(raw_b64)
                    else: # C'est le nouveau format compressé
                        decoded = base64.b64decode(raw_b64)
                        decompressed = zlib.decompress(decoded).decode('utf-8')
                        r['json_data'] = json.loads(decompressed)
                except: continue
            return filtered
        except: return []
