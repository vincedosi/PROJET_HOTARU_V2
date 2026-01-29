PROBLÈMES À RÉSOUDRE :

Navigation : Actuellement, on ne peut pas revenir en arrière. Je veux une sidebar fixe avec des onglets (, Audit , Rapports, Paramètres).

Scraping Intelligent (Smart Sampling) : Le crawler actuel sature sur les sites e-commerce ou institutionnels (ex: 500 fiches produits ou 500 CIRFA).

Feedback IA : La phase de catégorisation via l'API Mistral manque de feedback visuel (Barre de progression).

MISSIONS POUR CLAUDE :

Système de Navigation "SaaS"
Modifie app.py pour implémenter une sidebar de navigation propre.
Utilise des st.session_state pour mémoriser l'onglet actif afin que l'utilisateur ne perde pas ses données d'audit en changeant de page.

Ajoute le logo (assets/logo.png) en haut de cette sidebar.

Logique de "Smart Sampling" (Échantillonnage)
Avant de lancer l'analyse IA, crée une fonction detect_page_templates(urls).
Logique : Si 50 pages partagent la même structure d'URL (ex: /produit/* ou /recrutement/cirfa/*), n'analyse avec Mistral/OpenAI que 3 spécimens de ce groupe.

Pour les autres pages du groupe, "hérite" des scores et recommandations du groupe pour construire le graphique sans dépenser de jetons API.

Intégration Mistral & Visualisation
Pour rappel on construit d abord un schéma scraping brut puis on lance via OPtimiser via IA et on reconstruit alore graphique
Lors de la phase de "Regroupement Intelligent" par Mistral, implémente une st.progress() bar et un message de statut (st.status) pour informer l'utilisateur.

Le graphique (Graphe Organigramme) doit regrouper ces "fiches identiques" sous un seul nœud parent extensible ou un "cluster" pour que la vue reste claire (comme un organigramme propre).

Rappel toi aussi que tu dois mettre le lien de la page web et pourvoir s'y rendre en cliquant sur le noeud

UI/UX "Zen"
Applique un style CSS strict :
Fond blanc partout (background-color: #FFFFFF).

Boutons avec bordures noires de 1px et coins arrondis.

Utilise une police sans-serif très légère.

Supprime tous les éléments de décoration inutiles de Streamlit.

INSTRUCTIONS DE CODAGE :
Analyse mon fichier de crawl actuel.

Propose une modification du script de scraping pour inclure la détection de patterns d'URL (Regex intelligente).

Génère le code de la sidebar de navigation.

Intègre la barre de progression dans la fonction qui appelle l'API Mistral.

LANCE L'AMÉLIORATION DE LA NAVIGATION ET LA LOGIQUE DE SAMPLING MAINTENANT.

et complète le README.MD en expliquant le but du projet.
et qu 'on développe une app streamlit dans une ogique d e saas
