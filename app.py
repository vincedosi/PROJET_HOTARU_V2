import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(layout="wide", page_title="HOTARU DIAGNOSTIC")

def test_connection():
    st.title("🕵️‍♂️ DIAGNOSTIC DE CONNEXION")
    
    # 1. TEST DE LECTURE DES SECRETS
    st.subheader("1. Lecture du fichier secrets.toml")
    
    # Test URL
    if "sheet_url" in st.secrets:
        url = st.secrets["sheet_url"]
        st.success(f"✅ URL trouvée : {url}")
    elif "url" in st.secrets:
        url = st.secrets["url"]
        st.warning(f"⚠️ URL trouvée sous le nom 'url' (au lieu de 'sheet_url') : {url}")
    else:
        st.error("❌ AUCUNE URL TROUVÉE à la racine des secrets.")
        url = None

    # Test JSON Robot
    if "gcp_service_account" in st.secrets:
        st.success("✅ Section [gcp_service_account] détectée.")
        email = st.secrets["gcp_service_account"].get("client_email")
        st.info(f"🤖 Email du robot : {email}")
        
        if email:
            st.markdown(f"""
            ### 👉 ACTION REQUISE :
            Assurez-vous que cet email est bien **ÉDITEUR** du fichier Google Sheet :
            **`{email}`**
            """)
    else:
        st.error("❌ Section [gcp_service_account] INTROUVABLE.")
        return

    # 2. TEST DE CONNEXION REEL
    st.subheader("2. Tentative de Connexion Google")
    
    if st.button("Lancer le test de connexion"):
        try:
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scope)
            client = gspread.authorize(creds)
            
            st.write("🔑 Authentification réussie...")
            
            if url:
                st.write(f"📂 Tentative d'ouverture du fichier...")
                sh = client.open_by_url(url)
                st.success(f"✅ VICTOIRE ! Connecté au fichier : '{sh.title}'")
                
                ws = sh.sheet1
                st.write(f"📄 Premier onglet : '{ws.title}'")
                st.balloons()
            else:
                st.error("Pas d'URL à tester.")

        except gspread.exceptions.APIError as e:
            st.error("❌ ERREUR API GOOGLE (Problème de droits ou API désactivée)")
            st.code(e)
            st.warning("Conseil : Vérifiez que 'Google Drive API' et 'Google Sheets API' sont activées dans la console Google Cloud.")
            
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("❌ FICHIER NON TROUVÉ")
            st.warning("Le robot est connecté, mais il ne voit pas le fichier. Avez-vous bien partagé le fichier avec lui ?")
            
        except Exception as e:
            st.error("❌ ERREUR TECHNIQUE")
            st.code(f"{type(e).__name__}: {e}")

if __name__ == "__main__":
    test_connection()
