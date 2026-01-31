"""
DATABASE MANAGER
Gère la sauvegarde et le chargement des audits dans Google Sheets.
"""
import streamlit as st
import json
from datetime import datetime
import pandas as pd

# On essaie d'importer gspread, sinon on gère l'erreur
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    st.error("Il manque les librairies gspread. Ajoutez 'gspread' et 'oauth2client' dans requirements.txt")

class AuditDatabase:
    def __init__(self):
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        self.creds = None
        self.client = None
        self.sheet = None
        
        # Connexion via st.secrets
        if "gcp_service_account" in st.secrets:
            try:
                self.creds = ServiceAccountCredentials.from_json_keyfile_dict(
                    dict(st.secrets["gcp_service_account"]), self.scope
                )
                self.client = gspread.authorize(self.creds)
                # Ouvre le sheet défini dans secrets ou par défaut
                sheet_name = st.secrets.get("sheet_name", "HOTARU_DB")
                self.sheet = self.client.open(sheet_name)
            except Exception as e:
                print(f"Erreur connexion GSheets: {e}")

    def get_or_create_worksheet(self, name="audits"):
        """Vérifie si l'onglet existe, sinon le crée."""
        if not self.sheet: return None
        try:
            return self.sheet.worksheet(name)
        except:
            # Création avec les headers
            ws = self.sheet.add_worksheet(title=name, rows=100, cols=10)
            ws.append_row(["audit_id", "user_email", "date", "site_url", "nb_pages", "json_data"])
            return ws

    def save_audit(self, user_email, site_url, graph_data, stats):
        """Sauvegarde un audit complet."""
        if not self.sheet:
            st.warning("Base de données non connectée.")
            return False

        try:
            ws = self.get_or_create_worksheet("audits")
            
            # Création d'un ID unique
            audit_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{site_url[:10]}"
            
            # Sérialisation du graphe en JSON
            json_str = json.dumps(graph_data)
            
            # Ajout de la ligne
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
            st.error(f"Erreur sauvegarde: {e}")
            return False

    def load_user_audits(self, user_email):
        """Récupère la liste des audits d'un utilisateur."""
        if not self.sheet: return []
        
        try:
            ws = self.get_or_create_worksheet("audits")
            records = ws.get_all_records()
            # Filtrer par email
            return [r for r in records if r['user_email'] == user_email]
        except Exception as e:
            st.error(f"Erreur chargement: {e}")
            return []
