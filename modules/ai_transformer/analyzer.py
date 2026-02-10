"""
HOTARU AI Transformer - Analyzer Module
Analyse la structure HTML et détecte les opportunités d'optimisation IA.
"""

from dataclasses import dataclass
from typing import Dict, List
import re

from bs4 import BeautifulSoup


@dataclass
class ContentBlock:
    """Représente un bloc de contenu analysé."""

    tag: str
    text: str
    xpath: str
    ai_score: float
    issues: List[str]
    suggestions: List[str]


class HTMLAnalyzer:
    """Analyse le HTML pour détecter les patterns non optimisés pour l'IA."""

    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, "html.parser")
        self.blocks: List[ContentBlock] = []
        self.global_score: float = 0

    def analyze(self) -> Dict:
        """Lance l'analyse complète du HTML."""

        results: Dict = {
            "global_score": 0,
            "blocks": [],
            "issues": [],
            "opportunities": [],
            "metadata": self._analyze_metadata(),
            "structure": self._analyze_structure(),
            "content": self._analyze_content(),
        }

        # Calcul du score global
        results["global_score"] = self._calculate_global_score(results)

        return results

    def _analyze_metadata(self) -> Dict:
        """Analyse les métadonnées (title, meta description, schema)."""

        metadata: Dict = {
            "title": None,
            "description": None,
            "schema_org": [],
            "open_graph": {},
            "issues": [],
        }

        # Title
        title_tag = self.soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.string or ""
            if len(metadata["title"]) < 30:
                metadata["issues"].append("Title trop court (< 30 caractères)")
            if "?" not in metadata["title"] and "comment" not in metadata["title"].lower():
                metadata["issues"].append("Title ne pose pas de question claire")
        else:
            metadata["issues"].append("Aucun <title> détecté")

        # Meta description
        desc_tag = self.soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            metadata["description"] = desc_tag.get("content", "")
            if len(metadata["description"]) < 100:
                metadata["issues"].append("Meta description trop courte")
        else:
            metadata["issues"].append("Aucune meta description")

        # Schema.org JSON-LD
        schema_scripts = self.soup.find_all("script", type="application/ld+json")
        metadata["schema_org"] = [script.string for script in schema_scripts if script.string]

        if not metadata["schema_org"]:
            metadata["issues"].append("Aucun Schema.org JSON-LD détecté")

        return metadata

    def _analyze_structure(self) -> Dict:
        """Analyse la structure sémantique (H1-H6, sections)."""

        structure: Dict = {
            "headings": [],
            "hierarchy_issues": [],
            "qa_patterns": 0,
            "list_patterns": 0,
        }

        # Analyse des titres
        for level in range(1, 7):
            headings = self.soup.find_all(f"h{level}")
            for h in headings:
                text = h.get_text(strip=True)
                structure["headings"].append(
                    {
                        "level": level,
                        "text": text,
                        "is_question": self._is_question(text),
                        "ai_score": self._score_heading(text, level),
                    }
                )

        # Détection des patterns Q&A
        structure["qa_patterns"] = len(
            [h for h in structure["headings"] if h["is_question"]]
        )

        # Vérification hiérarchie
        if structure["headings"]:
            if structure["headings"][0]["level"] != 1:
                structure["hierarchy_issues"].append("Pas de H1 en premier")

            # Vérifier les sauts de niveaux
            for i in range(1, len(structure["headings"])):
                prev_level = structure["headings"][i - 1]["level"]
                curr_level = structure["headings"][i]["level"]
                if curr_level - prev_level > 1:
                    structure["hierarchy_issues"].append(
                        f"Saut de H{prev_level} à H{curr_level} (titre index {i})"
                    )

        return structure

    def _analyze_content(self) -> Dict:
        """Analyse la qualité du contenu textuel."""

        content: Dict = {
            "paragraphs": [],
            "total_words": 0,
            "avg_sentence_length": 0,
            "direct_answers": 0,
            "issues": [],
        }

        # Analyse des paragraphes
        paragraphs = self.soup.find_all("p")

        for i, p in enumerate(paragraphs):
            text = p.get_text(strip=True)
            if len(text) < 20:
                continue

            analysis = {
                "index": i,
                "text": text,
                "word_count": len(text.split()),
                "has_direct_answer": self._has_direct_answer(text),
                "readability_score": self._calculate_readability(text),
                "ai_citation_score": self._calculate_citation_potential(text),
            }

            content["paragraphs"].append(analysis)
            content["total_words"] += analysis["word_count"]

            if analysis["has_direct_answer"]:
                content["direct_answers"] += 1

        # Détection des problèmes
        if content["total_words"] < 300:
            content["issues"].append("Contenu trop court (< 300 mots)")

        if content["direct_answers"] == 0:
            content["issues"].append("Aucune réponse directe détectée")

        if content["direct_answers"] / max(len(content["paragraphs"]), 1) < 0.3:
            content["issues"].append(
                "Moins de 30% des paragraphes contiennent des réponses directes"
            )

        return content

    def _is_question(self, text: str) -> bool:
        """Détecte si un texte est une question."""

        question_words = [
            "comment",
            "pourquoi",
            "quoi",
            "quel",
            "quelle",
            "où",
            "quand",
            "qui",
            "combien",
            "est-ce que",
        ]
        text_lower = text.lower()
        return text.endswith("?") or any(word in text_lower for word in question_words)

    def _has_direct_answer(self, text: str) -> bool:
        """Détecte si un paragraphe contient une réponse directe."""

        direct_patterns = [
            r"^(Oui|Non|C'est|Il s'agit|La réponse est)",
            r"^(Pour .+, il faut|Il est recommandé|La solution est)",
            r"^(En résumé|En bref|Concrètement)",
            r"^\d+\s+(étapes?|façons?|méthodes?|raisons?)",
        ]

        return any(re.match(pattern, text, re.IGNORECASE) for pattern in direct_patterns)

    def _score_heading(self, text: str, level: int) -> float:
        """Score un titre pour l'optimisation IA (0-100)."""

        score = 50.0  # Base

        # Bonus question
        if self._is_question(text):
            score += 30

        # Bonus longueur optimale (40-80 caractères)
        if 40 <= len(text) <= 80:
            score += 10
        elif len(text) < 20:
            score -= 20

        # Bonus mots-clés actionnables
        action_words = ["comment", "guide", "tutoriel", "étapes", "méthode"]
        if any(word in text.lower() for word in action_words):
            score += 10

        return max(0.0, min(100.0, score))

    def _calculate_readability(self, text: str) -> float:
        """Calcule un score de lisibilité simple (0-100)."""

        words = text.split()
        sentences = text.count(".") + text.count("!") + text.count("?")

        if sentences == 0:
            return 50.0

        avg_words_per_sentence = len(words) / sentences

        # Score basé sur la longueur moyenne des phrases
        if 10 <= avg_words_per_sentence <= 20:
            return 100.0
        if avg_words_per_sentence < 5:
            return 60.0
        if avg_words_per_sentence > 30:
            return 40.0
        return 70.0

    def _calculate_citation_potential(self, text: str) -> float:
        """Calcule le potentiel de citation par une IA (0-100)."""

        score = 50.0

        # Bonus réponse directe
        if self._has_direct_answer(text):
            score += 30

        # Bonus chiffres/données
        if re.search(r"\d+%|\d+\s+(euros?|dollars?|ans?|jours?)", text):
            score += 10

        # Bonus liste/énumération
        if re.search(r"\d+\.\s+|•|−|–", text):
            score += 10

        # Malus texte trop long
        if len(text) > 500:
            score -= 20

        return max(0.0, min(100.0, score))

    def _calculate_global_score(self, results: Dict) -> float:
        """Calcule le score global AI-readiness (0-100)."""

        scores: List[float] = []

        # Score métadonnées (20 %)
        meta_score = 100.0
        meta_score -= len(results["metadata"]["issues"]) * 15
        scores.append(meta_score * 0.2)

        # Score structure (30 %)
        struct_score = 100.0
        struct_score -= len(results["structure"]["hierarchy_issues"]) * 10
        if results["structure"]["qa_patterns"] == 0:
            struct_score -= 30
        scores.append(max(0.0, struct_score) * 0.3)

        # Score contenu (50 %)
        content_score = 100.0
        content_score -= len(results["content"]["issues"]) * 15

        if results["content"]["paragraphs"]:
            avg_citation = sum(
                p["ai_citation_score"] for p in results["content"]["paragraphs"]
            ) / len(results["content"]["paragraphs"])
            content_score = (content_score + avg_citation) / 2

        scores.append(max(0.0, content_score) * 0.5)

        return sum(scores)


if __name__ == "__main__":
    # Test rapide manuel
    sample_html = """
    <html>
    <head>
        <title>Guide SEO</title>
        <meta name="description" content="Un guide">
    </head>
    <body>
        <h1>Mon article</h1>
        <p>Voici du contenu générique sans réponse claire.</p>
        <h2>Comment optimiser ?</h2>
        <p>Pour optimiser votre site, il faut suivre 3 étapes principales.</p>
    </body>
    </html>
    """

    analyzer = HTMLAnalyzer(sample_html)
    results = analyzer.analyze()

    print(f"Score global: {results['global_score']:.1f}/100")
    meta_issues = len(results["metadata"]["issues"])
    struct_issues = len(results["structure"]["hierarchy_issues"])
    content_issues = len(results["content"]["issues"])
    print(f"Issues détectées: {meta_issues + struct_issues + content_issues}")

