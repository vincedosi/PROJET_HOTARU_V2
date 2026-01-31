"""
DATABASE MANAGER
Gère la sauvegarde et le chargement des audits dans Google Sheets.
Utilise la méthode moderne 'google-auth' (Plus robuste pour le déploiement).
"""
import streamlit as st
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials # <--- Nouvelle méthode moderne

class AuditDatabase:
    def __init__(self):
        # Définition du scope (droits d'accès)
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds = None
        self.client = None
        self.sheet = None
        
        # Connexion via st.secrets (Gestion sécurisée)
        if "gcp_service_account" in st.secrets:
            try:
                # Création des credentials avec la nouvelle méthode
                self.creds = Credentials.from_service_account_info(
                    dict(st.secrets["gcp_service_account"]),
                    scopes=self.scopes
                )
                self.client = gspread.authorize(self.creds)
                
                # Ouvre le sheet défini dans secrets ou par défaut
                sheet_name = st.secrets.get("sheet_name", "HOTARU_DB")
                self.sheet = self.client.open(sheet_name)
            except Exception as e:
                # On print l'erreur dans la console serveur pour débugger sans casser l'UI
                print(f"⚠️ Erreur connexion GSheets: {e}")

    def get_or_create_worksheet(self, name="audits"):
        """Vérifie si l'onglet existe, sinon le crée."""
        if not self.sheet: return None
        try:
            return self.sheet.worksheet(name)
        except:
            # Création avec les headers si l'onglet n'existe pas
            ws = self.sheet.add_worksheet(title=name, rows=100, cols=10)
            ws.append_row(["audit_id", "user_email", "date", "site_url", "nb_pages", "json_data"])
            return ws

    def save_audit(self, user_email, site_url, graph_data, stats):
        """Sauvegarde un audit complet."""
        if not self.sheet:
            st.warning("Base de données non connectée (Vérifiez st.secrets).")
            return False

        try:
            ws = self.get_or_create_worksheet("audits")
            
            # Création d'un ID unique
            audit_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{site_url.replace('https://', '')[:10]}"
            
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
            # Filtrer par email pour la sécurité
            return [r for r in records if r['user_email'] == user_email]
        except Exception as e:
            st.error(f"Erreur chargement: {e}")
            return []
