"""
SMART SCRAPER HYBRIDE (V3 - Deep & Smart)
- Limite augmentée (500 URLs)
- Filtres anti-bruit (login, admin, etc.)
- Priorité au contenu
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import random
import re

class SmartScraper:
    def __init__(self, base_url, max_urls=500): # On pousse à 500
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_urls = max_urls
        self.visited = set()
        self.results = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # On ignore ces patterns qui n'apportent pas de valeur SEO
        self.exclude_patterns = [
            'login', 'signin', 'signup', 'register', 'cart', 'checkout', 
            'account', 'admin', 'wp-', 'feed', '.pdf', '.jpg', '.png', 
            'tel:', 'mailto:', 'javascript:', '#'
        ]

    def is_valid_url(self, url):
        """Vérifie si l'URL est pertinente."""
        if any(ex in url.lower() for ex in self.exclude_patterns):
            return False
        return True

    def clean_title(self, title, h1):
        """Nettoie le titre pour l'affichage."""
        text = h1 if h1 and len(h1) > 5 else title
        if not text: return "Page sans titre"
        
        # Nettoyage classique (Enlever le nom du site à la fin)
        separators = [' - ', ' | ', ' : ', ' — ']
        for sep in separators:
            if sep in text:
                text = text.split(sep)[0]
                
        return text.strip()[:40] # On coupe si trop long

    def get_page_details(self, url):
        try:
            resp = requests.get(url, headers=self.headers, timeout=4)
            if resp.status_code != 200: return None
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            raw_title = soup.title.string.strip() if soup.title else ""
            h1 = soup.find('h1').get_text().strip() if soup.find('h1') else ""
            final_title = self.clean_title(raw_title, h1)
            
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                
                # On ne garde que les liens du domaine et valides
                if urlparse(full_url).netloc == self.domain and self.is_valid_url(full_url):
                    clean_link = full_url.split('#')[0].split('?')[0] # Retire ancres et params
                    if clean_link != url: # Pas de lien vers soi-même
                        links.append(clean_link)
                    
            return {
                "url": url,
                "title": final_title,
                "links": list(set(links))
            }
        except:
            return None

    def run_analysis(self, progress_callback=None):
        queue = [self.base_url]
        self.visited.add(self.base_url)
        crawled_count = 0
        
        while queue and crawled_count < self.max_urls:
            current_url = queue.pop(0)
            
            # Feedback visuel tous les 10 items
            if progress_callback and crawled_count % 10 == 0:
                percent = min(crawled_count / self.max_urls, 0.95)
                progress_callback(f"Exploration ({crawled_count}): {current_url.split('/')[-1]}", percent)
            
            data = self.get_page_details(current_url)
            
            if data:
                self.results.append(data)
                crawled_count += 1
                
                # Ajout des liens à la file d'attente
                for link in data['links']:
                    if link not in self.visited:
                        self.visited.add(link)
                        queue.append(link)
            
            time.sleep(0.05) # Très rapide

        # Analyse des clusters
        patterns = self.analyze_patterns(self.results)
        return self.results, {"total_urls": len(self.results), "patterns": len(patterns)}

    def analyze_patterns(self, pages):
        groups = {}
        for p in pages:
            path = urlparse(p['url']).path
            segments = [s for s in path.split('/') if s]
            
            # Logique de dossier intelligent
            if len(segments) > 0:
                group_key = segments[0]
                # Si le premier segment est une langue (fr, en), on prend le suivant
                if group_key in ['fr', 'en', 'de', 'es'] and len(segments) > 1:
                    group_key = segments[1]
            else:
                group_key = "Accueil"
                
            if group_key not in groups:
                groups[group_key] = {"count": 0, "samples": [], "name": group_key}
            
            groups[group_key]["count"] += 1
            groups[group_key]["samples"].append(p)
            
        return list(groups.values())
    
    def get_pattern_summary(self):
        return self.analyze_patterns(self.results)
