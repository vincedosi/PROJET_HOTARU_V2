"""
HOTARU AI Transformer - Transformer Module
Transforme le HTML pour maximiser la lisibilité par les IA.
"""

from datetime import datetime
import json
import re
from typing import Dict, List

from bs4 import BeautifulSoup


class AIOptimizedTransformer:
    """Transforme le HTML pour optimiser la lecture par les IA."""

    def __init__(self, html_content: str, analysis: Dict):
        self.soup = BeautifulSoup(html_content, "html.parser")
        self.analysis = analysis
        self.transformations: List[Dict] = []

    def transform(self) -> str:
        """Lance toutes les transformations et retourne le HTML optimisé."""

        self._optimize_metadata()
        self._restructure_headings()
        self._optimize_paragraphs()
        self._add_schema_org()
        self._add_faq_schema()
        self._improve_semantic_structure()

        return self.soup.prettify()

    def _optimize_metadata(self) -> None:
        """Optimise title et meta description."""

        # Optimisation du title
        title_tag = self.soup.find("title")
        if title_tag:
            old_title = title_tag.string or ""

            # Si le title n'est pas une question, on en fait une
            if not old_title.endswith("?"):
                new_title = f"Comment {old_title.lower()} ? Guide complet {datetime.now().year}"
                title_tag.string = new_title

                self.transformations.append(
                    {
                        "type": "title_optimization",
                        "before": old_title,
                        "after": new_title,
                        "reason": "Transformation en question pour meilleure visibilité IA",
                    }
                )

        # Optimisation meta description
        desc_tag = self.soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            old_desc = desc_tag.get("content", "")

            new_desc = (
                f"✓ Découvrez {old_desc[:100]}. Guide pratique avec exemples concrets "
                f"et étapes détaillées. Mis à jour en {datetime.now().year}."
            )
            desc_tag["content"] = new_desc[:160]

            self.transformations.append(
                {
                    "type": "meta_description",
                    "before": old_desc,
                    "after": new_desc[:160],
                    "reason": "Ajout de réponse directe et call-to-action",
                }
            )

    def _restructure_headings(self) -> None:
        """Restructure les titres en format Question/Réponse."""

        headings = self.soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

        for h in headings:
            old_text = h.get_text(strip=True)

            # Si ce n'est pas déjà une question
            if not old_text.endswith("?"):
                new_text = self._convert_to_question(old_text, h.name)

                if new_text != old_text:
                    h.string = new_text

                    self.transformations.append(
                        {
                            "type": "heading_question",
                            "level": h.name,
                            "before": old_text,
                            "after": new_text,
                            "reason": "Conversion en format question",
                        }
                    )

    def _convert_to_question(self, text: str, level: str) -> str:
        """Convertit un titre en question pertinente."""

        text_lower = text.lower()

        if "définition" in text_lower or "qu'est-ce" in text_lower:
            return f"Qu'est-ce que {text.replace('Définition de', '').replace('Définition', '').strip()} ?"

        if "avantages" in text_lower or "bénéfices" in text_lower:
            subject = text.replace("Avantages", "").replace("de", "").strip()
            return f"Quels sont les avantages de {subject} ?"

        if "étapes" in text_lower or "comment" in text_lower:
            if "comment" not in text_lower:
                subject = text.replace("Étapes", "").replace("pour", "").strip()
                return f"Comment {subject} ?"
            return text if text.endswith("?") else f"{text} ?"

        if "raisons" in text_lower or "pourquoi" in text_lower:
            if "pourquoi" not in text_lower:
                subject = text.replace("Raisons", "").replace("de", "").strip()
                return f"Pourquoi {subject} ?"
            return text if text.endswith("?") else f"{text} ?"

        # Conversion générique en "Comment ..."
        if level in ["h2", "h3"]:
            return f"Comment {text.lower()} ?"
        return text

    def _optimize_paragraphs(self) -> None:
        """Optimise les paragraphes pour ajout de réponses directes."""

        headings = self.soup.find_all(["h2", "h3"])

        for h in headings:
            next_p = h.find_next_sibling("p")

            if next_p:
                text = next_p.get_text(strip=True)

                if not self._starts_with_direct_answer(text):
                    question = h.get_text(strip=True)
                    direct_intro = self._generate_direct_intro(question)

                    strong_tag = self.soup.new_tag("strong")
                    strong_tag.string = direct_intro + " "

                    next_p.insert(0, strong_tag)

                    self.transformations.append(
                        {
                            "type": "direct_answer_intro",
                            "question": question,
                            "intro_added": direct_intro,
                            "reason": "Ajout réponse directe pour citation IA",
                        }
                    )

    def _starts_with_direct_answer(self, text: str) -> bool:
        """Vérifie si un texte commence par une réponse directe."""

        direct_starters = [
            r"^(Oui|Non|C'est|Il s'agit)",
            r"^(La réponse est|En résumé|Concrètement)",
            r"^(Pour .+, il faut|La meilleure)",
            r"^\d+\s+(étapes?|façons?|méthodes?)",
        ]

        return any(re.match(pattern, text, re.IGNORECASE) for pattern in direct_starters)

    def _generate_direct_intro(self, question: str) -> str:
        """Génère une intro de réponse directe basée sur la question."""

        q = question.strip()
        q_lower = q.lower()

        if q.startswith("Qu'est-ce"):
            return "Il s'agit de"
        if q.startswith("Comment"):
            return "Pour cela, il faut"
        if q.startswith("Pourquoi"):
            return "La raison principale est que"
        if q.startswith("Quels"):
            return "Les principaux sont"
        if q.startswith("Combien"):
            return "Le nombre est de"

        # Fallback générique
        if "comment" in q_lower:
            return "Pour y répondre, il faut"
        return "La réponse est simple :"

    def _add_schema_org(self) -> None:
        """Ajoute Schema.org Article si absent."""

        existing_schemas = self.soup.find_all("script", type="application/ld+json")

        has_article = False
        for script in existing_schemas:
            try:
                if not script.string:
                    continue
                data = json.loads(script.string)
                if data.get("@type") == "Article":
                    has_article = True
            except Exception:
                continue

        if not has_article:
            h1 = self.soup.find("h1")
            title = h1.get_text(strip=True) if h1 else "Article"

            schema = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": title,
                "datePublished": datetime.now().isoformat(),
                "dateModified": datetime.now().isoformat(),
                "author": {
                    "@type": "Organization",
                    "name": "HOTARU AI Optimizer",
                },
                "publisher": {
                    "@type": "Organization",
                    "name": "HOTARU",
                },
            }

            if not self.soup.head and self.soup.html:
                self.soup.html.insert(0, self.soup.new_tag("head"))

            script_tag = self.soup.new_tag("script", type="application/ld+json")
            script_tag.string = json.dumps(schema, indent=2, ensure_ascii=False)
            self.soup.head.append(script_tag)

            self.transformations.append(
                {
                    "type": "schema_org_article",
                    "added": True,
                    "reason": "Ajout Schema.org Article pour meilleure indexation",
                }
            )

    def _add_faq_schema(self) -> None:
        """Génère un Schema.org FAQPage basé sur les H2/H3 questions."""

        questions: List[Dict] = []
        headings = self.soup.find_all(["h2", "h3"])

        for h in headings:
            question_text = h.get_text(strip=True)

            next_p = h.find_next_sibling("p")
            if next_p:
                answer_text = next_p.get_text(strip=True)[:300]

                questions.append(
                    {
                        "@type": "Question",
                        "name": question_text,
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": answer_text,
                        },
                    }
                )

        if questions:
            faq_schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": questions,
            }

            script_tag = self.soup.new_tag("script", type="application/ld+json")
            script_tag.string = json.dumps(faq_schema, indent=2, ensure_ascii=False)
            self.soup.head.append(script_tag)

            self.transformations.append(
                {
                    "type": "faq_schema",
                    "questions_count": len(questions),
                    "reason": "Ajout FAQPage schema pour featured snippets",
                }
            )

    def _improve_semantic_structure(self) -> None:
        """Améliore la structure sémantique HTML5."""

        if not self.soup.find("main"):
            body = self.soup.body
            if body:
                content_start = body.find(["h1", "article"])

                if content_start:
                    main_tag = self.soup.new_tag("main")

                    for sibling in list(content_start.find_next_siblings()):
                        main_tag.append(sibling.extract())

                    main_tag.insert(0, content_start.extract())
                    body.append(main_tag)

                    self.transformations.append(
                        {
                            "type": "semantic_structure",
                            "added": "<main>",
                            "reason": "Amélioration structure HTML5 sémantique",
                        }
                    )

    def get_transformations_summary(self) -> List[Dict]:
        """Retourne le résumé des transformations effectuées."""

        return self.transformations


if __name__ == "__main__":
    # Test manuel simple
    html_test = """
    <html>
    <head><title>Guide SEO</title></head>
    <body>
        <h1>SEO en 2024</h1>
        <h2>Les bases du référencement</h2>
        <p>Le SEO est important pour votre visibilité en ligne.</p>
    </body>
    </html>
    """

    transformer = AIOptimizedTransformer(html_test, {})
    optimized_html = transformer.transform()

    print("=== HTML OPTIMISÉ ===")
    print(optimized_html)
    print("\n=== TRANSFORMATIONS ===")
    for t in transformer.get_transformations_summary():
        print(f"- {t['type']}: {t.get('reason', 'N/A')}")

