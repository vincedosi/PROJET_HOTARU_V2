"""
HOTARU - Bloc Méthodologie (Authority Score)
Contenu Markdown unique affiché dans l'onglet Méthodologie des modules concernés.
"""

import streamlit as st

METHODOLOGIE_AUTHORITY_MD = """
## Synthèse : L'AI Authority Index en bref

L'indice repose sur une réalité technique : les IA ne \"devinent\" pas qui est une autorité, elles compilent des preuves structurées et citées. Notre algorithme scanne **5 piliers stratégiques** pour calculer un score sur 100 :

1. **Knowledge Graph (30%)** : L'entité existe-t-elle dans la base de données universelle (Wikidata) ?
2. **Données Structurées (25%)** : Le site parle-t-il le \"langage machine\" (JSON-LD) ?
3. **Autorité de Citation (20%)** : La marque est-elle référencée par des tiers de confiance (Wikipedia, réseaux sociaux) ?
4. **Complétude Sémantique (15%)** : Le contenu couvre-t-il tout le champ lexical de son expertise ?
5. **Fraîcheur (10%)** : Les informations sont-elles à jour pour éviter les hallucinations ?

**Objectif :** Plus le score est élevé, plus la probabilité que l'IA cite votre marque comme référence lors d'une requête utilisateur est forte.

---

## Méthodologie Détaillée

### 1. Couverture Knowledge Graph (Poids : 30%)

C’est le socle de l'identité numérique. Les LLMs utilisent des bases de connaissances comme **Wikidata** pour relier les concepts entre eux.

* **Ce que le code vérifie :** La présence d'un identifiant unique (**QID**).
* **Indicateurs de performance :**
  * Nombre de propriétés renseignées (ex: fondateur, date de création).
  * Présence d'un lien vers une page Wikipedia associée.
  * Nombre de \"claims\" (affirmations) sourcées par des références externes.

* **Impact IA :** Une entité absente de Wikidata est souvent considérée comme une \"simple chaîne de caractères\" et non comme une entité réelle par les modèles d'IA.

### 2. Empreinte des Données Structurées (Poids : 25%)

Les LLMs préfèrent les données organisées. Le balisage **Schema.org** en format **JSON-LD** permet d'injecter du sens directement dans le code sans ambiguïté.

* **Ce que le code vérifie :** Il scanne jusqu'à 50 pages du site pour détecter les scripts `ld+json`.
* **Indicateurs de performance :**
  * Pourcentage de pages balisées.
  * Diversité des types utilisés (`Organization`, `Article`, `FAQPage`, `Product`).
  * Présence cruciale du type `Organization` sur la page d'accueil.

* **Impact IA :** Cela aide l'IA à extraire des faits précis (prix, auteur, localisation) sans risque d'erreur d'interprétation.

### 3. Autorité de Citation & Confiance (Poids : 20%)

Ici, on mesure la preuve sociale et la crédibilité technique.

* **Ce que le code vérifie :**
  * **Mentions Wikipedia :** Recherche via l'API Wikipedia pour voir si le nom de l'entité apparaît dans des articles existants.
  * **Signaux de Réassurance :** Analyse de la page d'accueil à la recherche de mentions légales, politiques de confidentialité, et coordonnées (email/téléphone).
  * **Présence Sociale :** Détection des liens vers LinkedIn, Twitter, Facebook, etc.

* **Impact IA :** Les modèles sont entraînés pour privilégier les sources qui affichent des signaux de confiance (E-E-A-T).

### 4. Complétude Sémantique (Poids : 15%)

L'IA évalue si vous êtes un expert en observant la richesse de votre vocabulaire métier.

* **Ce que le code vérifie :** Extraction des termes clés via un algorithme de traitement de texte (**TF-IDF**).
* **Indicateurs de performance :**
  * Nombre de concepts uniques identifiés.
  * **Analyse concurrentielle :** Si des URLs concurrentes sont fournies, le code compare le \"recouvrement\" sémantique.

* **Impact IA :** Un contenu pauvre ou trop généraliste sera jugé moins pertinent qu'un site couvrant tout le spectre sémantique d'une thématique.

### 5. Fraîcheur du Contenu (Poids : 10%)

Une donnée périmée est une donnée risquée pour une IA.

* **Ce que le code vérifie :** Analyse du fichier `sitemap.xml` et des balises `lastmod`.
* **Indicateurs de performance :**
  * Âge moyen des pages en jours.
  * Date de la dernière publication détectée.

* **Impact IA :** Les modèles récents (avec accès web) privilégient les informations à jour pour répondre aux questions d'actualité.

---

## Interprétation des Résultats

| Score | Niveau d'Autorité | Impact LLM |
| --- | --- | --- |
| **80 - 100** | **Forte** | Référence prioritaire. Très haute probabilité de citation directe. |
| **60 - 79** | **Moyenne** | Autorité reconnue. Citation probable sur des requêtes spécifiques. |
| **40 - 59** | **Faible** | Présence détectée mais manque de preuves de confiance ou de structure. |
| **0 - 39** | **Très Faible** | \"Bruit de fond\". L'IA connaît le nom mais ne peut pas confirmer l'autorité. |

---
"""



# Contenu méthodologie par module (titre + texte court)
METHODOLOGIE_CONTENT = {
    "authority": {
        "title": "AUTHORITY SCORE — MÉTHODOLOGIE",
        "subtitle": "AI Authority Index // 5 piliers",
        "sections": [
            ("01. INDICATEUR", "L'AI Authority Index mesure la probabilité qu'une entité soit citée par les LLMs (ChatGPT, Claude, Perplexity). Score sur 100, basé sur 5 piliers pondérés."),
            ("02. LES 5 PILIERS", "Knowledge Graph (30 %) — Présence Wikidata. Structured Data (25 %) — JSON-LD. Citation Authority (20 %) — Wikipédia, backlinks. Semantic Completeness (15 %) — Richesse sémantique. Content Freshness (10 %) — Fraîcheur des données."),
            ("03. INTERPRÉTATION", "80+ : Autorité forte. 60–79 : Autorité moyenne. 40–59 : Autorité faible. < 40 : Très faible visibilité pour les LLMs."),
        ],
    },
    "master": {
        "title": "MASTER DATA — MÉTHODOLOGIE",
        "subtitle": "Données d'entité permanentes // JSON-LD",
        "sections": [
            ("01. OBJECTIF", "Construire une fiche entité (Organization) unique et fiable, alimentant le JSON-LD de toutes les pages. Source de vérité pour les moteurs et les LLMs."),
            ("02. SOURCES", "Wikidata (QID) pour l'identité et les faits. SIRET pour les entreprises françaises. Mistral AI pour l'enrichissement des champs (description, secteurs)."),
            ("03. EXPORT", "Le JSON-LD généré respecte le schéma Organization. Réutilisable dans les balises script type=\"application/ld+json\" sur l'ensemble du site."),
        ],
    },
    "leaf": {
        "title": "LEAF BUILDER — MÉTHODOLOGIE",
        "subtitle": "JSON-LD spécifique à la page",
        "sections": [
            ("01. PRINCIPE", "Chaque page peut porter un JSON-LD adapté à son contenu (Article, FAQPage, Product, etc.). LEAF combine le Master (entité) et les données dynamiques de la page."),
            ("02. ANALYSE IA", "Mistral analyse le contenu (titre, meta, H1) et prédit le type de page et les champs recommandés. Comparatif avant/après pour valider les changements."),
            ("03. USAGE", "Exporter le JSON-LD et l'intégrer dans la page. Vérifier la cohérence avec le Master Data pour garder une entité unique."),
        ],
    },
}


def render_methodologie_for_module(module_key: str):
    """
    Affiche le contenu Méthodologie pour un module (authority, master, leaf).
    Pour Authority Score : méthodologie détaillée (METHODOLOGIE_AUTHORITY_MD).
    Audit garde sa méthode dédiée dans audit_geo (METHODOLOGIE HOTARU complète).
    """
    if module_key == "authority":
        st.markdown(METHODOLOGIE_AUTHORITY_MD)
        return
    content = METHODOLOGIE_CONTENT.get(module_key)
    if not content:
        st.info("Méthodologie non définie pour ce module.")
        return

    st.markdown('<div class="methodo-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="methodo-title">{content["title"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="methodo-subtitle">{content["subtitle"]}</div>', unsafe_allow_html=True)

    for header, text in content["sections"]:
        st.markdown(f'<div class="methodo-header">{header}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="methodo-text">{text}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
