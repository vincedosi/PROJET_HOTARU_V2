
"""
DATABASE MANAGER (MODE DEBUG)
Objectif : Identifier pourquoi la sauvegarde échoue alors que la connexion marche.
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
        
        # 1. Vérification de la présence des secrets
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets 'gcp_service_account' introuvables dans .streamlit/secrets.toml")
            return

        try:
            # 2. Authentification
            self.creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=self.scopes
            )
            self.client = gspread.authorize(self.creds)
            
            # 3. Ouverture du Fichier
            # ATTENTION : C'est souvent ici que ça casse !
            target_sheet_name = st.secrets.get("sheet_name", "HOTARU_DB")
            
            try:
                self.sheet = self.client.open(target_sheet_name)
            except gspread.exceptions.SpreadsheetNotFound:
                st.error(f"❌ Impossible de trouver le fichier Google Sheet nommé : '{target_sheet_name}'")
                st.info(f"👉 Vérifiez que votre fichier sur Drive s'appelle exactement '{target_sheet_name}' (majuscules comprises).")
                st.info("👉 Ou modifiez 'sheet_name' dans vos secrets Streamlit.")
                return

        except Exception as e:
            st.error(f"❌ Erreur critique de connexion GSheets : {e}")

    def get_or_create_worksheet(self, name="audits"):
        """Tente de récupérer l'onglet, sinon le crée."""
        if not self.sheet: return None
        try:
            return self.sheet.worksheet(name)
        except:
            try:
                # Création de l'onglet s'il n'existe pas
                ws = self.sheet.add_worksheet(title=name, rows=100, cols=10)
                # Ajout des en-têtes
                ws.append_row(["audit_id", "user_email", "date", "site_url", "nb_pages", "json_data"])
                return ws
            except Exception as e:
                st.error(f"❌ Erreur création onglet '{name}' : {e}")
                return None

    def save_audit(self, user_email, site_url, graph_data, stats):
        """Sauvegarde avec rapport d'erreur détaillé."""
        if not self.sheet:
            st.error("❌ Pas de connexion active au fichier Sheet.")
            return False

        try:
            ws = self.get_or_create_worksheet("audits")
            if not ws: return False
            
            audit_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{site_url.replace('https://', '')[:10]}"
            json_str = json.dumps(graph_data)
            
            # Tentative d'écriture
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
            # C'est ici qu'on va voir la vraie erreur !
            st.error(f"❌ CRASH SAUVEGARDE : {e}")
            return False

    def load_user_audits(self, user_email):
        if not self.sheet: return []
        try:
            ws = self.get_or_create_worksheet("audits")
            records = ws.get_all_records()
            return [r for r in records if r.get('user_email') == user_email]
        except Exception as e:
            # On ne bloque pas l'app pour le chargement, mais on logue
            print(f"Erreur chargement: {e}")
            return []
