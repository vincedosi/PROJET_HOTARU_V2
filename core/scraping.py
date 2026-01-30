"""
HOTARU - Smart Scraping Module
Sitemap scanning, URL pattern detection, and intelligent sampling.

Features:
- Regex-based URL pattern detection
- Smart sampling: only analyze 3 specimens per pattern
- Inheritance: other pages in pattern inherit scores
"""

import re
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import streamlit as st


@dataclass
class URLInfo:
    """Information about a URL."""
    url: str
    path: str
    depth: int
    cluster: Optional[int] = None
    pattern_group: Optional[str] = None
    is_specimen: bool = False
    score: Optional[float] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1: Optional[str] = None
    word_count: Optional[int] = None


@dataclass
class URLPattern:
    """A detected URL pattern (template)."""
    pattern: str
    regex: re.Pattern
    example_urls: List[str] = field(default_factory=list)
    specimen_urls: List[str] = field(default_factory=list)
    count: int = 0
    category_name: str = ""


class SmartScraper:
    """
    Smart web scraper with pattern detection and intelligent sampling.

    Smart Sampling Logic:
    - Detects URL patterns (e.g., /produit/*, /cirfa/*)
    - If 50+ pages share a pattern, only analyzes 3 specimens
    - Other pages inherit scores from their pattern group
    """

    SITEMAP_PATHS = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap/',
        '/sitemaps.xml',
        '/sitemap1.xml',
        '/post-sitemap.xml',
        '/page-sitemap.xml',
    ]

    # Common URL patterns to detect
    PATTERN_SIGNATURES = [
        # E-commerce
        (r'/produit[s]?/[^/]+/?$', 'Produits'),
        (r'/product[s]?/[^/]+/?$', 'Products'),
        (r'/article[s]?/[^/]+/?$', 'Articles'),
        (r'/item[s]?/[^/]+/?$', 'Items'),
        (r'/shop/[^/]+/?$', 'Boutique'),
        # Blog
        (r'/blog/[^/]+/?$', 'Blog'),
        (r'/post[s]?/[^/]+/?$', 'Posts'),
        (r'/actualite[s]?/[^/]+/?$', 'Actualites'),
        (r'/news/[^/]+/?$', 'News'),
        # Categories
        (r'/categor(y|ie)[s]?/[^/]+/?$', 'Categories'),
        (r'/tag[s]?/[^/]+/?$', 'Tags'),
        # Listings
        (r'/annonce[s]?/[^/]+/?$', 'Annonces'),
        (r'/offre[s]?/[^/]+/?$', 'Offres'),
        (r'/emploi[s]?/[^/]+/?$', 'Emplois'),
        (r'/job[s]?/[^/]+/?$', 'Jobs'),
        # Institutional
        (r'/cirfa[^/]*/[^/]+/?$', 'CIRFA'),
        (r'/agence[s]?/[^/]+/?$', 'Agences'),
        (r'/bureau[x]?/[^/]+/?$', 'Bureaux'),
        (r'/magasin[s]?/[^/]+/?$', 'Magasins'),
        (r'/store[s]?/[^/]+/?$', 'Stores'),
        # Generic patterns with IDs
        (r'/[^/]+/\d+/?$', 'Pages numerotees'),
        (r'/[^/]+-\d+/?$', 'Pages avec ID'),
    ]

    def __init__(
        self,
        base_url: str,
        max_urls: int = 500,
        sample_size: int = 50,
        specimens_per_pattern: int = 3
    ):
        """
        Initialize the scraper.

        Args:
            base_url: The website URL to scrape
            max_urls: Maximum URLs to collect from sitemap
            sample_size: Number of unique URLs to sample for analysis
            specimens_per_pattern: Number of specimens to analyze per pattern
        """
        self.base_url = self._normalize_url(base_url)
        self.domain = urlparse(self.base_url).netloc
        self.max_urls = max_urls
        self.sample_size = sample_size
        self.specimens_per_pattern = specimens_per_pattern
        self.urls: List[str] = []
        self.patterns: Dict[str, URLPattern] = {}
        self.url_to_pattern: Dict[str, str] = {}

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize a URL to have a consistent format."""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def find_sitemap(self) -> Optional[str]:
        """Try to find the sitemap URL."""
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; HotaruBot/1.0)'}

        # Try robots.txt first
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            response = requests.get(robots_url, headers=headers, timeout=10)

            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        return line.split(':', 1)[1].strip()
        except Exception:
            pass

        # Try common sitemap paths
        for path in self.SITEMAP_PATHS:
            try:
                sitemap_url = urljoin(self.base_url, path)
                response = requests.head(sitemap_url, headers=headers, timeout=5)
                if response.status_code == 200:
                    return sitemap_url
            except Exception:
                continue

        return None

    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse a sitemap and extract URLs."""
        urls = []
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; HotaruBot/1.0)'}

        try:
            response = requests.get(sitemap_url, headers=headers, timeout=30)
            if response.status_code != 200:
                return urls

            soup = BeautifulSoup(response.content, 'lxml-xml')

            # Check if it's a sitemap index
            sitemap_tags = soup.find_all('sitemap')
            if sitemap_tags:
                for sitemap in sitemap_tags[:10]:
                    loc = sitemap.find('loc')
                    if loc:
                        sub_urls = self.parse_sitemap(loc.text)
                        urls.extend(sub_urls)
                        if len(urls) >= self.max_urls:
                            break
            else:
                url_tags = soup.find_all('url')
                for url_tag in url_tags:
                    loc = url_tag.find('loc')
                    if loc:
                        urls.append(loc.text)
                        if len(urls) >= self.max_urls:
                            break

        except Exception as e:
            st.warning(f"Erreur parsing sitemap: {str(e)}")

        return urls[:self.max_urls]

    def crawl_site(self, max_pages: int = 100) -> List[str]:
        """Fallback: crawl the site if no sitemap is found."""
        visited: Set[str] = set()
        to_visit: List[str] = [self.base_url]
        urls: List[str] = []
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; HotaruBot/1.0)'}

        while to_visit and len(urls) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue

            try:
                response = requests.get(current_url, headers=headers, timeout=10)
                visited.add(current_url)

                if response.status_code == 200:
                    urls.append(current_url)
                    soup = BeautifulSoup(response.content, 'html.parser')

                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        full_url = urljoin(current_url, href)
                        parsed = urlparse(full_url)

                        if parsed.netloc == self.domain and full_url not in visited:
                            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                            if clean_url not in visited:
                                to_visit.append(clean_url)

            except Exception:
                continue

        return urls

    def detect_url_patterns(self, urls: List[str]) -> Dict[str, URLPattern]:
        """
        Detect URL patterns using regex matching.

        This is the Smart Sampling core logic:
        - Groups URLs by their structural pattern
        - Identifies high-frequency patterns (e.g., product pages)
        """
        patterns: Dict[str, URLPattern] = {}

        # First pass: try predefined patterns
        for url in urls:
            parsed = urlparse(url)
            path = parsed.path

            matched = False
            for pattern_regex, category_name in self.PATTERN_SIGNATURES:
                if re.search(pattern_regex, path, re.IGNORECASE):
                    pattern_key = pattern_regex

                    if pattern_key not in patterns:
                        patterns[pattern_key] = URLPattern(
                            pattern=pattern_regex,
                            regex=re.compile(pattern_regex, re.IGNORECASE),
                            category_name=category_name
                        )

                    patterns[pattern_key].example_urls.append(url)
                    patterns[pattern_key].count += 1
                    self.url_to_pattern[url] = pattern_key
                    matched = True
                    break

            # Second pass: auto-detect patterns from URL structure
            if not matched:
                # Extract pattern from path structure
                path_parts = [p for p in path.split('/') if p]

                if len(path_parts) >= 2:
                    # Create pattern from first directory level
                    base_pattern = f"/{path_parts[0]}/[^/]+/?$"
                    pattern_key = base_pattern

                    if pattern_key not in patterns:
                        patterns[pattern_key] = URLPattern(
                            pattern=base_pattern,
                            regex=re.compile(base_pattern, re.IGNORECASE),
                            category_name=path_parts[0].title()
                        )

                    patterns[pattern_key].example_urls.append(url)
                    patterns[pattern_key].count += 1
                    self.url_to_pattern[url] = pattern_key
                else:
                    # Root-level pages - unique
                    self.url_to_pattern[url] = 'unique'

        return patterns

    def smart_sample_urls(
        self,
        urls: List[str],
        patterns: Dict[str, URLPattern]
    ) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Intelligently sample URLs based on detected patterns.

        Smart Sampling Rules:
        - If a pattern has 10+ URLs: only analyze 3 specimens
        - Specimens are chosen from different depth levels
        - Other URLs in the pattern will inherit specimen analysis
        """
        specimens_to_analyze: List[str] = []
        pattern_specimens: Dict[str, List[str]] = {}

        # Process each pattern
        for pattern_key, pattern in patterns.items():
            pattern_urls = pattern.example_urls

            if len(pattern_urls) >= 10:
                # High-frequency pattern: smart sample
                # Pick specimens from different positions
                indices = [0, len(pattern_urls) // 2, len(pattern_urls) - 1]
                specimens = [pattern_urls[i] for i in indices if i < len(pattern_urls)]
                specimens = specimens[:self.specimens_per_pattern]
            else:
                # Low-frequency: analyze all
                specimens = pattern_urls[:self.specimens_per_pattern]

            pattern.specimen_urls = specimens
            pattern_specimens[pattern_key] = specimens
            specimens_to_analyze.extend(specimens)

        # Add unique pages (not matching any pattern)
        unique_urls = [u for u in urls if self.url_to_pattern.get(u) == 'unique']
        specimens_to_analyze.extend(unique_urls[:10])

        # Limit total specimens
        return specimens_to_analyze[:self.sample_size], pattern_specimens

    async def fetch_page_info(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Optional[URLInfo]:
        """Fetch and analyze a single page."""
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                title = soup.title.string if soup.title else None
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                meta_description = meta_desc['content'] if meta_desc else None
                h1_tag = soup.find('h1')
                h1 = h1_tag.get_text(strip=True) if h1_tag else None
                text = soup.get_text(separator=' ', strip=True)
                word_count = len(text.split())

                parsed = urlparse(url)
                pattern_group = self.url_to_pattern.get(url)

                return URLInfo(
                    url=url,
                    path=parsed.path,
                    depth=parsed.path.count('/'),
                    pattern_group=pattern_group,
                    is_specimen=True,
                    title=title,
                    meta_description=meta_description,
                    h1=h1,
                    word_count=word_count
                )

        except Exception:
            return None

    async def analyze_urls(self, urls: List[str]) -> List[URLInfo]:
        """Analyze multiple URLs concurrently."""
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; HotaruBot/1.0)'}

        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = [self.fetch_page_info(session, url) for url in urls]
            results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]

    def inherit_scores_for_pattern(
        self,
        analyzed_specimens: List[URLInfo],
        all_urls: List[str],
        patterns: Dict[str, URLPattern]
    ) -> List[URLInfo]:
        """
        Create URLInfo for all URLs, inheriting scores from specimens.

        This is the key optimization: URLs in the same pattern group
        inherit the average score from their analyzed specimens.
        """
        all_results: List[URLInfo] = []

        # Create specimen lookup by pattern
        pattern_scores: Dict[str, Dict] = {}
        for specimen in analyzed_specimens:
            pattern = specimen.pattern_group
            if pattern and pattern != 'unique':
                if pattern not in pattern_scores:
                    pattern_scores[pattern] = {
                        'specimens': [],
                        'avg_title_len': 0,
                        'avg_word_count': 0,
                        'has_h1_ratio': 0,
                        'has_meta_ratio': 0
                    }
                pattern_scores[pattern]['specimens'].append(specimen)

        # Calculate averages per pattern
        for pattern, data in pattern_scores.items():
            specimens = data['specimens']
            if specimens:
                data['avg_title_len'] = sum(
                    len(s.title or '') for s in specimens
                ) / len(specimens)
                data['avg_word_count'] = sum(
                    s.word_count or 0 for s in specimens
                ) / len(specimens)
                data['has_h1_ratio'] = sum(
                    1 for s in specimens if s.h1
                ) / len(specimens)
                data['has_meta_ratio'] = sum(
                    1 for s in specimens if s.meta_description
                ) / len(specimens)

        # Create URLInfo for all URLs
        analyzed_urls = {s.url for s in analyzed_specimens}

        for url in all_urls:
            if url in analyzed_urls:
                # Already analyzed - find and add
                for specimen in analyzed_specimens:
                    if specimen.url == url:
                        all_results.append(specimen)
                        break
            else:
                # Inherit from pattern
                pattern = self.url_to_pattern.get(url)
                parsed = urlparse(url)

                url_info = URLInfo(
                    url=url,
                    path=parsed.path,
                    depth=parsed.path.count('/'),
                    pattern_group=pattern,
                    is_specimen=False
                )

                # Inherit characteristics from pattern
                if pattern and pattern in pattern_scores:
                    data = pattern_scores[pattern]
                    # Approximate values based on pattern averages
                    url_info.word_count = int(data['avg_word_count'])
                    url_info.title = f"[Herite] {pattern_scores[pattern]['specimens'][0].title or 'Page'}"[:50] if data['specimens'] else None

                all_results.append(url_info)

        return all_results

    def run_analysis(
        self,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Tuple[List[URLInfo], Dict]:
        """
        Run the complete analysis pipeline with Smart Sampling.

        Returns:
            Tuple of (analyzed URLs, analysis stats)
        """
        stats = {
            'sitemap_found': False,
            'total_urls_found': 0,
            'patterns_detected': 0,
            'specimens_analyzed': 0,
            'urls_inherited': 0,
            'clusters': 0
        }

        if progress_callback:
            progress_callback("Recherche du sitemap...", 0.1)

        # Find sitemap
        sitemap_url = self.find_sitemap()

        if sitemap_url:
            stats['sitemap_found'] = True
            if progress_callback:
                progress_callback(f"Sitemap trouve!", 0.15)
            urls = self.parse_sitemap(sitemap_url)
        else:
            if progress_callback:
                progress_callback("Pas de sitemap, crawling...", 0.15)
            urls = self.crawl_site()

        self.urls = urls
        stats['total_urls_found'] = len(urls)

        if not urls:
            return [], stats

        if progress_callback:
            progress_callback(f"{len(urls)} URLs trouvees, detection patterns...", 0.25)

        # Detect URL patterns (Smart Sampling)
        patterns = self.detect_url_patterns(urls)
        self.patterns = patterns
        stats['patterns_detected'] = len(patterns)

        if progress_callback:
            progress_callback(f"{len(patterns)} patterns detectes, echantillonnage...", 0.35)

        # Smart sample URLs
        specimens, pattern_specimens = self.smart_sample_urls(urls, patterns)
        stats['specimens_analyzed'] = len(specimens)

        if progress_callback:
            progress_callback(f"Analyse de {len(specimens)} specimens...", 0.45)

        # Analyze specimens
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            analyzed = loop.run_until_complete(self.analyze_urls(specimens))
        finally:
            loop.close()

        if progress_callback:
            progress_callback("Heritage des scores...", 0.8)

        # Inherit scores for non-analyzed URLs
        all_results = self.inherit_scores_for_pattern(analyzed, urls, patterns)
        stats['urls_inherited'] = len(all_results) - len(analyzed)

        # Assign cluster IDs based on patterns
        pattern_to_cluster: Dict[str, int] = {}
        cluster_id = 0
        for url_info in all_results:
            pattern = url_info.pattern_group
            if pattern:
                if pattern not in pattern_to_cluster:
                    pattern_to_cluster[pattern] = cluster_id
                    cluster_id += 1
                url_info.cluster = pattern_to_cluster[pattern]
            else:
                url_info.cluster = cluster_id
                cluster_id += 1

        stats['clusters'] = len(pattern_to_cluster)

        if progress_callback:
            progress_callback("Analyse terminee!", 1.0)

        return all_results, stats

    def get_pattern_summary(self) -> List[Dict]:
        """Get a summary of detected patterns for display."""
        summary = []
        for pattern_key, pattern in self.patterns.items():
            summary.append({
                'name': pattern.category_name,
                'count': pattern.count,
                'specimens': len(pattern.specimen_urls),
                'example': pattern.example_urls[0] if pattern.example_urls else '',
                # 'samples' is a list of URLs for audit_geo.py graph building
                'samples': pattern.example_urls[:5] if pattern.example_urls else []
            })
        return sorted(summary, key=lambda x: x['count'], reverse=True)
