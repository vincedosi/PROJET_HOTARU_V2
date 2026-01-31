"""
DATABASE MANAGER (v1.0.0)
- Supporte la compression zlib/base64 pour les gros audits.
- Gestion des rôles (Admin/User).
- Recherche d'URL flexible dans les secrets.
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
        
        # 1. Vérification des secrets
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets [gcp_service_account] manquants.")
            return

        try:
            # 2. Authentification
            self.creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=self.scopes
            )
            self.client = gspread.authorize(self.creds)
            
            # 3. Récupération de l'URL du Sheet
            url = st.secrets.get("sheet_url") or st.secrets.get("url")
            if url:
                self.sheet = self.client.open_by_url(url)
            else:
                st.error("❌ 'sheet_url' introuvable dans les secrets.")
        except Exception as e:
            st.error(f"❌ Erreur de connexion GSheets : {e}")

    def get_or_create_worksheet(self, name="audits"):
        if not self.sheet: return None
        try:
            return self.sheet.worksheet(name)
        except:
            # Création de l'onglet avec les colonnes nécessaires
            ws = self.sheet.add_worksheet(title=name, rows=1000, cols=6)
            ws.append_row(["audit_id", "user_email", "date", "site_url", "nb_pages", "data_compressed"])
            return ws

    def save_audit(self, user_email, site_url, full_payload, stats):
        """Sauvegarde avec compression pour éviter l'erreur 400 GSheets."""
        if not self.sheet: return False
        try:
            ws = self.get_or_create_worksheet("audits")
            
            # --- COMPRESSION ---
            json_data = json.dumps(full_payload)
            compressed = zlib.compress(json_data.encode('utf-8'))
            safe_string = base64.b64encode(compressed).decode('utf-8')
            
            # Sécurité si l'audit est monstrueux
            if len(safe_string) > 49000:
                st.warning("⚠️ Audit très volumineux. Réduction aux 50 premières pages.")
                full_payload['results'] = full_payload['results'][:50]
                return self.save_audit(user_email, site_url, full_payload, stats)

            ws.append_row([
                datetime.now().strftime('%Y%m%d%H%M%S'),
                user_email.strip(),
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
        """Charge et décompresse les audits de l'utilisateur."""
        if not self.sheet: return []
        try:
            ws = self.get_or_create_worksheet("audits")
            records = ws.get_all_records()
            
            # Filtrage selon le rôle
            if is_admin:
                filtered = records
            else:
                filtered = [r for r in records if str(r.get('user_email')).strip() == user_email.strip()]
            
            # Décompression des données
            for r in filtered:
                try:
                    # Gère les deux colonnes possibles (transition)
                    raw_val = r.get('data_compressed') or r.get('json_data')
                    if not raw_val: continue
                    
                    if str(raw_val).startswith('{'):
                        # Ancien format non compressé
                        r['json_data'] = json.loads(raw_val)
                    else:
                        # Nouveau format compressé
                        decoded = base64.b64decode(raw_val)
                        decompressed = zlib.decompress(decoded).decode('utf-8')
                        r['json_data'] = json.loads(decompressed)
                except Exception:
                    continue
            return filtered
        except Exception as e:
            st.error(f"❌ Erreur de chargement : {e}")
            return []
