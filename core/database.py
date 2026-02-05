import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import time
import datetime
import zlib
import base64

# =============================================================================
# 👇 ECRIVEZ L'URL DE VOTRE GOOGLE SHEET ICI (Entre les guillemets)
# =============================================================================
Target_Sheet_URL = "https://docs.google.com/spreadsheets/d/1WVwJPO9augvBLqujng6Aqw3pUmClFsWJutmCa75ucCw/edit?usp=sharing" 
# ⚠️ Remplacez l'URL ci-dessus par la VÔTRE (celle de votre navigateur)
# =============================================================================

class AuditDatabase:
    def __init__(self):
        # Configuration des droits d'accès
        self.scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

        # Chargement des credentials depuis les secrets Streamlit
        try:
            self.creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=self.scope)
            self.client = gspread.authorize(self.creds)
        except Exception as e:
            st.error(f"Erreur de configuration Secrets (GCP): {e}")
            self.client = None
            self.sheet_file = None
            self.sheet = None
            return

        # Connexion au Fichier Google Sheet
        try:
            self.sheet_file = self.client.open_by_url(Target_Sheet_URL)
            
            # 🎯 CIBLAGE DE L'ONGLET 'audits' (Vu sur votre capture d'écran)
            try:
                self.sheet = self.sheet_file.worksheet("audits")
            except:
                # Si l'onglet 'audits' n'existe pas, on prend le premier par défaut
                self.sheet = self.sheet_file.sheet1
                
        except Exception as e:
            st.error(f"Impossible d'ouvrir le GSheet. Vérifiez l'URL ligne 13 de core/database.py.\nErreur: {e}")
            self.sheet = None

    def load_user_audits(self, user_email):
        """Charge les audits. FILTRE DÉSACTIVÉ pour débogage."""
        if not self.sheet:
            return []
            
        try:
            # Récupère toutes les données de la feuille
            all_rows = self.sheet.get_all_values()

            # S'il n'y a pas de données (juste les en-têtes ou vide)
            if len(all_rows) < 2:
                return []
                
            data_rows = all_rows[1:] # On ignore la ligne 1 (Titres)
            user_audits = []

            # On parcourt chaque ligne
            for row in data_rows:
                # Sécurité anti-ligne vide
                if len(row) < 2: 
                    continue

                # --- RECUPERATION DES DONNEES ---
                workspace_value = row[2] if len(row) > 2 else ""
                
                audit = {
                    "audit_id": row[0],
                    "user_email": row[1],
                    # Si la case workspace est vide ou n'existe pas, on met "Non classé"
                    "workspace": workspace_value.strip() if workspace_value.strip() != "" else "Non classé",
                    "date": row[3] if len(row) > 3 else "",
                    "site_url": row[4] if len(row) > 4 else "",
                    "nb_pages": row[5] if len(row) > 5 else 0,
                    "data_compressed": row[6] if len(row) > 6 else "",
                    "nom_site": row[7] if len(row) > 7 else "Site Inconnu"
                }
                user_audits.append(audit)
            
            return user_audits

        except Exception as e:
            st.error(f"Erreur lors de la lecture des audits : {e}")
            return []

    def save_audit(self, user_email, workspace, site_url, nom_site, json_data):
        """Sauvegarde un nouvel audit dans la feuille"""
        if not self.sheet:
            st.error("Impossible de sauvegarder : connexion à la base de données échouée")
            return False
            
        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            audit_id = f"{int(time.time())}"
            
            # Compression des données JSON pour que ça tienne dans une cellule
            json_str = json.dumps(json_data)
            compressed = base64.b64encode(zlib.compress(json_str.encode('utf-8'))).decode('ascii')
            
            # Gestion du nom du workspace
            final_ws = workspace if workspace and workspace.strip() != "" else "Non classé"
            
            # Création de la ligne à ajouter (Respect strict de l'ordre des colonnes A->H)
            new_row = [
                audit_id,       # A
                user_email,     # B
                final_ws,       # C
                date_str,       # D
                site_url,       # E
                len(json_data.get('results', [])), # F
                compressed,     # G
                nom_site        # H
            ]
            
            self.sheet.append_row(new_row)
            return True
            
        except Exception as e:
            st.error(f"Erreur de sauvegarde GSheet : {e}")
            return False
