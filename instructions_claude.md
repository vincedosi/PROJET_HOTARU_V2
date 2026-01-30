🏮 PROJECT HOTARU V3 - MASTER INSTRUCTIONS (FIX & FINAL)
1. UX & NAVIGATION (RÉPARATION URGENTE)
Problème actuel : La sidebar disparaît après les interactions et l'interface manque de structure.

A. Sidebar Persistante (Sidebar Fixe)
Modifie app.py. La Sidebar doit être codée au tout début du script, avant toute logique de page.

Contenu :

Logo assets/logo.png (centré, fond blanc).

Menu de navigation (st.radio ou boutons) :

📊 Dashboard (Accueil, KPIs).

🔍 Audit GEO (Le scanner).

⚙️ Paramètres (Clés API & Profil).

Mécanisme : Utilise st.session_state pour stocker l'onglet actif. Si je clique sur "Analyser" dans l'Audit, la sidebar DOIT rester visible.

B. Design System "Zen"
Fond 100% Blanc. Bordures noires fines (1px). Pas d'ombres.

Suppression des éléments décoratifs Streamlit par défaut.

2. GRAPHE INTERACTIF (CORRECTION DU CLIC)
Problème critique : Le clic sur un nœud recharge l'app avec une URL interne erronée (/component/streamlit_agraph...). Solution : Utiliser PyVis avec injection JavaScript manuelle. Abandonner streamlit-agraph.

Implémentation technique OBLIGATOIRE :
Dans modules/audit_geo.py, tu dois générer le graphe comme ceci pour que les liens externes fonctionnent :

Générer le fichier HTML via net.save_graph("temp.html").

Lire le HTML en string.

Injecter ce script JS avant la balise </body> :

JavaScript
<script type="text/javascript">
    network.on("click", function (params) {
        if (params.nodes.length > 0) {
            var nodeId = params.nodes[0];
            var node = nodes.get(nodeId);
            // Ouvre le lien dans un nouvel onglet
            if (node.url && node.url.startsWith("http")) {
                window.open(node.url, '_blank');
            }
        }
    });
</script>
Afficher avec streamlit.components.v1.html(html_content, height=700).

3. SMART CRAWLER (STOP AUX SPAGHETTIS)
Problème actuel : Noms de groupes illisibles (?$(102)) et trop de nœuds.

A. Logique de Clustering (Regex)
Dans core/scraper.py :

Analyser les URLs. Si un dossier (ex: /offres/) contient > 5 pages :

Créer un Cluster Virtuel.

Ne scraper que 3 pages de ce groupe.

Nommage Propre : Le nom du cluster doit être le segment d'URL nettoyé.

Mauvais : ?, \d+, groupe_1.

Bon : /offres/job-123 -> Nom: "OFFRES". (Regex: [a-zA-Z]{3,})

Si le nom est vide, mettre "DIVERS".

B. Logs Visuels
Afficher un st.expander("Journal d'activité", expanded=True) qui montre la progression : [INFO] Cluster détecté : 'OFFRES' (102 pages).

4. GESTION DES DONNÉES (SAAS)
Onglet Audit : Doit avoir une barre d'actions en haut :

[Charger un Audit] (Depuis GSheets).

[Sauvegarder] (Envoie le JSON compressé dans GSheets).

Paramètres (Vault) : Formulaire sécurisé pour entrer les clés API (Mistral/OpenAI). Les stocker chiffrées dans GSheets ou en session, mais ne plus les demander à chaque fois.

5. ORDRE D'EXÉCUTION POUR LE CODE
Refais app.py pour garantir la Sidebar.

Corrige core/scraper.py pour avoir des noms de clusters lisibles.

Refais le rendu graphique dans modules/audit_geo.py avec le Fix JavaScript pour les liens.

Ajoute les boutons Save/Load connectés à GSheets.
