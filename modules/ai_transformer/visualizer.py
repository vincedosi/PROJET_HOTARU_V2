"""
HOTARU AI Transformer - Visualizer Module
Génère les previews visuelles et comparaisons HTML.
"""

from typing import Dict, List
import base64  # Gardé si besoin futur d'iframe data: URL
import difflib

from bs4 import BeautifulSoup
from pygments import highlight
from pygments.lexers import HtmlLexer
from pygments.formatters import HtmlFormatter


class HTMLVisualizer:
    """Génère les visualisations avant/après."""

    def __init__(self, html_before: str, html_after: str, transformations: List[Dict]):
        self.html_before = html_before
        self.html_after = html_after
        self.transformations = transformations
        self.soup_before = BeautifulSoup(html_before, "html.parser")
        self.soup_after = BeautifulSoup(html_after, "html.parser")

    def generate_preview_html(self, html_content: str, title: str = "Preview") -> str:
        """Génère une preview HTML miniature avec iframe."""

        # Amélioration : ajouter du CSS de base pour les previews et normaliser l'HTML
        safe_html = html_content.replace('"', '&quot;').replace("'", "&#x27;")

        preview_template = f"""
        <div class="preview-container" style="margin: 16px 0;">
            <div class="preview-header" style="padding: 12px 16px; background: #f8f8f8; border-bottom: 1px solid #e0e0e0; font-weight: 600;">
                {title if title else "Preview"}
            </div>
            <div class="preview-iframe-wrapper" style="min-height: 500px; border: 1px solid #e0e0e0; background: white; overflow: auto;">
                <iframe
                    srcdoc="{safe_html}"
                    sandbox="allow-same-origin"
                    scrolling="auto"
                    style="width: 100%; height: 100%; border: none; display: block;"
                ></iframe>
            </div>
        </div>
        """

        return preview_template

    def generate_code_comparison(self) -> str:
        """Génère une comparaison côte-à-côte du code avec coloration syntaxique."""

        formatter = HtmlFormatter(style="monokai", noclasses=True)

        html_before_pretty = self.soup_before.prettify()
        highlighted_before = highlight(html_before_pretty, HtmlLexer(), formatter)

        html_after_pretty = self.soup_after.prettify()
        highlighted_after = highlight(html_after_pretty, HtmlLexer(), formatter)

        comparison_html = f"""
        <div class="code-comparison">
            <div class="code-panel before">
                <div class="code-header">
                    <span class="badge badge-warning">AVANT</span>
                    <span class="code-label">HTML Original</span>
                </div>
                <div class="code-content">
                    {highlighted_before}
                </div>
            </div>
            
            <div class="code-panel after">
                <div class="code-header">
                    <span class="badge badge-success">APRÈS</span>
                    <span class="code-label">HTML Optimisé IA</span>
                </div>
                <div class="code-content">
                    {highlighted_after}
                </div>
            </div>
        </div>
        """

        return comparison_html

    def generate_diff_view(self) -> str:
        """Génère une vue diff ligne par ligne."""

        before_lines = self.soup_before.prettify().splitlines()
        after_lines = self.soup_after.prettify().splitlines()

        diff = difflib.unified_diff(
            before_lines,
            after_lines,
            lineterm="",
            n=3,  # Contexte de 3 lignes
        )

        diff_html = '<div class="diff-view"><pre class="diff-content">'

        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                diff_html += (
                    f'<span class="diff-added">{self._escape_html(line)}</span>\n'
                )
            elif line.startswith("-") and not line.startswith("---"):
                diff_html += (
                    f'<span class="diff-removed">{self._escape_html(line)}</span>\n'
                )
            elif line.startswith("@@"):
                diff_html += (
                    f'<span class="diff-info">{self._escape_html(line)}</span>\n'
                )
            else:
                diff_html += (
                    f'<span class="diff-context">{self._escape_html(line)}</span>\n'
                )

        diff_html += "</pre></div>"

        return diff_html

    def generate_transformations_list(self) -> str:
        """Génère la liste des transformations avec badges."""

        transformations_html = '<div class="transformations-list">'

        grouped: Dict[str, List[Dict]] = {}
        for t in self.transformations:
            t_type = t.get("type", "other")
            grouped.setdefault(t_type, []).append(t)

        for t_type, items in grouped.items():
            count = len(items)
            icon, badge_class = self._get_transformation_style(t_type)

            transformations_html += f"""
            <div class="transformation-group">
                <div class="transformation-header">
                    <span class="transformation-icon">{icon}</span>
                    <h4>{self._format_type_name(t_type)}</h4>
                    <span class="badge {badge_class}">{count}</span>
                </div>
                <ul class="transformation-items">
            """

            for item in items:
                before = item.get("before", "N/A")
                after = item.get("after", "N/A")
                reason = item.get("reason", "")

                before_short = (
                    f"{before[:60]}..." if len(str(before)) > 60 else before
                )
                after_short = f"{after[:60]}..." if len(str(after)) > 60 else after

                transformations_html += f"""
                <li class="transformation-item">
                    <div class="transformation-change">
                        <span class="before-text">{self._escape_html(str(before_short))}</span>
                        <span class="arrow">→</span>
                        <span class="after-text">{self._escape_html(str(after_short))}</span>
                    </div>
                    {f'<div class="transformation-reason">{self._escape_html(reason)}</div>' if reason else ''}
                </li>
                """

            transformations_html += """
                </ul>
            </div>
            """

        transformations_html += "</div>"

        return transformations_html

    def _get_transformation_style(self, t_type: str) -> tuple:
        """Retourne l'icône et la classe CSS pour un type de transformation."""

        styles = {
            "title_optimization": ("📝", "badge-primary"),
            "meta_description": ("📋", "badge-primary"),
            "heading_question": ("❓", "badge-warning"),
            "direct_answer_intro": ("💡", "badge-success"),
            "schema_org_article": ("🏷️", "badge-info"),
            "faq_schema": ("❔", "badge-info"),
            "semantic_structure": ("🏗️", "badge-secondary"),
        }

        return styles.get(t_type, ("🔧", "badge-secondary"))

    def _format_type_name(self, t_type: str) -> str:
        """Formate le nom d'un type de transformation."""

        names = {
            "title_optimization": "Optimisation Title",
            "meta_description": "Meta Description",
            "heading_question": "Titres → Questions",
            "direct_answer_intro": "Réponses Directes",
            "schema_org_article": "Schema Article",
            "faq_schema": "Schema FAQ",
            "semantic_structure": "Structure Sémantique",
        }

        return names.get(t_type, t_type.replace("_", " ").title())

    def _escape_html(self, text: str) -> str:
        """Échappe les caractères HTML."""

        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def generate_score_gauges(self, scores: Dict) -> str:
        """Génère des jauges circulaires pour les scores globaux."""

        global_scores = scores.get("global", {})
        before = float(global_scores.get("before", 0.0))
        after = float(global_scores.get("after", 0.0))
        delta = float(global_scores.get("delta", 0.0))

        gauges_html = f"""
        <div class="score-gauges">
            <div class="gauge-container">
                <div class="gauge-wrapper">
                    <svg class="gauge" viewBox="0 0 120 120" preserveAspectRatio="xMidYMid meet">
                        <circle cx="60" cy="60" r="50" fill="none" stroke="#e0e0e0" stroke-width="12"/>
                        <circle cx="60" cy="60" r="50" fill="none" stroke="#ff6b6b" stroke-width="12"
                                stroke-dasharray="{before * 3.14159:.1f} 314.159"
                                stroke-linecap="round"
                                transform="rotate(-90 60 60)"/>
                        <text x="60" y="60" text-anchor="middle" dy="0.35em" font-size="28" font-weight="bold">
                            {before:.0f}
                        </text>
                        <text x="60" y="85" text-anchor="middle" font-size="10" fill="#666">
                            AVANT
                        </text>
                    </svg>
                </div>
                <div class="gauge-label">
                    Score Original
                    <br>
                    <span class="grade-badge grade-{global_scores.get('grade_before', 'F').lower().replace('+', 'plus')}">
                        {global_scores.get('grade_before', 'F')}
                    </span>
                </div>
            </div>

            <div class="gauge-arrow">
                <svg width="50" height="50" viewBox="0 0 50 50" style="display: inline-block;">
                    <path d="M10 25 L40 25 M40 25 L32 17 M40 25 L32 33"
                          stroke="#4CAF50" stroke-width="2.5" fill="none" stroke-linecap="round"/>
                </svg>
                <div class="improvement-badge">
                    +{delta:.0f} pts
                </div>
            </div>

            <div class="gauge-container">
                <div class="gauge-wrapper">
                    <svg class="gauge" viewBox="0 0 120 120" preserveAspectRatio="xMidYMid meet">
                        <circle cx="60" cy="60" r="50" fill="none" stroke="#e0e0e0" stroke-width="12"/>
                        <circle cx="60" cy="60" r="50" fill="none" stroke="#4CAF50" stroke-width="12"
                                stroke-dasharray="{after * 3.14159:.1f} 314.159"
                                stroke-linecap="round"
                                transform="rotate(-90 60 60)"/>
                        <text x="60" y="60" text-anchor="middle" dy="0.35em" font-size="28" font-weight="bold">
                            {after:.0f}
                        </text>
                        <text x="60" y="85" text-anchor="middle" font-size="10" fill="#666">
                            APRÈS
                        </text>
                    </svg>
                </div>
                <div class="gauge-label">
                    Score Optimisé IA
                    <br>
                    <span class="grade-badge grade-{global_scores.get('grade_after', 'F').lower().replace('+', 'plus')}">
                        {global_scores.get('grade_after', 'F')}
                    </span>
                </div>
            </div>
        </div>
        """

        return gauges_html

    def generate_category_bars(self, scores: Dict) -> str:
        """Génère des barres de progression par catégorie."""

        categories = scores.get("categories", {})

        bars_html = '<div class="category-bars">'

        category_labels = {
            "metadata": "Métadonnées",
            "structure": "Structure",
            "content": "Contenu",
            "schema": "Schema.org",
        }

        for cat_key, cat_data in categories.items():
            label = category_labels.get(cat_key, cat_key)
            before = float(cat_data.get("before", 0.0))
            after = float(cat_data.get("after", 0.0))
            delta = float(cat_data.get("delta", 0.0))

            if delta > 20:
                bar_color = "#4CAF50"  # Vert
            elif delta > 0:
                bar_color = "#2196F3"  # Bleu
            else:
                bar_color = "#9E9E9E"  # Gris

            bars_html += f"""
            <div class="category-bar-item">
                <div class="category-bar-header">
                    <span class="category-label">{label}</span>
                    <span class="category-scores">
                        <span class="score-before">{before:.0f}</span>
                        <span class="arrow">→</span>
                        <span class="score-after">{after:.0f}</span>
                        {f'<span class="score-delta positive">+{delta:.0f}</span>' if delta > 0 else ''}
                    </span>
                </div>
                <div class="category-bar-track">
                    <div class="category-bar-fill before" style="width: {before}%"></div>
                    <div class="category-bar-fill after" style="width: {after}%; background-color: {bar_color}"></div>
                </div>
            </div>
            """

        bars_html += "</div>"

        return bars_html


if __name__ == "__main__":
    # Test simple
    html_before = "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
    html_after = (
        "<html><head><title>Comment faire un test ?</title></head>"
        "<body><h1>Comment faire un test ?</h1>"
        "<p><strong>Pour faire un test, il faut</strong> suivre ces étapes.</p></body></html>"
    )

    transformations = [
        {
            "type": "title_optimization",
            "before": "Test",
            "after": "Comment faire un test ?",
            "reason": "Transformation en question",
        }
    ]

    visualizer = HTMLVisualizer(html_before, html_after, transformations)

    print("=== TRANSFORMATIONS (HTML) ===")
    print(visualizer.generate_transformations_list())

