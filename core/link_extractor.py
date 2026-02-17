"""
Extracteur de liens unifié - Élimine duplication entre V1 et V2 (60+ LOC)
Utilisé par core/scraping.py et core/scraping_v2.py
"""
import re
from typing import List, Set, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


class LinkExtractor:
    """Classe pour extraire les liens de manière robuste depuis plusieurs sources."""

    @staticmethod
    def extract_from_soup(soup: BeautifulSoup) -> List[str]:
        """Extrait les liens depuis les tags <a href>."""
        return [a.get("href", "") for a in soup.find_all("a", href=True)]

    @staticmethod
    def extract_from_data_href(soup: BeautifulSoup) -> List[str]:
        """Extrait les liens depuis data-href (SPA/frameworks modernes)."""
        links = []
        for tag in soup.find_all(attrs={"data-href": True}):
            href = tag.get("data-href", "").strip()
            if href and (href.startswith(("http", "/")) or not href.startswith("#")):
                links.append(href)
        return links

    @staticmethod
    def extract_from_markdown(markdown_text: str) -> List[str]:
        """Extrait les liens depuis du texte Markdown."""
        if not markdown_text or len(markdown_text) < 100:
            return []

        links = []

        # Pattern Markdown: [texte](url)
        for m in re.findall(r"\]\s*\(\s*([^)\s]+)\s*\)", markdown_text):
            if m.startswith(("http", "/")):
                links.append(m)

        # Pattern URL absolue: https?://...
        for m in re.findall(r"https?://[^\s\]\)\"\'>\>]+", markdown_text):
            clean = m.split(")")[0].split("]")[0]
            links.append(clean)

        return links

    @staticmethod
    def extract_from_js_result(js_result) -> List[str]:
        """Extrait les liens depuis le résultat d'exécution JS."""
        if js_result is None:
            return []

        links = []

        if isinstance(js_result, list):
            links = [u for u in js_result if isinstance(u, str) and u.startswith(("http", "/"))]

        elif isinstance(js_result, dict):
            for value in js_result.values():
                if isinstance(value, list):
                    links = [
                        u for u in value if isinstance(u, str) and u.startswith(("http", "/"))
                    ]
                    break

        return links

    @staticmethod
    def merge_sources(
        crawl4ai_links: Optional[List[str]] = None,
        soup_links: Optional[List[str]] = None,
        data_href_links: Optional[List[str]] = None,
        js_links: Optional[List[str]] = None,
        markdown_links: Optional[List[str]] = None,
    ) -> Set[str]:
        """
        Fusionne toutes les sources de liens dans un set (déduplication auto).

        Args:
            crawl4ai_links: Liens extraits par Crawl4AI
            soup_links: Liens depuis <a href>
            data_href_links: Liens depuis data-href
            js_links: Liens depuis JS execution
            markdown_links: Liens depuis Markdown

        Returns:
            Set de liens uniques
        """
        result = set()
        for links in [crawl4ai_links, soup_links, data_href_links, js_links, markdown_links]:
            if links:
                result.update(links)
        return result

    @staticmethod
    def filter_by_domain(
        links: List[str],
        domain_set: Set[str],
        base_url: str,
        exclude_patterns: List[str] = None,
    ) -> tuple[List[str], int]:
        """
        Filtre les liens par domaine et motifs d'exclusion.

        Args:
            links: Liste des liens à filtrer
            domain_set: Set de domaines autorisés
            base_url: URL de base pour résolution des URLs relatives
            exclude_patterns: Motifs à exclure (*.pdf, tel:, etc.)

        Returns:
            (Liste des liens valides, Nombre de liens filtrés)
        """
        exclude_patterns = exclude_patterns or []
        valid_links = []
        filtered_count = 0

        for href in links:
            if not href:
                continue

            # Exclude patterns check
            if any(pattern in href.lower() for pattern in exclude_patterns):
                filtered_count += 1
                continue

            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            netloc_lower = parsed.netloc.lower()

            # Domain check
            if netloc_lower in domain_set:
                valid_links.append(full_url)
            else:
                filtered_count += 1

        return valid_links, filtered_count


__all__ = ["LinkExtractor"]
