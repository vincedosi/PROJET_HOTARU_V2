"""
AI CLUSTERING - MISTRAL API HANDLER
Mode: TEXTE BRUT (Robustesse maximale)
Objectif: Éviter les erreurs de parsing JSON "Unterminated string".
"""

import streamlit as st
import requests

def get_naming_prompt(cluster_data):
    """Génère un prompt simple pour le renommage."""
    
    # On prépare le texte des exemples pour l'IA
    examples_text = ""
    # On s'adapte à la structure de données (qu'elle soit une liste ou un dict)
    if isinstance(cluster_data, dict):
        for c_id, data in cluster_data.items():
            # Gestion sécurisée des formats de données
            if isinstance(data, dict) and 'samples' in data:
                samples = data['samples']
            elif isinstance(data, list):
                samples = data
            else:
                samples = []
                
            urls_sample = "\n".join([f"- {u}" for u in samples[:3]])
            examples_text += f"\nGROUPE ID: {c_id}\nURLS:\n{urls_sample}\n"

    return f"""
    Tu es un Architecte de l'Information expert en UX.
    Ta mission : Analyser des groupes d'URLs et leur donner un nom de catégorie court et pertinent.

    RÈGLES STRICTES :
    1. Trouve un nom court (2-4 mots max).
    2. Ajoute un ÉMOJI pertinent au début.
    3. Réponds UNIQUEMENT ligne par ligne sous le format : ID: RESULTAT
    4. PAS DE BLABLA, PAS D'INTRODUCTION, PAS DE JSON.

    EXEMPLE DE RÉPONSE ATTENDUE :
    group_1: 🛍️ Fiches Produits
    group_2: 📝 Articles de Blog
    group_3: ⚖️ Mentions Légales

    A TOI DE JOUER :
    {examples_text}
    """

def analyze_clusters_with_mistral(cluster_data):
    """
    Envoie les clusters à Mistral et récupère les noms via Parsing Texte Simple.
    """
    api_key = st.session_state.get('mistral_api_key')
    
    if not api_key:
        st.warning("⚠️ Clé API Mistral manquante. Allez dans l'onglet Config.")
        # On retourne les clusters tels quels sans renommage
        return {k: "Non analysé" for k in cluster_data.keys()}

    # Préparation du prompt
    prompt = get_naming_prompt(cluster_data)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "model": "mistral-tiny", # Modèle rapide et pas cher
        "messages": [
            {"role": "system", "content": "Tu es un assistant de classification web strict. Tu réponds ligne par ligne."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1, # Très faible pour être factuel
        "max_tokens": 1000
    }

    try:
        # Appel API
        response = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        
        result_json = response.json()
        raw_content = result_json["choices"][0]["message"]["content"]
        
        # --- PARSING ROBUSTE (TEXTE vs JSON) ---
        # On ne fait pas de json.loads(). On lit ligne par ligne.
        # C'est beaucoup plus résistant aux erreurs de coupure.
        
        renamed_categories = {}
        
        # Découpage ligne par ligne
        lines = raw_content.split('\n')
        
        for line in lines:
            if ":" in line:
                # On sépare au premier 'deux points'
                parts = line.split(":", 1)
                group_id = parts[0].strip()
                name = parts[1].strip()
                
                # Nettoyage basique (au cas où l'IA mettrait des guillemets)
                name = name.replace('"', '').replace("'", "").replace("`", "")
                
                # On enregistre le nom
                renamed_categories[group_id] = name
        
        return renamed_categories

    except Exception as e:
        st.error(f"Erreur API Mistral : {str(e)}")
        # En cas d'erreur, on renvoie un dict vide
        return {}
