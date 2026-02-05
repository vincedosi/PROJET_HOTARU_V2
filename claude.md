🏮 PROJECT HOTARU V3 - MASTER INSTRUCTIONS (SaaS & Smart Architecture)
1. VISION & DESIGN SYSTEM ("ZEN JAPONAIS")
Philosophie : Minimalisme radical. Tout ce qui n'est pas essentiel disparaît.

Palette : Fond 100% Blanc (#FFFFFF), Textes et Lignes Noir Pur (#000000).

Composants :

Boutons : Fond blanc, bordure noire fine (1px), coins arrondis, texte noir. (Inversion noir/blanc au survol).

Inputs : Lignes simples (border-bottom only) ou contours très fins.

Sidebar : Fond blanc pur. Logo assets/logo.png centré en haut.

Layout : Navigation par onglets persistants (Tabs) gérés via st.session_state.

2. NAVIGATION & SÉCURITÉ (SaaS)
A. Structure de la Sidebar
En-tête : Logo Hotaru.

Menu :

🔍 AUDIT GEO (Cœur du système)

🛠️ TRANSFORMATION (Module futur)

⚙️ PARAMÈTRES (Clés & Profil)

Pied de page : Avatar utilisateur + Bouton Déconnexion.

B. Gestion des Données (Data Isolation)
Cloisonnement : Un utilisateur ne voit QUE ses propres audits. Filtrage strict par user_id dans toutes les requêtes Database.

Admin : Seul le rôle 'admin' peut voir les statistiques globales.

C. Le "Vault" (Clés API)
Problème : Ne plus demander les clés à chaque session.

Solution :

Dans l'onglet Paramètres, formulaire pour entrer les clés (Mistral, OpenAI).

Chiffrer les clés avant de les stocker dans la colonne api_vault de Google Sheets (Table users).

Au login, déchiffrer silencieusement et charger dans la session.

3. CŒUR DU SYSTÈME : LE "SMART ARCHITECT" (Phase 1)
Objectif : Cartographier un site sans le scorer. Transformer 1000 URLs en un organigramme lisible de ~15 clusters nommés.

Étape A : Découverte & Clustering (Code Python)
Sitemap First : Tenter de lire sitemap.xml. Si échec, crawler les liens internes.

Pattern Matching (Regex) :

Analyser les URLs pour trouver des répétitions (/produit/id-1, /produit/id-2).

Regrouper ces URLs dans des "Clusters Virtuels".

Smart Sampling :

Si un cluster > 5 pages : Ne garder que 3 spécimens pour l'analyse.

Les autres sont comptabilisés mais ignorés (Économie massive de tokens).

Étape B : Renommage Intelligent (API Mistral)
Ne pas calculer de score GEO maintenant. Utiliser l'IA uniquement pour structurer.

Prompt Système : "Tu es un Architecte de l'Information. Analyse ces 3 URLs et titres d'un même groupe. Donne un nom de catégorie court et descriptif (ex: 'Fiches Produits', 'Blog', 'Mentions Légales'). Réponds uniquement le nom."

Résultat : Le nœud du graphe s'appellera "📦 Fiches Produits (540 pages)" et non une URL brute.

Étape C : Visualisation & UX
Graphe Interactif :

Fond blanc. Nœuds rectangulaires.

Labels : Le nom généré par Mistral.

Clic : Ouvre un panneau latéral listant les 3 URLs échantillons (cliquables).

Console de Logs (Effet Hacker) :

Afficher un st.expander("Journal d'activité") qui montre les logs en temps réel :

[INFO] Cluster détecté : /blog/* (120 pages)

[IA] Mistral a renommé le cluster -> "Actualités"

4. DATABASE & VERSIONING (Google Sheets)
Table audits :

Colonnes : audit_id, user_id, site_url, timestamp, graph_data_json (Compressé), status (Structure Only / Scored).

Save/Load :

Bouton "Sauvegarder l'architecture" après l'analyse Mistral.

Dashboard d'accueil (Onglet Audit) : Tableau des audits passés avec bouton "Charger".

5. INSTRUCTIONS DE CODAGE IMMÉDIATES
Architecture : Crée la navigation app.py et l'injection CSS assets/style.css.

Settings : Implémente le "Vault" pour sécuriser les clés API dans GSheets.

Core Scraper : Code la logique de Clustering/Sampling (Regex) + Lecture Sitemap.

AI Engine : Implémente uniquement le prompt de "Renommage de catégorie".

EXÉCUTION : Commence par la structure SaaS (Nav + Vault) puis attaque le Smart Scraper.
