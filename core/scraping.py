"""
SMART SCRAPER HYBRIDE (V5 - Support React + 10K pages)
- Support des SPA React/Vue/Angular
- Limite 10 000 pages fonctionnelle
- Filtres anti-bruit
- Capture HTML complète pour GEO
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SmartScraper:
    def __init__(self, base_url, max_urls=500, use_selenium=False):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_urls = max_urls
        self.visited = set()
        self.results = []
        self.use_selenium = use_selenium
        self.driver = None
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        self.exclude_patterns = [
            'login', 'signin', 'signup', 'register', 'cart', 'checkout', 
            'account', 'admin', 'wp-', 'feed', '.pdf', '.jpg', '.png', 
            'tel:', 'mailto:', 'javascript:', '#'
        ]
        
        # Détecter si le site est en React/SPA
        if self._is_spa_site():
            self.use_selenium = True
            self._init_selenium()

    def _is_spa_site(self):
        """Détecte si le site utilise un framework JS (React, Vue, Angular)"""
        try:
            resp = requests.get(self.base_url, headers=self.headers, timeout=5)
            html = resp.text.lower()
            
            # Patterns typiques des SPA
            spa_patterns = [
                'react', 'vue', 'angular', 'ng-app', 'data-reactroot',
                '<div id="root">', '<div id="app">', '__next'
            ]
            
            return any(pattern in html for pattern in spa_patterns)
        except:
            return False

    def _init_selenium(self):
        """Initialise Selenium pour les sites React"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Impossible d'initialiser Selenium: {e}")
            self.use_selenium = False

    def is_valid_url(self, url):
        """Vérifie si l'URL est pertinente."""
        if any(ex in url.lower() for ex in self.exclude_patterns):
            return False
        return True

    def clean_title(self, title, h1, url):
        """Nettoie le titre pour l'affichage."""
        domain_name = urlparse(url).netloc.split('.')[0].lower()
        
        def is_useful(text):
            if not text or len(text) < 3:
                return False
            text_clean = text.lower().replace(' ', '').replace('-', '')
            if domain_name in text_clean and len(text_clean) < len(domain_name) + 5:
                return False
            return True
        
        if h1 and len(h1) > 10:
            text = h1
        elif title and len(title) > 5:
            text = title
        else:
            text = ""
        
        if text:
            separators = [' - ', ' | ', ' : ', ' — ', ' – ', ' · ']
            for sep in separators:
                if sep in text:
                    parts = [p.strip() for p in text.split(sep)]
                    useful_parts = [p for p in parts if is_useful(p)]
                    if useful_parts:
                        text = max(useful_parts, key=len)
                    break
        
        if not is_useful(text):
            path = urlparse(url).path
            segments = [s for s in path.split('/') if s and s not in ['fr', 'en', 'de', 'es', 'www']]
            if segments:
                text = segments[-1].replace('-', ' ').replace('_', ' ').title()
            else:
                return "Accueil"
        
        text = text.strip()
        return text[:40] + ".." if len(text) > 40 else text

    def get_page_details(self, url):
        try:
            start_time = time.time()
            
            # Utiliser Selenium si nécessaire
            if self.use_selenium and self.driver:
                self.driver.get(url)
                # Attendre le chargement JS
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(1)  # Laisser le JS s'exécuter
                
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                response_time = time.time() - start_time
            else:
                resp = requests.get(url, headers=self.headers, timeout=4)
                response_time = time.time() - start_time
                
                if resp.status_code != 200: 
                    return None
                
                soup = BeautifulSoup(resp.content, 'html.parser')
                html_content = str(soup)
            
            # Extraction des données
            raw_title = soup.title.string.strip() if soup.title else ""
            h1 = soup.find('h1').get_text().strip() if soup.find('h1') else ""
            final_title = self.clean_title(raw_title, h1, url)
            
            meta_desc = ""
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag and meta_tag.get('content'):
                meta_desc = meta_tag['content'].strip()
            
            # Liens
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                
                if urlparse(full_url).netloc == self.domain and self.is_valid_url(full_url):
                    clean_link = full_url.split('#')[0].split('?')[0]
                    if clean_link != url:
                        links.append(clean_link)
            
            # Données GEO
            has_structured_data = bool(soup.find('script', type='application/ld+json'))
            h2_count = len(soup.find_all('h2'))
            lists_count = len(soup.find_all(['ul', 'ol']))
            
            return {
                "url": url,
                "title": final_title,
                "links": list(set(links)),
                "description": meta_desc,
                "h1": h1,
                "response_time": response_time,
                "html_content": html_content,
                "last_modified": "",
                "has_structured_data": has_structured_data,
                "h2_count": h2_count,
                "lists_count": lists_count
            }
        except Exception as e:
            print(f"Erreur scraping {url}: {e}")
            return None

    def run_analysis(self, progress_callback=None):
        queue = [self.base_url]
        self.visited.add(self.base_url)
        crawled_count = 0
        
        try:
            while queue and crawled_count < self.max_urls:
                current_url = queue.pop(0)
                
                if progress_callback and crawled_count % 10 == 0:
                    percent = min(crawled_count / self.max_urls, 0.95)
                    progress_callback(f"Exploration ({crawled_count}/{self.max_urls}): {current_url.split('/')[-1][:30]}", percent)
                
                data = self.get_page_details(current_url)
                
                if data:
                    self.results.append(data)
                    crawled_count += 1
                    
                    for link in data['links']:
                        if link not in self.visited and len(self.visited) < self.max_urls * 2:
                            self.visited.add(link)
                            queue.append(link)
                
                # Pause adaptative selon le nombre de pages
                if self.max_urls > 1000:
                    time.sleep(0.01)  # Très rapide pour gros volumes
                else:
                    time.sleep(0.05)
        
        finally:
            # Fermer Selenium
            if self.driver:
                self.driver.quit()
        
        patterns = self.analyze_patterns(self.results)
        
        if progress_callback:
            progress_callback("Analyse terminée ✓", 1.0)
        
        return self.results, {"total_urls": len(self.results), "patterns": len(patterns)}

    def analyze_patterns(self, pages):
        groups = {}
        for p in pages:
            path = urlparse(p['url']).path
            segments = [s for s in path.split('/') if s]
            
            if len(segments) > 0:
                group_key = segments[0]
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
