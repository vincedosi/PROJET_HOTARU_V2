"""
MODULE: DASHBOARD
Affiche la version actuelle, le changelog et un résumé de l'activité.
"""
import streamlit as st
from datetime import datetime

def render_dashboard():
    # En-tête avec Version
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Tableau de Bord")
        st.caption("Vue d'ensemble et mises à jour du système.")
    with col2:
        # Badge de version stylé
        st.markdown("""
            <div style="text-align: right; padding: 10px;">
                <span style="
                    background-color: #000; 
                    color: #fff; 
                    padding: 5px 12px; 
                    border-radius: 20px; 
                    font-size: 0.9rem; 
                    font-weight: bold;
                ">v0.9.0 Beta</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- SECTION 1 : STATUT SYSTEME ---
    # On récupère les infos de session s'il y a un audit en cours
    if 'current_stats' in st.session_state and st.session_state.current_stats:
        stats = st.session_state.current_stats
        url = st.session_state.get('audit_url_input', 'Inconnu')
        
        st.subheader("📊 Dernier Audit Actif")
        c1, c2, c3 = st.columns(3)
        c1.metric("Cible", url.replace("https://", "").replace("http://", "")[:20]+"...")
        c2.metric("Pages Scannées", stats.get('total_urls', 0))
        c3.metric("Stacks Identifiées", stats.get('patterns', 0))
        
        st.info("💡 Pour sauvegarder ces données, allez dans l'onglet 'Audit GEO' > Sauvegarder.")
        st.markdown("---")

    # --- SECTION 2 : JOURNAL DES VERSIONS (CHANGELOG) ---
    st.subheader("📜 Journal de Version")
    
    with st.container():
        # VERSION ACTUELLE
        with st.expander("v0.9.0 - La Mise à Jour 'Deep Dive' (Actuelle)", expanded=True):
            st.markdown("""
            **Date :** 31 Janvier 2026
            
            Cette version majeure transforme la capacité d'analyse de l'outil.
            
            * **🕷️ Nouveau Crawler Hybride :** HOTARU ne dépend plus uniquement des Sitemaps. Il est désormais capable de suivre les liens internes (Crawl Récursif) pour cartographier des sites complexes comme `sengager.fr` ou `ikea.com`.
            * **📚 Graphe 'Stacks' :** Finis les nuages de points illisibles. Les groupes de plus de 5 pages sont automatiquement empilés en "Stacks" pour une visualisation claire.
            * **💾 Sauvegarde Cloud :** Vos audits sont maintenant sauvegardés dans Google Sheets et peuvent être rechargés à tout moment.
            * **🏷️ Naming IA Avancé :** L'IA utilise désormais les vrais `<title>` et `<h1>` des pages pour nommer les dossiers, et plus seulement les URLs.
            """)

        # VERSIONS PRECEDENTES
        with st.expander("v0.8.5 - Refonte UX/UI"):
            st.markdown("""
            **Date :** 30 Janvier 2026
            * **🎨 Design Zen :** Nouvelle interface noir & blanc épurée.
            * **🧭 Top Navigation :** Suppression de la sidebar latérale instable au profit d'une barre de navigation horizontale robuste.
            * **⚡ Fix PyVis :** Résolution du bug de clic sur le graphe (ouverture des liens dans un nouvel onglet).
            """)
            
        with st.expander("v0.1.0 - Alpha"):
            st.markdown("""
            * Lancement initial du prototype.
            * Analyse basique via Sitemap.
            * Connexion API Mistral.
            """)

    # --- SECTION 3 : ROADMAP ---
    st.markdown("---")
    st.caption("🚀 Prochainement : Export PDF, Analyse de Contenu Sémantique, Multi-agents.")
