"""
HOTARU - Smart Scraping Module
Sitemap scanning, URL clustering, and intelligent sampling.
"""

import re
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np
import streamlit as st


@dataclass
class URLInfo:
    """Information about a URL."""
    url: str
    path: str
    depth: int
    cluster: Optional[int] = None
    score: Optional[float] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1: Optional[str] = None
    word_count: Optional[int] = None


class SmartScraper:
    """
    Smart web scraper with sitemap analysis and intelligent sampling.

    Features:
    - Sitemap detection and parsing
    - URL clustering based on path patterns
    - Intelligent sampling from each cluster
    - Async fetching for performance
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

    def __init__(self, base_url: str, max_urls: int = 500, sample_size: int = 50):
        """
        Initialize the scraper.

        Args:
            base_url: The website URL to scrape
            max_urls: Maximum URLs to collect from sitemap
            sample_size: Number of URLs to sample for detailed analysis
        """
        self.base_url = self._normalize_url(base_url)
        self.domain = urlparse(self.base_url).netloc
        self.max_urls = max_urls
        self.sample_size = sample_size
        self.urls: List[URLInfo] = []
        self.sampled_urls: List[URLInfo] = []

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize a URL to have a consistent format."""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def find_sitemap(self) -> Optional[str]:
        """
        Try to find the sitemap URL.

        Returns:
            Sitemap URL if found, None otherwise
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; HotaruBot/1.0)'
        }

        # Try robots.txt first
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            response = requests.get(robots_url, headers=headers, timeout=10)

            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        return sitemap_url
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
        """
        Parse a sitemap and extract URLs.

        Args:
            sitemap_url: URL of the sitemap

        Returns:
            List of URLs found in the sitemap
        """
        urls = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; HotaruBot/1.0)'
        }

        try:
            response = requests.get(sitemap_url, headers=headers, timeout=30)

            if response.status_code != 200:
                return urls

            soup = BeautifulSoup(response.content, 'lxml-xml')

            # Check if it's a sitemap index
            sitemap_tags = soup.find_all('sitemap')
            if sitemap_tags:
                # It's an index, parse each sub-sitemap
                for sitemap in sitemap_tags[:10]:  # Limit to 10 sub-sitemaps
                    loc = sitemap.find('loc')
                    if loc:
                        sub_urls = self.parse_sitemap(loc.text)
                        urls.extend(sub_urls)

                        if len(urls) >= self.max_urls:
                            break
            else:
                # Regular sitemap, extract URLs
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
        """
        Fallback: crawl the site if no sitemap is found.

        Args:
            max_pages: Maximum number of pages to crawl

        Returns:
            List of discovered URLs
        """
        visited: Set[str] = set()
        to_visit: List[str] = [self.base_url]
        urls: List[str] = []

        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; HotaruBot/1.0)'
        }

        while to_visit and len(urls) < max_pages:
            current_url = to_visit.pop(0)

            if current_url in visited:
                continue

            try:
                response = requests.get(current_url, headers=headers, timeout=10)
                visited.add(current_url)

                if response.status_code == 200:
                    urls.append(current_url)

                    # Parse links
                    soup = BeautifulSoup(response.content, 'html.parser')

                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        full_url = urljoin(current_url, href)
                        parsed = urlparse(full_url)

                        # Only follow internal links
                        if parsed.netloc == self.domain and full_url not in visited:
                            # Clean URL
                            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                            if clean_url not in visited:
                                to_visit.append(clean_url)

            except Exception:
                continue

        return urls

    def cluster_urls(self, urls: List[str], n_clusters: int = 10) -> Dict[int, List[str]]:
        """
        Cluster URLs based on their path patterns.

        Args:
            urls: List of URLs to cluster
            n_clusters: Number of clusters

        Returns:
            Dictionary mapping cluster ID to list of URLs
        """
        if len(urls) < n_clusters:
            n_clusters = max(1, len(urls) // 2)

        # Extract paths for clustering
        paths = []
        for url in urls:
            parsed = urlparse(url)
            # Tokenize path
            path = parsed.path.replace('/', ' ').replace('-', ' ').replace('_', ' ')
            paths.append(path)

        # Vectorize paths
        vectorizer = TfidfVectorizer(max_features=100, stop_words='english')

        try:
            X = vectorizer.fit_transform(paths)

            # Cluster
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)

            # Group by cluster
            clusters: Dict[int, List[str]] = {}
            for url, label in zip(urls, labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(url)

            return clusters

        except Exception:
            # Fallback: single cluster
            return {0: urls}

    def smart_sample(self, clusters: Dict[int, List[str]]) -> List[str]:
        """
        Intelligently sample URLs from each cluster.

        Args:
            clusters: Dictionary of clustered URLs

        Returns:
            List of sampled URLs
        """
        sampled = []
        samples_per_cluster = max(1, self.sample_size // len(clusters))

        for cluster_id, cluster_urls in clusters.items():
            # Sample from this cluster
            n_samples = min(samples_per_cluster, len(cluster_urls))

            # Prefer diverse depth levels
            by_depth: Dict[int, List[str]] = {}
            for url in cluster_urls:
                depth = urlparse(url).path.count('/')
                if depth not in by_depth:
                    by_depth[depth] = []
                by_depth[depth].append(url)

            # Sample from each depth
            cluster_samples = []
            for depth_urls in by_depth.values():
                n = max(1, n_samples // len(by_depth))
                cluster_samples.extend(
                    np.random.choice(depth_urls, min(n, len(depth_urls)), replace=False)
                )

            sampled.extend(cluster_samples[:samples_per_cluster])

        return sampled[:self.sample_size]

    async def fetch_page_info(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Optional[URLInfo]:
        """
        Fetch and analyze a single page.

        Args:
            session: aiohttp session
            url: URL to fetch

        Returns:
            URLInfo with page details or None on error
        """
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Extract info
                title = soup.title.string if soup.title else None
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                meta_description = meta_desc['content'] if meta_desc else None
                h1_tag = soup.find('h1')
                h1 = h1_tag.get_text(strip=True) if h1_tag else None

                # Word count (approximate)
                text = soup.get_text(separator=' ', strip=True)
                word_count = len(text.split())

                parsed = urlparse(url)

                return URLInfo(
                    url=url,
                    path=parsed.path,
                    depth=parsed.path.count('/'),
                    title=title,
                    meta_description=meta_description,
                    h1=h1,
                    word_count=word_count
                )

        except Exception:
            return None

    async def analyze_urls(self, urls: List[str]) -> List[URLInfo]:
        """
        Analyze multiple URLs concurrently.

        Args:
            urls: List of URLs to analyze

        Returns:
            List of URLInfo objects
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; HotaruBot/1.0)'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = [self.fetch_page_info(session, url) for url in urls]
            results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]

    def run_analysis(self, progress_callback=None) -> Tuple[List[URLInfo], Dict]:
        """
        Run the complete analysis pipeline.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (analyzed URLs, analysis stats)
        """
        stats = {
            'sitemap_found': False,
            'total_urls_found': 0,
            'clusters': 0,
            'urls_analyzed': 0
        }

        if progress_callback:
            progress_callback("Recherche du sitemap...", 0.1)

        # Find sitemap
        sitemap_url = self.find_sitemap()

        if sitemap_url:
            stats['sitemap_found'] = True
            if progress_callback:
                progress_callback(f"Sitemap trouvé: {sitemap_url}", 0.2)

            # Parse sitemap
            urls = self.parse_sitemap(sitemap_url)
        else:
            if progress_callback:
                progress_callback("Pas de sitemap, crawling du site...", 0.2)

            # Fallback to crawling
            urls = self.crawl_site()

        stats['total_urls_found'] = len(urls)

        if not urls:
            return [], stats

        if progress_callback:
            progress_callback(f"{len(urls)} URLs trouvées, clustering...", 0.4)

        # Cluster URLs
        n_clusters = min(10, max(3, len(urls) // 20))
        clusters = self.cluster_urls(urls, n_clusters)
        stats['clusters'] = len(clusters)

        if progress_callback:
            progress_callback(f"{len(clusters)} clusters identifiés, échantillonnage...", 0.5)

        # Smart sample
        sampled_urls = self.smart_sample(clusters)

        if progress_callback:
            progress_callback(f"Analyse de {len(sampled_urls)} pages...", 0.6)

        # Analyze sampled URLs
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            analyzed = loop.run_until_complete(self.analyze_urls(sampled_urls))
        finally:
            loop.close()

        stats['urls_analyzed'] = len(analyzed)

        # Assign cluster IDs
        cluster_map = {}
        for cluster_id, cluster_urls in clusters.items():
            for url in cluster_urls:
                cluster_map[url] = cluster_id

        for url_info in analyzed:
            url_info.cluster = cluster_map.get(url_info.url, 0)

        if progress_callback:
            progress_callback("Analyse terminée!", 1.0)

        return analyzed, stats
