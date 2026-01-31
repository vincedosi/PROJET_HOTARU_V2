"""
SMART SCRAPER HYBRIDE
1. Vérifie Sitemap
2. Si Sitemap vide -> Crawl Récursif (BS4)
3. Extrait Titres & H1 pour l'IA
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import random
import re

class SmartScraper:
    def __init__(self, base_url, max_urls=200):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_urls = max_urls
        self.visited = set()
        self.results = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_page_details(self, url):
        """Extrait Title, H1 et Links d'une page."""
        try:
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.status_code != 200: return None
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Extraction Métadonnées
            title = soup.title.string.strip() if soup.title else url.split('/')[-1]
            h1 = soup.find('h1').get_text().strip() if soup.find('h1') else ""
            
            # Nettoyage Titre (Enlever " - NomSite")
            if title and len(title) > 50: title = title[:50] + "..."
            
            # Extraction Liens (pour le crawl)
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                # On garde que les liens internes du même domaine
                if urlparse(full_url).netloc == self.domain:
                    links.append(full_url)
                    
            return {
                "url": url,
                "title": title, # CRUCIAL: On a enfin le vrai nom
                "h1": h1,
                "links": links
            }
        except:
            return None

    def run_analysis(self, progress_callback=None):
        """Lance le crawl hybride."""
        queue = [self.base_url]
        self.visited.add(self.base_url)
        
        crawled_count = 0
        
        while queue and crawled_count < self.max_urls:
            current_url = queue.pop(0)
            
            # Feedback UI
            if progress_callback and crawled_count % 5 == 0:
                progress_callback(f"Analyse: {current_url[:40]}...", crawled_count / self.max_urls)
            
            data = self.get_page_details(current_url)
            
            if data:
                self.results.append(data)
                crawled_count += 1
                
                # Ajout des nouveaux liens à la queue
                for link in data['links']:
                    # Nettoyage des ancres et query params pour éviter les doublons
                    clean_link = link.split('#')[0].split('?')[0]
                    if clean_link not in self.visited and clean_link.startswith("http"):
                        self.visited.add(clean_link)
                        queue.append(clean_link)
            
            time.sleep(random.uniform(0.1, 0.3)) # Politesse

        # Analyse des patterns (Grouping)
        patterns = self.analyze_patterns(self.results)
        
        stats = {
            "total_urls": len(self.results),
            "patterns": len(patterns)
        }
        return self.results, stats

    def analyze_patterns(self, pages):
        """Regroupe les pages par dossier URL."""
        groups = {}
        for p in pages:
            path = urlparse(p['url']).path
            segments = [s for s in path.split('/') if s]
            
            # Logique de groupement (ex: /blog/, /produits/)
            if len(segments) > 0:
                group_key = segments[0] # Premier dossier
            else:
                group_key = "root"
                
            if group_key not in groups:
                groups[group_key] = {"count": 0, "samples": [], "name": group_key}
            
            groups[group_key]["count"] += 1
            groups[group_key]["samples"].append(p) # On stocke tout l'objet page (avec titre)
            
        return list(groups.values())

    def get_pattern_summary(self):
        return self.analyze_patterns(self.results)
