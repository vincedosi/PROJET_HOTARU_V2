"""
HOTARU AI Transformer - Scorer Module
Compare les scores avant/après transformation.
"""

from dataclasses import dataclass
from typing import Dict, List
import json


@dataclass
class ScoreCard:
    """Carte de score pour un critère donné."""

    category: str
    name: str
    before: float
    after: float
    max_score: float
    impact: str  # 'critical', 'high', 'medium', 'low'
    explanation: str


class AIScorer:
    """Calcule et compare les scores AI-readiness avant/après."""

    # Poids des différentes catégories
    WEIGHTS = {
        "metadata": 0.15,
        "structure": 0.25,
        "content": 0.40,
        "schema": 0.20,
    }

    def __init__(self, analysis_before: Dict, analysis_after: Dict):
        self.before = analysis_before
        self.after = analysis_after
        self.scorecards: List[ScoreCard] = []

    def calculate_scores(self) -> Dict:
        """Calcule tous les scores et retourne le comparatif."""

        scores: Dict = {
            "global": self._calculate_global_scores(),
            "categories": self._calculate_category_scores(),
            "scorecards": self._generate_scorecards(),
            "improvements": self._detect_improvements(),
            "ranking": self._calculate_ranking(),
        }

        return scores

    def _calculate_global_scores(self) -> Dict:
        """Calcule les scores globaux avant/après."""

        before_score = self.before.get("global_score", 0.0)
        after_score = self._calculate_after_global_score()

        delta = after_score - before_score
        improvement_pct = (delta / max(before_score, 1.0)) * 100.0

        return {
            "before": before_score,
            "after": after_score,
            "delta": delta,
            "improvement_pct": improvement_pct,
            "grade_before": self._score_to_grade(before_score),
            "grade_after": self._score_to_grade(after_score),
        }

    def _calculate_after_global_score(self) -> float:
        """Calcule le score global après transformation."""

        meta_score = self._score_metadata(self.after)
        struct_score = self._score_structure(self.after)
        content_score = self._score_content(self.after)
        schema_score = self._score_schema(self.after)

        global_score = (
            meta_score * self.WEIGHTS["metadata"]
            + struct_score * self.WEIGHTS["structure"]
            + content_score * self.WEIGHTS["content"]
            + schema_score * self.WEIGHTS["schema"]
        )

        return round(global_score, 1)

    def _score_metadata(self, analysis: Dict) -> float:
        """Score les métadonnées (0-100)."""

        score = 100.0

        meta = analysis.get("metadata", {})
        issues = meta.get("issues", [])

        score -= len(issues) * 20.0

        title = meta.get("title", "") or ""
        if title and ("?" in title or "comment" in title.lower()):
            score += 10.0

        desc = meta.get("description", "") or ""
        if desc and len(desc) >= 120:
            score += 10.0

        return max(0.0, min(100.0, score))

    def _score_structure(self, analysis: Dict) -> float:
        """Score la structure sémantique (0-100)."""

        score = 100.0

        struct = analysis.get("structure", {})

        hierarchy_issues = struct.get("hierarchy_issues", [])
        score -= len(hierarchy_issues) * 15.0

        qa_patterns = struct.get("qa_patterns", 0)
        if qa_patterns >= 5:
            score += 20.0
        elif qa_patterns >= 3:
            score += 10.0
        elif qa_patterns == 0:
            score -= 30.0

        headings = struct.get("headings", [])
        if headings and headings[0].get("level") == 1:
            score += 10.0

        return max(0.0, min(100.0, score))

    def _score_content(self, analysis: Dict) -> float:
        """Score la qualité du contenu (0-100)."""

        score = 100.0

        content = analysis.get("content", {})
        issues = content.get("issues", [])

        score -= len(issues) * 15.0

        direct_answers = content.get("direct_answers", 0)
        paragraphs = content.get("paragraphs", [])
        total_paragraphs = len(paragraphs)

        if total_paragraphs > 0:
            direct_ratio = direct_answers / total_paragraphs

            if direct_ratio >= 0.5:
                score += 20.0
            elif direct_ratio >= 0.3:
                score += 10.0
            elif direct_ratio < 0.2:
                score -= 20.0

        if paragraphs:
            avg_citation = sum(
                p.get("ai_citation_score", 0.0) for p in paragraphs
            ) / len(paragraphs)
            score = (score + avg_citation) / 2.0

        return max(0.0, min(100.0, score))

    def _score_schema(self, analysis: Dict) -> float:
        """Score la présence de Schema.org (0-100)."""

        score = 0.0

        meta = analysis.get("metadata", {})
        schemas = meta.get("schema_org", [])

        if not schemas:
            return 0.0

        schema_types = set()
        for schema_str in schemas:
            try:
                schema_data = json.loads(schema_str)
                schema_type = schema_data.get("@type", "")
                if isinstance(schema_type, str):
                    schema_types.add(schema_type)
                elif isinstance(schema_type, list):
                    schema_types.update(schema_type)
            except Exception:
                continue

        if "Article" in schema_types or "BlogPosting" in schema_types:
            score += 40.0

        if "FAQPage" in schema_types:
            score += 40.0

        if "Organization" in schema_types or "Person" in schema_types:
            score += 10.0

        if "BreadcrumbList" in schema_types:
            score += 10.0

        return min(100.0, score)

    def _calculate_category_scores(self) -> Dict:
        """Calcule les scores par catégorie."""

        categories: Dict = {}

        for cat in ["metadata", "structure", "content", "schema"]:
            scorer_method = getattr(self, f"_score_{cat}")

            before_val = scorer_method(self.before)
            after_val = scorer_method(self.after)

            categories[cat] = {
                "before": before_val,
                "after": after_val,
                "weight": self.WEIGHTS[cat],
                "delta": after_val - before_val,
            }

        return categories

    def _generate_scorecards(self) -> List[ScoreCard]:
        """Génère des scorecards détaillées pour chaque critère."""

        cards: List[ScoreCard] = []

        meta_before = self.before.get("metadata", {})
        meta_after = self.after.get("metadata", {})

        title_before = meta_before.get("title", "") or ""
        title_after = meta_after.get("title", "") or ""

        cards.append(
            ScoreCard(
                category="metadata",
                name="Title optimisé (Question)",
                before=100.0 if ("?" in title_before) else 0.0,
                after=100.0 if ("?" in title_after) else 0.0,
                max_score=100.0,
                impact="high",
                explanation=(
                    "Un title en format question améliore de ~40% le taux de clic "
                    "depuis les réponses d'IA."
                ),
            )
        )

        struct_before = self.before.get("structure", {})
        struct_after = self.after.get("structure", {})

        qa_before = struct_before.get("qa_patterns", 0)
        qa_after = struct_after.get("qa_patterns", 0)

        cards.append(
            ScoreCard(
                category="structure",
                name="Titres en format Q&A",
                before=min(100.0, qa_before * 20.0),
                after=min(100.0, qa_after * 20.0),
                max_score=100.0,
                impact="critical",
                explanation=(
                    "Les IA privilégient les contenus structurés en "
                    "Questions/Réponses."
                ),
            )
        )

        content_before = self.before.get("content", {})
        content_after = self.after.get("content", {})

        direct_before = content_before.get("direct_answers", 0)
        direct_after = content_after.get("direct_answers", 0)

        total_p_before = len(content_before.get("paragraphs", []))
        total_p_after = len(content_after.get("paragraphs", []))

        ratio_before = (direct_before / max(total_p_before, 1)) * 100.0
        ratio_after = (direct_after / max(total_p_after, 1)) * 100.0

        cards.append(
            ScoreCard(
                category="content",
                name="Paragraphes avec réponse directe",
                before=ratio_before,
                after=ratio_after,
                max_score=100.0,
                impact="critical",
                explanation=(
                    "Les IA citent en priorité les paragraphes qui "
                    "commencent par une réponse claire."
                ),
            )
        )

        schema_before = len(meta_before.get("schema_org", []))
        schema_after = len(meta_after.get("schema_org", []))

        cards.append(
            ScoreCard(
                category="schema",
                name="Schema.org JSON-LD",
                before=min(100.0, schema_before * 50.0),
                after=min(100.0, schema_after * 50.0),
                max_score=100.0,
                impact="medium",
                explanation=(
                    "Schema.org aide les IA à comprendre le contexte "
                    "et la structure de la page."
                ),
            )
        )

        self.scorecards = cards
        return cards

    def _detect_improvements(self) -> List[Dict]:
        """Détecte les améliorations clés apportées."""

        improvements: List[Dict] = []

        categories = self._calculate_category_scores()

        for cat_name, cat_data in categories.items():
            delta = cat_data["delta"]
            if delta > 10.0:
                improvements.append(
                    {
                        "category": cat_name,
                        "delta": delta,
                        "impact": self._categorize_impact(delta),
                        "message": self._generate_improvement_message(
                            cat_name, delta
                        ),
                    }
                )

        improvements.sort(key=lambda x: x["delta"], reverse=True)

        return improvements

    def _categorize_impact(self, delta: float) -> str:
        """Catégorise l'impact d'une amélioration."""

        if delta >= 40.0:
            return "critical"
        if delta >= 25.0:
            return "high"
        if delta >= 10.0:
            return "medium"
        return "low"

    def _generate_improvement_message(self, category: str, delta: float) -> str:
        """Génère un message d'amélioration."""

        messages = {
            "metadata": (
                f"Métadonnées optimisées : +{delta:.0f} pts - "
                "meilleure compréhension par les IA."
            ),
            "structure": (
                f"Structure améliorée : +{delta:.0f} pts - "
                "format Question/Réponse appliqué."
            ),
            "content": (
                f"Contenu optimisé : +{delta:.0f} pts - "
                "réponses directes ajoutées."
            ),
            "schema": (
                f"Schema.org ajouté : +{delta:.0f} pts - "
                "données structurées implémentées."
            ),
        }

        return messages.get(
            category, f"Amélioration {category} : +{delta:.0f} pts"
        )

    def _calculate_ranking(self) -> Dict:
        """Calcule le ranking de la page (Bronze/Silver/Gold/Platinum)."""

        after_score = self._calculate_after_global_score()

        if after_score >= 90.0:
            tier = "Platinum"
            color = "#E5E4E2"
            message = "Parfait ! Votre page est optimale pour les IA."
        elif after_score >= 75.0:
            tier = "Gold"
            color = "#FFD700"
            message = "Excellent ! Votre page est bien optimisée."
        elif after_score >= 60.0:
            tier = "Silver"
            color = "#C0C0C0"
            message = "Bien ! Quelques optimisations restent possibles."
        else:
            tier = "Bronze"
            color = "#CD7F32"
            message = "Votre page nécessite des optimisations importantes."

        return {
            "tier": tier,
            "color": color,
            "score": after_score,
            "message": message,
        }

    def _score_to_grade(self, score: float) -> str:
        """Convertit un score en note (A+, A, B, C, D, F)."""

        if score >= 95.0:
            return "A+"
        if score >= 90.0:
            return "A"
        if score >= 80.0:
            return "B+"
        if score >= 70.0:
            return "B"
        if score >= 60.0:
            return "C"
        if score >= 50.0:
            return "D"
        return "F"


if __name__ == "__main__":
    # Test simple avec des données simulées
    analysis_before = {
        "global_score": 45,
        "metadata": {
            "title": "Mon guide SEO",
            "description": "Un guide",
            "schema_org": [],
            "issues": ["Title trop court", "Aucun Schema.org"],
        },
        "structure": {
            "headings": [
                {"level": 1, "text": "SEO", "is_question": False},
            ],
            "qa_patterns": 0,
            "hierarchy_issues": [],
        },
        "content": {
            "paragraphs": [
                {"text": "Texte générique", "ai_citation_score": 30},
            ],
            "direct_answers": 0,
            "issues": ["Aucune réponse directe"],
        },
    }

    analysis_after = {
        "global_score": 85,
        "metadata": {
            "title": "Comment optimiser son SEO ? Guide complet 2024",
            "description": "Découvrez les meilleures techniques SEO...",
            "schema_org": ['{"@type": "Article"}', '{"@type": "FAQPage"}'],
            "issues": [],
        },
        "structure": {
            "headings": [
                {
                    "level": 1,
                    "text": "Comment optimiser son SEO ?",
                    "is_question": True,
                },
                {
                    "level": 2,
                    "text": "Quelles sont les bases ?",
                    "is_question": True,
                },
            ],
            "qa_patterns": 2,
            "hierarchy_issues": [],
        },
        "content": {
            "paragraphs": [
                {
                    "text": "Pour optimiser votre SEO, il faut...",
                    "ai_citation_score": 85,
                },
            ],
            "direct_answers": 1,
            "issues": [],
        },
    }

    scorer = AIScorer(analysis_before, analysis_after)
    scores = scorer.calculate_scores()

    print("=== SCORES GLOBAUX ===")
    print(
        f"Avant: {scores['global']['before']}/100 "
        f\"(Grade {scores['global']['grade_before']})\"
    )
    print(
        f"Après: {scores['global']['after']}/100 "
        f\"(Grade {scores['global']['grade_after']})\"
    )
    print(
        "Amélioration: "
        f\"+{scores['global']['delta']:.1f} pts "
        f\"({scores['global']['improvement_pct']:.0f}%)\"
    )

    print("\n=== RANKING ===")
    print(f\"{scores['ranking']['tier']} - {scores['ranking']['message']}\")

    print("\n=== AMÉLIORATIONS ===")
    for imp in scores["improvements"]:
        print(f\"✓ {imp['message']}\")

