"""
DATABASE MANAGER (MODE URL)
Correction : Ouvre le Google Sheet directement via son URL.
"""
import streamlit as st
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

class AuditDatabase:
    def __init__(self):
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds = None
        self.client = None
        self.sheet = None
        
        # 1. Vérif des secrets JSON
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Erreur Config : Il manque la section [gcp_service_account] dans les secrets.")
            return

        try:
            # 2. Connexion Robot
            self.creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=self.scopes
            )
            self.client = gspread.authorize(self.creds)
            
            # 3. OUVERTURE PAR URL (C'est ça la correction !)
            if "sheet_url" in st.secrets:
                url = st.secrets["sheet_url"]
                try:
                    self.sheet = self.client.open_by_url(url)
                    # Petit message discret pour dire que c'est connecté
                    # st.toast("Base de données connectée", icon="✅") 
                except gspread.exceptions.APIError as e:
                    st.error(f"❌ Erreur d'accès URL. Vérifiez que '{st.secrets['gcp_service_account']['client_email']}' est bien Éditeur du fichier.")
            else:
                st.error("❌ Il manque la clé 'sheet_url' dans les secrets Streamlit.")
                
        except Exception as e:
            st.error(f"❌ Erreur technique GSheets : {e}")

    def get_or_create_worksheet(self, name="audits"):
        if not self.sheet: return None
        try:
            return self.sheet.worksheet(name)
        except:
            try:
                # Si l'onglet n'existe pas, on le crée
                ws = self.sheet.add_worksheet(title=name, rows=100, cols=10)
                ws.append_row(["audit_id", "user_email", "date", "site_url", "nb_pages", "json_data"])
                return ws
            except Exception as e:
                st.error(f"Impossible de créer l'onglet '{name}'. Vérifiez les droits Éditeur du robot.")
                return None

    def save_audit(self, user_email, site_url, graph_data, stats):
        if not self.sheet:
            st.error("Base de données non connectée (Vérifiez st.secrets).")
            return False

        try:
            ws = self.get_or_create_worksheet("audits")
            if not ws: return False
            
            audit_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{site_url.replace('https://', '')[:10]}"
            json_str = json.dumps(graph_data)
            
            ws.append_row([
                audit_id,
                user_email,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                site_url,
                stats.get('total_urls', 0),
                json_str
            ])
            return True
        except Exception as e:
            st.error(f"Erreur Sauvegarde : {e}")
            return False

    def load_user_audits(self, user_email):
        if not self.sheet: return []
        try:
            ws = self.get_or_create_worksheet("audits")
            records = ws.get_all_records()
            return [r for r in records if r.get('user_email') == user_email]
        except:
            return []
