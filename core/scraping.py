"""
SMART SCRAPER HYBRIDE (V2 - Deep & Clean)
- Nettoyage intelligent des titres
- Capture du maillage interne (Internal Linking)
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import random
import re

class SmartScraper:
    def __init__(self, base_url, max_urls=300): # Augmenté à 300
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_urls = max_urls
        self.visited = set()
        self.results = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def clean_title(self, title, h1, domain):
        """Choisit le meilleur titre et le nettoie."""
        # 1. Candidat principal
        text = h1 if h1 and len(h1) > 5 else title
        if not text: return "Sans titre"

        # 2. Nettoyage (Enlever le nom du site souvent à la fin)
        # Ex: "Devenir Marin - La Marine Recrute" -> "Devenir Marin"
        site_name = domain.split('.')[0]
        text = re.split(r' [-|] ', text)[0] # Coupe au premier tiret ou pipe
        
        # 3. Si le titre est juste le nom de domaine, c'est nul
        if site_name in text.lower() and len(text) < len(site_name) + 5:
            return h1 if h1 else "Page Accueil"
            
        return text.strip()

    def get_page_details(self, url):
        try:
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.status_code != 200: return None
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Extraction Raw
            raw_title = soup.title.string.strip() if soup.title else ""
            h1 = soup.find('h1').get_text().strip() if soup.find('h1') else ""
            
            # Nettoyage Intelligent
            final_name = self.clean_title(raw_title, h1, self.domain)
            
            # Extraction Liens Internes (Pour le maillage)
            internal_links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                # On garde seulement les liens vers le même domaine
                if urlparse(full_url).netloc == self.domain:
                    internal_links.append(full_url.split('#')[0]) # Retire les ancres
                    
            return {
                "url": url,
                "title": final_name, # Titre propre
                "depth": 0, # Sera calculé dans la boucle
                "links": list(set(internal_links)) # Liens uniques sortants
            }
        except:
            return None

    def run_analysis(self, progress_callback=None):
        queue = [self.base_url]
        self.visited.add(self.base_url)
        crawled_count = 0
        
        while queue and crawled_count < self.max_urls:
            current_url = queue.pop(0)
            
            if progress_callback and crawled_count % 5 == 0:
                progress_callback(f"Exploration ({crawled_count}): {current_url.split('/')[-1][:30]}...", crawled_count / self.max_urls)
            
            data = self.get_page_details(current_url)
            
            if data:
                self.results.append(data)
                crawled_count += 1
                
                # Ajout des enfants à la queue
                for link in data['links']:
                    if link not in self.visited:
                        self.visited.add(link)
                        queue.append(link)
            
            time.sleep(0.1) 

        patterns = self.analyze_patterns(self.results)
        return self.results, {"total_urls": len(self.results), "patterns": len(patterns)}

    def analyze_patterns(self, pages):
        groups = {}
        for p in pages:
            path = urlparse(p['url']).path
            segments = [s for s in path.split('/') if s]
            
            if len(segments) > 0:
                group_key = segments[0]
                if len(segments) > 1 and group_key in ['fr', 'en']: # Ignorer /fr/
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
