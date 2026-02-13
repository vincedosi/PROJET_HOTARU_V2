# =============================================================================
# VIEW - Authority Score (Streamlit UI)
# Appelle la logique modules.audit.authority_score et affiche avec st.*
# =============================================================================

import time
import streamlit as st

from modules.audit.authority_score import compute_authority_score


def _score_color(score):
    """Retourne la couleur selon le score - monochrome"""
    if score >= 70:
        return "#000000"
    elif score >= 40:
        return "rgba(0,0,0,0.55)"
    else:
        return "rgba(0,0,0,0.25)"


def _score_status(score):
    """Retourne le statut"""
    if score >= 70:
        return "FORT"
    elif score >= 40:
        return "MOYEN"
    else:
        return "FAIBLE"


def render_authority_score():
    """Rendu principal de l'onglet Authority Score (SaaS)."""
    st.markdown(
        '<h1 class="zen-title">AUTHORITY SCORE</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="zen-subtitle">'
        "AI AUTHORITY INDEX // MESURE LA COMPATIBILITE D'UNE MARQUE AVEC LES LLMS & SYSTEMES RAG</p>",
        unsafe_allow_html=True,
    )

    tab_analyse, tab_methodo = st.tabs(["Analyse", "Méthodologie"])
    with tab_analyse:
        _render_authority_analyse_content()
    with tab_methodo:
        from views.methodologie_blocks import render_methodologie_for_module
        render_methodologie_for_module("authority")


def _render_authority_analyse_content():
    """Contenu de l'onglet Analyse (Authority Score)."""
    st.markdown(
        '<p class="section-title">01 / ANALYSE</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-container">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        entity_name = st.text_input(
            "ENTITY NAME",
            placeholder="Ex: Nike, Coca-Cola, LVMH...",
            key="authority_entity_name",
        )
    with col2:
        website_url = st.text_input(
            "WEBSITE",
            placeholder="https://www.example.com",
            key="authority_website_url",
        )

    competitors = st.text_area(
        "COMPETITORS (ONE URL PER LINE)",
        placeholder="https://www.concurrent1.com\nhttps://www.concurrent2.com",
        height=80,
        key="authority_competitors",
    )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("CALCULER L'AUTHORITY SCORE", use_container_width=True, type="primary"):
        if not entity_name or not website_url:
            st.warning("Veuillez renseigner le nom de l'entite et le site web.")
            return

        url = website_url.strip()
        if not url.startswith("http"):
            url = "https://" + url

        comp_list = [c.strip() for c in competitors.strip().split("\n") if c.strip()] if competitors else []

        with st.spinner("Analyse en cours (graphe de connaissances, JSON-LD, vecteurs)..."):
            progress = st.progress(0, "Calcul en cours...")
            result = compute_authority_score(entity_name, url, comp_list)
            progress.progress(1.0, "Analyse terminee.")
            time.sleep(0.3)
            progress.empty()

        st.session_state["authority_result"] = result
        st.session_state["authority_entity"] = entity_name

    # === AFFICHAGE DES RESULTATS ===
    if "authority_result" not in st.session_state:
        return

    result = st.session_state["authority_result"]
    entity = st.session_state.get("authority_entity", "")
    overall = result["overall_score"]
    bd = result["breakdown"]

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    for pillar_name, error_msg in result.get("errors", []):
        st.warning(f"Pilier {pillar_name} : analyse partielle ({error_msg})")

    st.markdown(
        f'<div style="text-align:center;padding:48px 0;">'
        f'<span class="label-caps" style="margin-bottom:16px;display:block;">AI AUTHORITY INDEX</span>'
        f'<div style="font-size:7rem;font-weight:900;line-height:1;color:#000;letter-spacing:-0.05em;font-style:italic;">'
        f'{overall}</div>'
        f'<div style="font-size:0.85rem;font-weight:600;color:rgba(0,0,0,0.4);margin-top:8px;">/100</div>'
        f'<div class="step-badge" style="margin-top:20px;padding:8px 24px;font-size:0.6rem;">'
        f'{result["interpretation"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if entity:
        st.markdown(
            f'<p style="text-align:center;font-size:0.8rem;color:rgba(0,0,0,0.4);margin-top:4px;">'
            f'Entite analysee : <strong style="color:#000;">{entity}</strong></p>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<p class="section-title">02 / DÉTAIL PAR PILIER</p>',
        unsafe_allow_html=True,
    )

    pillar_config = [
        ("Ancrage Knowledge Graph", "knowledge_graph", "30%"),
        ("Interopérabilité des Données", "structured_data", "25%"),
        ("Autorité de Citation", "citation_authority", "20%"),
        ("Densité Vectorielle (Semantic Density)", "semantic_completeness", "15%"),
        ("Fraîcheur de Contenu", "content_freshness", "10%"),
    ]

    for display_name, key, weight in pillar_config:
        pillar = bd[key]
        pscore = pillar["score"]
        color = _score_color(pscore)
        status = _score_status(pscore)
        pct = pscore / 100

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:16px;padding:16px 0;'
            f'border-bottom:1px solid rgba(0,0,0,0.08);">'
            f'<div style="min-width:220px;">'
            f'<span style="font-weight:800;font-size:0.7rem;color:#000;letter-spacing:0.05em;text-transform:uppercase;">{display_name}</span>'
            f'<span style="font-size:0.6rem;color:rgba(0,0,0,0.4);margin-left:8px;">({weight})</span>'
            f'</div>'
            f'<div style="flex:1;background:rgba(0,0,0,0.06);height:6px;position:relative;">'
            f'<div style="position:absolute;left:0;top:0;height:100%;width:{pct*100}%;background:{color};"></div>'
            f'</div>'
            f'<div style="min-width:50px;text-align:right;">'
            f'<span style="font-weight:900;font-size:0.9rem;color:#000;">{pscore}</span>'
            f'<span style="font-size:0.65rem;color:rgba(0,0,0,0.4);">/100</span>'
            f'</div>'
            f'<div style="min-width:70px;">'
            f'<span class="step-badge" style="font-size:0.55rem;">{status}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<p class="section-title">03 / DONNÉES DÉTAILLÉES</p>',
        unsafe_allow_html=True,
    )

    tab_labels = [
        f"ANCRAGE KNOWLEDGE GRAPH ({bd['knowledge_graph']['score']}/100)",
        f"INTEROPÉRABILITÉ DES DONNÉES ({bd['structured_data']['score']}/100)",
        f"AUTORITÉ DE CITATION ({bd['citation_authority']['score']}/100)",
        f"DENSITÉ VECTORIELLE ({bd['semantic_completeness']['score']}/100)",
        f"FRAÎCHEUR DE CONTENU ({bd['content_freshness']['score']}/100)",
    ]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_labels)

    with tab1:
        kg_d = bd["knowledge_graph"].get("details", {})
        if kg_d.get("qid"):
            st.markdown(
                f'<div style="padding:12px;border:1px solid rgba(0,0,0,0.12);margin-bottom:12px;">'
                f'<span class="label-caps">QID WIKIDATA</span>'
                f'<div style="font-size:0.9rem;font-weight:700;color:#000;margin-top:4px;">'
                f'<a href="https://www.wikidata.org/wiki/{kg_d["qid"]}" target="_blank" '
                f'style="color:#000;border-bottom:1px solid #000;">'
                f'{kg_d["qid"]}</a></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("PROPRIETES", kg_d.get("nb_properties", 0))
            with col2:
                st.metric("REFERENCES", kg_d.get("nb_references", 0))
            with col3:
                st.metric("IDS EXTERNES", kg_d.get("nb_external_ids", 0))
            with col4:
                st.metric("WIKIPEDIA", "OUI" if kg_d.get("has_wikipedia") else "NON")
        else:
            st.markdown(
                '<p style="font-size:0.8rem;color:#000;font-weight:700;">'
                "Entite non trouvee dans Wikidata.</p>",
                unsafe_allow_html=True,
            )

    with tab2:
        sd_d = bd["structured_data"].get("details", {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("PAGES ANALYSEES", sd_d.get("pages_analyzed", 0))
        with col2:
            st.metric("PAGES AVEC JSON-LD", sd_d.get("pages_with_jsonld", 0))
        with col3:
            st.metric("% JSON-LD", f'{sd_d.get("jsonld_percentage", 0)}%')
        with col4:
            st.metric("LIENS sameAs", sd_d.get("same_as_count", 0))

        types = sd_d.get("schema_types", [])
        if types:
            st.markdown(
                '<span class="label-caps" style="margin-top:12px;">TYPES SCHEMA.ORG</span>',
                unsafe_allow_html=True,
            )
            types_html = " ".join(
                f'<span style="display:inline-block;padding:3px 10px;margin:2px;font-size:0.65rem;'
                f'font-weight:700;border:1px solid rgba(0,0,0,0.12);color:#000;letter-spacing:0.05em;">{t}</span>'
                for t in types
            )
            st.markdown(types_html, unsafe_allow_html=True)

        if sd_d.get("has_organization"):
            st.markdown(
                '<p style="font-size:0.75rem;color:#000;font-weight:700;margin-top:8px;">'
                "Type Organization detecte</p>",
                unsafe_allow_html=True,
            )

        if sd_d.get("has_same_as"):
            st.markdown(
                '<p style="font-size:0.75rem;color:#000;font-weight:700;margin-top:4px;">'
                "Propriete <code>sameAs</code> detectee : le site est plus facilement resolu "
                "comme entite unique par les LLMs et les index RAG.</p>",
                unsafe_allow_html=True,
            )

    with tab3:
        ca_d = bd["citation_authority"].get("details", {})
        col1, col2 = st.columns(2)
        with col1:
            st.metric("REFERENCES WIKIPEDIA", ca_d.get("wikipedia_references", 0))
        with col2:
            st.metric("SIGNALUX DE CONFIANCE", ca_d.get("trust_signals", 0))

        social = ca_d.get("social_presence", {})
        if social:
            st.markdown(
                '<span class="label-caps" style="margin-top:12px;">PRESENCE SOCIALE</span>',
                unsafe_allow_html=True,
            )
            social_html = ""
            for platform, present in social.items():
                bg = "#000" if present else "transparent"
                text_c = "#fff" if present else "rgba(0,0,0,0.4)"
                border = "#000" if present else "rgba(0,0,0,0.12)"
                social_html += (
                    f'<span style="display:inline-block;padding:3px 10px;margin:2px;font-size:0.6rem;'
                    f'font-weight:800;letter-spacing:0.1em;text-transform:uppercase;'
                    f'background:{bg};color:{text_c};border:1px solid {border};">{platform}</span>'
                )
            st.markdown(social_html, unsafe_allow_html=True)

    with tab4:
        sc_d = bd["semantic_completeness"].get("details", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("MODE", sc_d.get("mode", "N/A"))
        with col2:
            st.metric("SIMILARITÉ COSINE", sc_d.get("similarity", 0.0))
        with col3:
            st.metric("TOKENS CONTENU", sc_d.get("site_tokens", 0))

        warning = sc_d.get("warning")
        if warning:
            st.info(f"🧠 {warning}")

    with tab5:
        cf_d = bd["content_freshness"].get("details", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_age = cf_d.get("avg_age_days")
            st.metric("AGE MOYEN (JOURS)", round(avg_age) if avg_age is not None else "N/A")
        with col2:
            st.metric("DERNIERE PUBLICATION", cf_d.get("last_publication", "N/A"))
        with col3:
            st.metric("PAGES AVEC DATES", cf_d.get("pages_with_dates", 0))

    recommendations = result.get("recommendations", [])
    if recommendations:
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">04 / RECOMMANDATIONS PRIORITAIRES</p>',
            unsafe_allow_html=True,
        )

        for i, reco in enumerate(recommendations, 1):
            st.markdown(
                f'<div style="padding:16px;border:1px solid rgba(0,0,0,0.12);border-left:3px solid #000;'
                f'margin-bottom:8px;">'
                f'<span class="label-caps">ACTION {i}</span>'
                f'<div style="font-size:0.85rem;color:#000;line-height:1.6;margin-top:6px;">{reco}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
