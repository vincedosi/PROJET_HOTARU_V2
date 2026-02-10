"""
HOTARU v3 – Module AI TRANSFORMER
Interface Streamlit pour analyser et optimiser une page HTML pour les IA.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st
import requests

from core.scraping import fetch_page
from modules.ai_transformer import (
    HTMLAnalyzer,
    AIOptimizedTransformer,
    AIScorer,
    HTMLVisualizer,
)


def _inject_ai_transformer_css() -> None:
    """Injecte le CSS spécifique au module (scopé, sans toucher au design global)."""
    if st.session_state.get("_ai_transformer_css_loaded"):
        return
    st.session_state["_ai_transformer_css_loaded"] = True

    st.markdown(
        """
<style>
.ai-transformer-hero {
    margin-bottom: 32px;
}
.ai-transformer-hero-title {
    font-size: 2.4rem;
    font-weight: 900;
    font-style: italic;
    letter-spacing: -0.05em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.ai-transformer-hero-subtitle {
    font-size: 0.95rem;
    color: var(--text-secondary);
    max-width: 640px;
}
.ai-transformer-url-box {
    border: 1px solid var(--border);
    padding: 20px;
    margin-bottom: 32px;
}
.ai-transformer-results-block {
    border: 1px solid var(--border-light);
    padding: 24px;
    margin-top: 24px;
}

/* Jauges globales */
.score-gauges {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 40px;
    flex-wrap: wrap;
    margin-bottom: 32px;
}
.gauge-container {
    text-align: center;
}
.gauge-wrapper {
    position: relative;
    width: 180px;
    height: 180px;
    margin: 0 auto 8px;
}
.gauge {
    width: 100%;
    height: 100%;
}
.gauge circle {
    transition: stroke-dasharray 0.8s ease-in-out;
}
.gauge-label {
    font-size: 0.8rem;
    color: var(--text-muted);
}
.grade-badge {
    display: inline-block;
    padding: 4px 10px;
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-radius: 0;
    border: 1px solid var(--border-light);
}
.grade-aplus,
.grade-a {
    background: #000000;
    color: #ffffff;
}
.grade-bplus,
.grade-b {
    background: #ffffff;
    color: #000000;
}
.grade-c,
.grade-d,
.grade-f {
    background: #ffffff;
    color: #000000;
    border-color: var(--border);
}
.gauge-arrow {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
}
.improvement-badge {
    font-size: 0.8rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 4px 10px;
    border: 1px solid var(--border);
}

/* Barres par catégorie */
.category-bars {
    display: grid;
    gap: 16px;
}
.category-bar-item {
    border: 1px solid var(--border-light);
    padding: 16px;
}
.category-bar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.category-label {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}
.category-scores {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8rem;
}
.score-before {
    text-decoration: line-through;
    color: var(--text-muted);
}
.score-after {
    font-weight: 700;
}
.score-delta {
    font-size: 0.75rem;
    font-weight: 700;
}
.category-bar-track {
    position: relative;
    height: 10px;
    background: var(--border-muted);
    border-radius: 0;
    overflow: hidden;
}
.category-bar-fill {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    transition: width 0.8s ease-in-out;
}
.category-bar-fill.before {
    background: rgba(0,0,0,0.15);
}
.category-bar-fill.after {
    background: #000000;
}

/* Ranking */
.ai-transformer-ranking {
    border: 1px solid var(--border);
    padding: 16px 20px;
    margin-top: 24px;
}
.ai-transformer-ranking-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border: 1px solid var(--border);
    font-size: 0.8rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.ai-transformer-ranking-message {
    margin-top: 8px;
    font-size: 0.85rem;
}

/* Transformations & code */
.code-comparison {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}
@media (max-width: 1200px) {
    .code-comparison {
        grid-template-columns: 1fr;
    }
}
.code-panel {
    border: 1px solid var(--border-light);
}
.code-header {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-light);
    display: flex;
    align-items: center;
    gap: 8px;
}
.badge {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    padding: 2px 6px;
    border-radius: 0;
}
.badge-warning,
.badge-success {
    border: 1px solid var(--border);
}
.code-content {
    padding: 12px;
    max-height: 480px;
    overflow: auto;
}

.transformations-list {
    display: grid;
    gap: 12px;
}
.transformation-group {
    border: 1px solid var(--border-light);
}
.transformation-header {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-light);
    display: flex;
    align-items: center;
    gap: 8px;
}
.transformation-items {
    list-style: none;
    margin: 0;
    padding: 0;
}
.transformation-item {
    padding: 10px 12px;
    border-top: 1px solid var(--border-light);
}
.transformation-change {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.before-text,
.after-text {
    font-family: 'SF Mono', 'Consolas', monospace;
    font-size: 0.75rem;
    padding: 4px 6px;
    border: 1px solid var(--border-light);
    max-width: 100%;
}
.transformation-reason {
    margin-top: 4px;
    font-size: 0.8rem;
    color: var(--text-secondary);
}

.preview-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}
@media (max-width: 1200px) {
    .preview-grid {
        grid-template-columns: 1fr;
    }
}
.preview-container {
    border: 1px solid var(--border-light);
}
.preview-header {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-light);
}
.preview-iframe-wrapper {
    background: white;
    height: 450px;
}
.preview-iframe {
    width: 100%;
    height: 100%;
    border: none;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _get_ranking_badge_html(ranking: Dict[str, Any]) -> str:
    tier = str(ranking.get("tier", "Bronze"))
    message = ranking.get("message", "")

    icon = {
        "Platinum": "💎",
        "Gold": "🥇",
        "Silver": "🥈",
        "Bronze": "🥉",
    }.get(tier, "🏆")

    return (
        f'<div class="ai-transformer-ranking">'
        f'<div class="ai-transformer-ranking-badge">'
        f"{icon} {tier}"
        f"</div>"
        f'<div class="ai-transformer-ranking-message">{message}</div>'
        f"</div>"
    )


def render_ai_transformer_tab() -> None:
    """Rendu principal de l'onglet AI TRANSFORMER."""
    _inject_ai_transformer_css()

    st.markdown(
        '<p class="section-title">AI TRANSFORMER / OPTIMISATION HTML</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ai-transformer-hero">', unsafe_allow_html=True)
    st.markdown(
        '<div class="ai-transformer-hero-title">Transformer votre contenu pour les IA</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ai-transformer-hero-subtitle">'
        "Analyse et ré-écriture automatique d'une page pour maximiser sa visibilité "
        "dans les réponses des IA (ChatGPT, Claude, Perplexity...)."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="ai-transformer-url-box">', unsafe_allow_html=True)
    col_url, col_btn = st.columns([3, 1])
    with col_url:
        url = st.text_input(
            "URL à analyser",
            key="ai_transformer_url",
            placeholder="https://example.com/votre-page",
        )
    with col_btn:
        run = st.button("Analyser & transformer", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    result: Dict[str, Any] | None = st.session_state.get("ai_transformer_result")

    if run:
        if not url:
            st.error("Merci de saisir une URL.")
            return
        with st.spinner("Analyse et transformation en cours..."):
            try:
                raw_html = fetch_page(url, timeout=15)
            except requests.RequestException as e:  # type: ignore[attr-defined]
                st.error(f"Erreur lors de la récupération de la page : {e}")
                return

            try:
                analyzer_before = HTMLAnalyzer(raw_html)
                analysis_before = analyzer_before.analyze()

                transformer = AIOptimizedTransformer(raw_html, analysis_before)
                optimized_html = transformer.transform()
                transformations = transformer.get_transformations_summary()

                analyzer_after = HTMLAnalyzer(optimized_html)
                analysis_after = analyzer_after.analyze()

                scorer = AIScorer(analysis_before, analysis_after)
                scores = scorer.calculate_scores()
            except Exception as e:  # pragma: no cover - defensive
                st.error(f"Erreur lors de l'analyse ou de la transformation : {e}")
                return

            result = {
                "url": url,
                "html_before": raw_html,
                "html_after": optimized_html,
                "analysis_before": analysis_before,
                "analysis_after": analysis_after,
                "transformations": transformations,
                "scores": scores,
            }
            st.session_state["ai_transformer_result"] = result

    if not result:
        st.info(
            "Saisissez une URL puis cliquez sur « Analyser & transformer » pour lancer le module."
        )
        return

    scores = result["scores"]
    html_before = result["html_before"]
    html_after = result["html_after"]
    transformations = result["transformations"]

    visualizer = HTMLVisualizer(html_before, html_after, transformations)

    st.markdown('<div class="ai-transformer-results-block">', unsafe_allow_html=True)
    st.subheader("Scores globaux")
    st.markdown(visualizer.generate_score_gauges(scores), unsafe_allow_html=True)
    st.markdown(visualizer.generate_category_bars(scores), unsafe_allow_html=True)

    ranking = scores.get("ranking", {})
    if ranking:
        st.markdown(_get_ranking_badge_html(ranking), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    tabs = st.tabs(["Transformations", "Code HTML", "Preview visuelle"])

    with tabs[0]:
        st.markdown(
            visualizer.generate_transformations_list(), unsafe_allow_html=True
        )

    with tabs[1]:
        st.markdown(visualizer.generate_code_comparison(), unsafe_allow_html=True)

    with tabs[2]:
        preview_before = visualizer.generate_preview_html(
            html_before, "AVANT – HTML original"
        )
        preview_after = visualizer.generate_preview_html(
            html_after, "APRÈS – HTML optimisé IA"
        )
        st.markdown(
            f'<div class="preview-grid">{preview_before}{preview_after}</div>',
            unsafe_allow_html=True,
        )

