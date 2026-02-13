"""
HOTARU - Bloc Méthodologie (Authority Score)
Contenu Markdown unique affiché dans l'onglet Méthodologie des modules concernés.
"""

import streamlit as st

METHODOLOGIE_AUTHORITY_MD = """
## Synthèse : L'AI Authority Index (Version 2.0 - AI Native)

**La réalité technique :** Les IA génératives (LLMs) ne \"lisent\" pas le web comme des humains. Elles traitent des probabilités, des vecteurs et des entités.

Notre algorithme ne cherche pas à plaire à un moteur de recherche classique, il audite la **capacité de votre marque à être ingérée, comprise et restituée par une IA**.

Nous scannons **5 piliers techniques** pour calculer un **Score de Compatibilité IA** sur 100 :

1. **Ancrage Knowledge Graph (30%)** : L'entité existe-t-elle sans ambiguïté dans la mémoire de l'IA ?
2. **Interopérabilité des Données (25%)** : Le contenu est-il structuré pour être \"lu\" instantanément par les machines ?
3. **Autorité & Confiance (20%)** : La marque est-elle validée par les sources d'entraînement prioritaires ?
4. **Densité Vectorielle (15%)** : Le contenu couvre-t-il mathématiquement le cœur du sujet (sans bruit) ?
5. **Fraîcheur Temporelle (10%)** : L'information est-elle assez récente pour être sélectionnée par les agents de recherche (RAG) ?

---

## Méthodologie Détaillée

### 1. Ancrage Knowledge Graph (Poids : 30%)

**Le système d'identité de l'IA.** Pour une IA, s'il n'y a pas d'entité nommée, il n'y a que du texte. Nous vérifions si votre marque est reconnue comme une **\"Entité\"** (un objet unique avec des attributs) et non comme une simple chaîne de mots.

* **Ce que l'algo vérifie :** L'existence d'un nœud dans le Knowledge Graph universel (Wikidata) et la richesse de ses connexions.
* **Indicateurs Clés :**
  * Présence d'un ID unique (QID).
  * Interconnexions (Le graphe relie-t-il la marque à ses fondateurs, ses produits, son secteur ?).
  * Validation par des tiers (Sources fiables liées à l'entité).
* **Impact IA :** Une entité reconnue dans le Graph réduit drastiquement les hallucinations. L'IA \"sait\" de qui elle parle avant même de générer le premier mot.

### 2. Interopérabilité des Données (Poids : 25%)

**Le langage natif de la machine.**

Les LLMs modernes utilisent des outils de recherche (RAG) pour trouver l'info. Ces outils privilégient les données qui ne demandent aucun effort d'interprétation. Le **JSON-LD** est ce standard.

* **Ce que l'algo vérifie :** L'injection de données structurées (Schema.org) qui décrivent explicitement le contenu sans ambiguïté.
* **Indicateurs Clés :**
  * Couverture du balisage (Organization, Product, Person, FAQ).
  * Résolution des entités (Lier votre site à vos profils sociaux et Wikipedia via le code **sameAs**).
* **Impact IA :** Cela permet à l'IA d'extraire des faits (Prix, Auteur, Note) avec une confiance de 100%, sans avoir à \"deviner\" en lisant le texte visuel.

### 3. Autorité de Citation (Poids : 20%)

**La validation par le corpus d'entraînement.**

Les modèles sont entraînés à minimiser l'erreur. Ils accordent plus de \"poids\" statistique aux informations provenant de domaines à haute fiabilité (Universités, Gouvernement, Wikipédia, Presse de référence).

* **Ce que l'algo vérifie :** La présence de la marque dans des environnements numériques de haute confiance.
* **Indicateurs Clés :**
  * Mentions dans Wikipédia et sources académiques/officielles.
  * Cohérence des signaux de confiance sur le site (Pages \"À propos\", Politique de confidentialité claire, auteurs identifiés).
* **Impact IA :** L'IA considère ces sources comme la \"vérité terrain\". Être cité par elles transfère cette autorité à votre marque.

### 4. Densité Vectorielle & Sémantique (Poids : 15%)

**La compréhension du sens profond.**

Oubliez les mots-clés. Les IA fonctionnent par **Embeddings** (représentation mathématique du sens). Nous mesurons si votre contenu se situe mathématiquement au \"centre\" de votre sujet d'expertise.

* **Ce que l'algo vérifie :** Nous transformons votre contenu en vecteurs et calculons sa \"distance\" par rapport au concept idéal de votre expertise.
* **Indicateurs Clés :**
  * **Proximité Sémantique :** Votre contenu répond-il précisément à l'intention ou divague-t-il ?
  * **Densité d'Information :** Le ratio faits/mots. L'IA pénalise le \"remplissage\" marketing vide de sens.
  * **Couverture Contextuelle :** Le contenu aborde-t-il les sous-concepts logiques attendus par le modèle ?
* **Impact IA :** Un contenu avec une forte densité vectorielle \"active\" plus fortement les neurones du modèle liés à l'expertise, augmentant la probabilité d'être utilisé dans la réponse.

### 5. Fraîcheur Temporelle (Poids : 10%)

**La priorité de récupération.**

Les IA connectées au web (ChatGPT Search, Perplexity, Google AI Overviews) filtrent l'information par date pour répondre aux questions actuelles. Une information ancienne est souvent ignorée par sécurité.

* **Ce que l'algo vérifie :** La récence des mises à jour techniques et éditoriales.
* **Indicateurs Clés :**
  * Date de dernière modification (lastmod) dans le Sitemap.
  * Fréquence de mise à jour du contenu \"froid\".
* **Impact IA :** C'est un filtre binaire pour les agents de recherche (RAG). Si l'info est jugée obsolète, elle n'est même pas transmise au modèle pour analyse.

---

## Interprétation des Scores

| Score | Niveau d'Autorité IA | Conséquence pour la Marque |
| --- | --- | --- |
| **80 - 100** | **Référence \"Gold\"** | La marque est une entité racine. Très haute probabilité de citation directe et factuelle. |
| **60 - 79** | **Autorité Validée** | L'IA comprend le sujet. Citation probable si la requête est précise. |
| **40 - 59** | **Signal Faible** | L'IA détecte le contenu mais manque de preuves structurées pour lui faire confiance. Risque d'hallucination. |
| **0 - 39** | **Bruit de Fond** | Invisible pour les modèles. L'IA traitera le contenu comme du texte générique sans autorité. |

---

## Pourquoi cette méthodologie est unique ?

*\"Contrairement au SEO classique qui cherche à placer des mots-clés pour un moteur de recherche, cette méthodologie audite la **digestibilité de votre marque pour une intelligence artificielle**. Nous ne travaillons pas sur le positionnement d'une page, mais sur la **compréhension fondamentale de votre entreprise par les modèles qui façonneront le web de demain.**\"*
"""



# Contenu méthodologie par module (titre + texte court)
METHODOLOGIE_CONTENT = {
    "authority": {
        "title": "AUTHORITY SCORE — MÉTHODOLOGIE",
        "subtitle": "AI Authority Index v2.0 — AI Native // Score de Compatibilité IA",
        "sections": [
            ("01. INDICATEUR", "L'AI Authority Index (v2.0) audite la capacité de votre marque à être ingérée, comprise et restituée par les LLMs. Score sur 100, 5 piliers techniques."),
            ("02. LES 5 PILIERS", "Ancrage Knowledge Graph (30 %) — Interopérabilité des Données (25 %) — Autorité & Confiance (20 %) — Densité Vectorielle (15 %) — Fraîcheur Temporelle (10 %)."),
            ("03. INTERPRÉTATION", "80–100 : Référence Gold. 60–79 : Autorité validée. 40–59 : Signal faible. 0–39 : Bruit de fond, invisible pour les modèles."),
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
