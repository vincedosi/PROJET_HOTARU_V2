"""
DATABASE MANAGER (v0.9.9 - DETECTIVE MODE)
Correction : Cherche l'URL du Sheet partout (Racine, ou dans gcp_service_account).
Gère les erreurs de nommage (url vs sheet_url).
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
            st.error("❌ ERREUR CRITIQUE : La section [gcp_service_account] est absente des secrets.")
            return

        try:
            # 2. Connexion Authentifiée
            self.creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=self.scopes
            )
            self.client = gspread.authorize(self.creds)
            
            # 3. RECHERCHE INTELLIGENTE DE L'URL (Le Détective)
            # On cherche partout où l'utilisateur a pu mettre l'URL
            found_url = None
            
            # A. Cherche à la racine 'sheet_url'
            if "sheet_url" in st.secrets:
                found_url = st.secrets["sheet_url"]
            # B. Cherche à la racine 'url'
            elif "url" in st.secrets:
                found_url = st.secrets["url"]
            # C. Cherche DANS le bloc gcp_service_account (Erreur fréquente d'indentation TOML)
            elif "sheet_url" in st.secrets["gcp_service_account"]:
                found_url = st.secrets["gcp_service_account"]["sheet_url"]
            elif "url" in st.secrets["gcp_service_account"]:
                found_url = st.secrets["gcp_service_account"]["url"]

            # 4. Connexion au fichier
            if found_url:
                try:
                    self.sheet = self.client.open_by_url(found_url)
                except gspread.exceptions.APIError:
                    st.error(f"❌ Accès refusé au Sheet. Vérifiez que '{self.creds.service_account_email}' est bien 'Éditeur'.")
                except Exception as e:
                    st.error(f"❌ URL invalide ou fichier introuvable : {e}")
            else:
                st.warning("⚠️ Aucune URL de Sheet trouvée dans les secrets (cherché 'sheet_url' ou 'url').")
                st.info("Ajoutez : sheet_url = 'https://...' tout en haut de vos secrets.")

        except Exception as e:
            st.error(f"❌ Erreur technique globale : {e}")

    def get_or_create_worksheet(self, name="audits"):
        if not self.sheet: return None
        try:
            return self.sheet.worksheet(name)
        except:
            try:
                # Création si n'existe pas
                ws = self.sheet.add_worksheet(title=name, rows=100, cols=10)
                ws.append_row(["audit_id", "user_email", "date", "site_url", "nb_pages", "json_data"])
                return ws
            except Exception as e:
                st.error(f"Erreur création onglet : {e}")
                return None

    def save_audit(self, user_email, site_url, graph_data, stats):
        if not self.sheet:
            st.error("❌ Base de données non connectée (URL introuvable ou droits insuffisants).")
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
            st.error(f"❌ Erreur lors de l'écriture : {e}")
            return False

    def load_user_audits(self, user_email):
        if not self.sheet: return []
        try:
            ws = self.get_or_create_worksheet("audits")
            records = ws.get_all_records()
            return [r for r in records if r.get('user_email') == user_email]
        except:
            return []
