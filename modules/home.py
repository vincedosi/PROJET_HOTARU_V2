import streamlit as st

def render_home_guide():
    # Style Hotaru 200% : Full White, Lignes ultra-fines, Typographie chirurgicale
    st.markdown("""
    <style>
        .hotaru-container {
            font-family: 'Inter', sans-serif;
            color: #0f172a;
            max-width: 900px;
            margin: auto;
            padding: 20px;
        }
        .hotaru-title {
            font-size: 2.8rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-bottom: 0.2rem;
            color: #000;
        }
        .hotaru-subtitle {
            font-size: 1.1rem;
            color: #94a3b8;
            margin-bottom: 4rem;
            font-weight: 400;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        .section-header {
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            color: #000;
            margin-bottom: 2rem;
            border-bottom: 2px solid #000;
            padding-bottom: 8px;
            width: fit-content;
        }
        .geo-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 30px;
            margin-bottom: -1px; /* Pour l'effet de grille collée */
            transition: all 0.2s ease;
        }
        .geo-card:hover {
            background: #f8fafc;
            z-index: 10;
            position: relative;
        }
        .badge {
            font-size: 0.65rem;
            font-weight: 800;
            color: #64748b;
            border: 1px solid #e2e8f0;
            padding: 2px 8px;
            margin-bottom: 15px;
            display: inline-block;
        }
        .grade-row {
            display: flex;
            justify-content: space-between;
            padding: 15px 0;
            border-bottom: 1px solid #f1f5f9;
        }
        .grade-letter { font-weight: 800; font-size: 1.2rem; }
        .grade-range { font-family: 'Mono', monospace; color: #64748b; }

        .health-visual {
            border: 1px solid #000;
            padding: 40px;
            margin: 50px 0;
            background: #fff;
        }
        .dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 10px; }
        
        .tips-list { list-style: none; padding: 0; }
        .tips-list li {
            padding: 15px 0;
            border-bottom: 1px solid #f1f5f9;
            color: #000;
            font-size: 1rem;
            display: flex;
            align-items: center;
        }
        .tips-list li::before {
            content: "";
            width: 12px;
            height: 1px;
            background: #000;
            margin-right: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="hotaru-container">', unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="hotaru-title">MÉTHODOLOGIE HOTARU</div>', unsafe_allow_html=True)
    st.markdown('<div class="hotaru-subtitle">2026 Framework</div>', unsafe_allow_html=True)

    # Intro
    st.markdown('<div class="section-header">01. CONCEPT</div>', unsafe_allow_html=True)
    st.write("L'optimisation des actifs sémantiques pour la citation directe par les LLMs.  Le score Hotaru mesure la capacité d'un contenu à être extrait et validé par les moteurs génératifs.")
    
    st.markdown('<div style="margin-bottom:4rem;"></div>', unsafe_allow_html=True)

    # Critères
    st.markdown('<div class="section-header">02. CRITÈRES D\'ANALYSE</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="geo-card">
            <div class="badge">15 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Meta Description</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Précision sémantique du résumé pour le crawling par les agents IA.</div>
        </div>
        <div class="geo-card">
            <div class="badge">15 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Données Structurées</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Schémas JSON-LD, identification des entités et relations.</div>
        </div>
        <div class="geo-card">
            <div class="badge">20 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Architecture Sémantique</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Logique de titrage Hn et structuration par listes/tableaux.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="geo-card">
            <div class="badge">15 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Profondeur & Sources</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Richesse textuelle et autorité des maillages externes.</div>
        </div>
        <div class="geo-card">
            <div class="badge">10 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Richesse en Entités</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Extraction de faits, dates et données propriétaires.</div>
        </div>
        <div class="geo-card">
            <div class="badge">25 PTS</div>
            <div style="font-weight:700; font-size:1.1rem; margin-bottom:8px;">Technique IA-Ready</div>
            <div style="font-size:0.9rem; color:#64748b; line-height:1.5;">Accessibilité bots et présence du standard llms.txt.</div>
        </div>
        """, unsafe_allow_html=True)

    # Barème
    st.markdown('<div style="margin-bottom:4rem;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">03. SCORING SYSTEM</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="grade-row"><span class="grade-letter">A+</span><span class="grade-range">90 - 100</span></div>
    <div class="grade-row"><span class="grade-letter">A</span><span class="grade-range">80 - 89</span></div>
    <div class="grade-row"><span class="grade-letter">B</span><span class="grade-range">70 - 79</span></div>
    <div class="grade-row"><span class="grade-letter">C</span><span class="grade-range">50 - 69</span></div>
    <div class="grade-row"><span class="grade-letter">F</span><span class="grade-range"> < 50</span></div>
    """, unsafe_allow_html=True)

    # Mode Santé (En blanc, bordures noires)
    st.markdown("""
    <div class="health-visual">
        <div style="font-weight:800; text-transform:uppercase; font-size:0.7rem; letter-spacing:0.2em; margin-bottom:2rem;">Health Monitoring</div>
        <div style="display:flex; gap:30px;">
            <div><span class="dot" style="background:#22c55e;"></span><span style="font-size:0.9rem; font-weight:600;">OPTIMAL</span></div>
            <div><span class="dot" style="background:#eab308;"></span><span style="font-size:0.9rem; font-weight:600;">AVERAGE</span></div>
            <div><span class="dot" style="background:#ef4444;"></span><span style="font-size:0.9rem; font-weight:600;">CRITICAL</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Conseils
    st.markdown('<div class="section-header">04. STRATEGIC DIRECTIVES</div>', unsafe_allow_html=True)
    st.markdown("""
    <ul class="tips-list">
        <li>Privilégier les formats factuels (tableaux, data-points).</li>
        <li>Convertir les paragraphes denses en listes structurées.</li>
        <li>Implémenter le balisage JSON-LD spécifique.</li>
        <li>Utiliser des titres sous forme de questions directes.</li>
        <li>Maintenir une fraîcheur de donnée < 90 jours.</li>
    </ul>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
