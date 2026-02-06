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
    if isinstance(cluster_data, dict):
        for c_id, data in cluster_data.items():
            # Gestion sécurisée des formats de données
            if isinstance(data, dict) and 'samples' in data:
                samples = data['samples']
            elif isinstance(data, list):
                samples = data
            else:
                samples = []
            # Affichage enrichi : URL, Titre, H1
            samples_lines = []
            for s in samples[:3]:
                if isinstance(s, dict):
                    url = s.get('url', '')
                    title = s.get('title', '') or ''
                    h1 = s.get('h1', '') or ''
                    samples_lines.append(f"- URL: {url}\n  Titre: {title}\n  H1: {h1}")
                else:
                    samples_lines.append(f"- URL: {s}")
            examples_text += f"\nGROUPE ID: {c_id}\nSAMPLES:\n" + "\n".join(samples_lines) + "\n"

    return f"""
Tu es un Architecte de l'Information expert en UX.
Ta mission : Analyser des groupes de pages web (chaque groupe contient plusieurs pages similaires). Pour chaque groupe, tu reçois 3 exemples avec leur URL, leur <title> et leur <h1>.

RÈGLES STRICTES :
1. Analyse les points communs entre les titres, h1 et URLs de chaque groupe.
2. Trouve un nom de catégorie métier court (2-4 mots max) qui représente la valeur métier (ex: 'Meubles de Bureau' au lieu de 'Produits').
3. Ajoute un ÉMOJI pertinent au début.
4. Réponds UNIQUEMENT ligne par ligne sous le format : ID: RESULTAT
5. PAS DE BLABLA, PAS D'INTRODUCTION, PAS DE JSON.

EXEMPLE DE RÉPONSE ATTENDUE :
group_1: 🛋️ Canapés & Fauteuils
group_2: 🍽️ Cuisines Équipées
group_3: 📝 Conseils & Guides

A TOI DE JOUER :
{examples_text}
"""

def analyze_clusters_with_mistral(cluster_data):
    """
    Envoie les clusters à Mistral et récupère les noms via Parsing Texte Simple.
    """
    try:
        api_key = st.secrets["mistral"]["api_key"]
    except Exception:
        api_key = None

    if not api_key:
        st.warning("Clé API Mistral manquante dans les secrets Streamlit.")
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
