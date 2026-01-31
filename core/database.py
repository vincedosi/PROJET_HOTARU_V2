"""
DATABASE MANAGER (v1.1.0 - SUPER ADMIN MODE)
- Supporte la compression zlib/base64.
- Bypass le filtrage email pour le rôle 'admin'.
- Gestion robuste des erreurs de décompression.
"""
import streamlit as st
import json
import zlib
import base64
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
        
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Erreur : Section [gcp_service_account] introuvable dans les secrets.")
            return

        try:
            # Authentification via les secrets Streamlit
            self.creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=self.scopes
            )
            self.client = gspread.authorize(self.creds)
            
            # Récupération de l'URL du Google Sheet
            url = st.secrets.get("sheet_url") or st.secrets.get("url")
            if url:
                self.sheet = self.client.open_by_url(url)
            else:
                st.error("❌ Erreur : URL du Google Sheet (sheet_url) manquante dans les secrets.")
        except Exception as e:
            st.error(f"❌ Erreur de connexion GSheets : {e}")

    def get_or_create_worksheet(self, name="audits"):
        """Récupère l'onglet 'audits' ou le crée s'il est absent."""
        if not self.sheet: return None
        try:
            return self.sheet.worksheet(name)
        except:
            ws = self.sheet.add_worksheet(title=name, rows=1000, cols=6)
            ws.append_row(["audit_id", "user_email", "date", "site_url", "nb_pages", "data_compressed"])
            return ws

    def save_audit(self, user_email, site_url, full_payload, stats):
        """Compresse et sauvegarde l'audit complet dans Google Sheets."""
        if not self.sheet: return False
        try:
            ws = self.get_or_create_worksheet("audits")
            
            # Compression JSON pour passer sous la limite des 50k caractères
            json_data = json.dumps(full_payload)
            compressed = zlib.compress(json_data.encode('utf-8'))
            safe_string = base64.b64encode(compressed).decode('utf-8')
            
            # Sécurité anti-débordement
            if len(safe_string) > 49500:
                st.warning("⚠️ Audit trop lourd. Sauvegarde partielle (Top 50 pages).")
                full_payload['results'] = full_payload['results'][:50]
                return self.save_audit(user_email, site_url, full_payload, stats)

            ws.append_row([
                datetime.now().strftime('%Y%m%d%H%M%S'),
                user_email.strip().lower(),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                site_url,
                stats.get('total_urls', 0),
                safe_string
            ])
            return True
        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde : {e}")
            return False

    def load_user_audits(self, user_email, is_admin=False):
        """
        Charge les audits. 
        Si is_admin est True, récupère TOUTES les lignes sans exception.
        """
        if not self.sheet: return []
        try:
            ws = self.get_or_create_worksheet("audits")
            records = ws.get_all_records()
            
            filtered = []
            for r in records:
                # --- LOGIQUE DE FILTRAGE ---
                if is_admin:
                    # En mode admin, on ne pose pas de question, on prend tout
                    filtered.append(r)
                else:
                    # En mode user, comparaison flexible (gère les emails tronqués)
                    db_email = str(r.get('user_email', '')).strip().lower()
                    current_user = user_email.strip().lower()
                    if current_user in db_email or db_email in current_user:
                        filtered.append(r)
            
            # --- DÉCOMPRESSION DES DONNÉES ---
            for r in filtered:
                try:
                    raw_val = r.get('data_compressed') or r.get('json_data')
                    if not raw_val: continue
                    
                    if str(raw_val).startswith('{'):
                        # Cas des anciennes données non compressées
                        r['json_data'] = json.loads(raw_val)
                    else:
                        # Nouveau format compressé
                        decoded = base64.b64decode(raw_val)
                        decompressed = zlib.decompress(decoded).decode('utf-8')
                        r['json_data'] = json.loads(decompressed)
                except Exception:
                    # On ignore les lignes corrompues
                    continue
            return filtered
        except Exception as e:
            st.error(f"❌ Erreur de chargement de l'historique : {e}")
            return []
