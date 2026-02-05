import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import hashlib

class AuthManager:
    """Gestionnaire d'authentification basé sur Google Sheets"""
    
    def __init__(self):
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        try:
            self.creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=self.scope
            )
            self.client = gspread.authorize(self.creds)
            
            # Connexion au Google Sheet
            sheet_url = st.secrets.get("sheet_url", "")
            if not sheet_url:
                st.error("❌ URL du Google Sheet manquante dans les secrets")
                self.sheet_file = None
                return
                
            self.sheet_file = self.client.open_by_url(sheet_url)
            
            # Récupération de l'onglet "users"
            try:
                self.users_sheet = self.sheet_file.worksheet("users")
            except:
                # Si l'onglet n'existe pas, on le crée avec un admin par défaut
                self.users_sheet = self.sheet_file.add_worksheet(
                    title="users",
                    rows=100,
                    cols=5
                )
                # En-têtes
                self.users_sheet.append_row(["email", "password_hash", "created_at", "last_login", "role"])
                
                # Création d'un compte admin par défaut
                # Mot de passe : "123"
                admin_hash = self._hash_password("123")
                self.users_sheet.append_row([
                    "admin@hotaru.app",
                    admin_hash,
                    "2025-02-02",
                    "",
                    "admin"
                ])
                
        except Exception as e:
            st.error(f"❌ Erreur d'initialisation AuthManager : {e}")
            self.sheet_file = None
    
    def _hash_password(self, password):
        """Hash un mot de passe avec SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def login(self, email, password):
        """Vérifie les identifiants de connexion"""
        if not self.sheet_file:
            st.error("❌ Base de données non connectée")
            return False
        
        try:
            # Récupère tous les utilisateurs
            all_users = self.users_sheet.get_all_records()
            
            # Hash du mot de passe saisi
            password_hash = self._hash_password(password)
            
            # Recherche de l'utilisateur
            for user in all_users:
                if user['email'].lower().strip() == email.lower().strip():
                    stored_hash = str(user['password_hash']).strip()
                    
                    # 🔥 MODE COMPATIBILITÉ : Accepte hash OU mot de passe en clair
                    if stored_hash == password_hash or stored_hash == password:
                        # Stocke le rôle de l'utilisateur
                        st.session_state.user_role = user.get('role', 'admin')
                        
                        # Met à jour last_login (optionnel)
                        try:
                            from datetime import datetime
                            row_index = all_users.index(user) + 2  # +2 car ligne 1 = headers
                            self.users_sheet.update_cell(row_index, 4, datetime.now().strftime("%Y-%m-%d %H:%M"))
                        except:
                            pass  # Si erreur, on continue quand même
                        
                        return True
                    else:
                        return False
            
            return False
            
        except Exception as e:
            st.error(f"Erreur de connexion : {e}")
            return False
    
    def register(self, email, password, role="user"):
        """Crée un nouveau compte utilisateur (réservé aux admins)"""
        if not self.sheet_file:
            return False
        
        try:
            # Vérifier si l'email existe déjà
            all_users = self.users_sheet.get_all_records()
            
            for user in all_users:
                if user['email'].lower() == email.lower():
                    st.error("❌ Cet email est déjà enregistré")
                    return False
            
            # Créer le compte
            password_hash = self._hash_password(password)
            from datetime import datetime
            self.users_sheet.append_row([
                email,
                password_hash,
                datetime.now().strftime("%Y-%m-%d"),
                "",
                role
            ])
            
            return True
            
        except Exception as e:
            st.error(f"Erreur d'inscription : {e}")
            return False
    
    def change_password(self, email, old_password, new_password):
        """Change le mot de passe d'un utilisateur"""
        if not self.sheet_file:
            return False
        
        try:
            all_users = self.users_sheet.get_all_values()
            
            old_hash = self._hash_password(old_password)
            new_hash = self._hash_password(new_password)
            
            # Recherche de l'utilisateur (commence à la ligne 2, ignore les en-têtes)
            for i, row in enumerate(all_users[1:], start=2):
                if row[0].lower() == email.lower():
                    # Vérif mot de passe actuel (hash OU clair)
                    if row[1] == old_hash or row[1] == old_password:
                        # Mise à jour du mot de passe
                        self.users_sheet.update_cell(i, 2, new_hash)
                        st.success("✅ Mot de passe modifié avec succès")
                        return True
                    else:
                        st.error("❌ Ancien mot de passe incorrect")
                        return False
            
            return False
            
        except Exception as e:
            st.error(f"Erreur de changement de mot de passe : {e}")
            return False
    
    def auto_migrate_passwords(self):
        """🔄 Convertit automatiquement les mots de passe en clair en hash (Admin uniquement)"""
        if not self.sheet_file:
            return False
        
        try:
            all_users = self.users_sheet.get_all_values()
            
            for i, row in enumerate(all_users[1:], start=2):
                password_field = row[1]
                
                # Si le mot de passe fait moins de 20 caractères, c'est probablement du clair
                if len(password_field) < 20:
                    new_hash = self._hash_password(password_field)
                    self.users_sheet.update_cell(i, 2, new_hash)
                    st.info(f"✅ Mot de passe hashé pour {row[0]}")
            
            st.success("✅ Migration des mots de passe terminée")
            return True
            
        except Exception as e:
            st.error(f"Erreur de migration : {e}")
            return False
