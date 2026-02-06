"""
SMART SCRAPER HYBRIDE (V7 - LOGS STREAMLIT + COMPTEUR + VITESSE)
- Logs visibles dans l'interface Streamlit
- Compteur de pages en temps réel
- Optimisation vitesse (threading + requests session)
- Support React/SPA
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed

class SmartScraper:
    def __init__(self, base_url, max_urls=500, use_selenium=False):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.max_urls = max_urls
        self.visited = set()
        self.results = []
        self.use_selenium = use_selenium
        self.driver = None
        self.log_callback = None
        
        # Session requests pour réutiliser la connexion (+ rapide)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Compteurs de debug
        self.stats = {
            'pages_crawled': 0,
            'pages_skipped': 0,
            'links_discovered': 0,
            'links_filtered': 0,
            'links_duplicate': 0,
            'errors': 0,
            'queue_full_blocks': 0
        }
        
        # Filtres anti-bruit réduits (seulement les vrais parasites)
        self.exclude_patterns = [
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.doc', '.docx',
            'tel:', 'mailto:', 'javascript:', 'void(0)'
        ]
        
        # Détecter si le site est en React/SPA
        if self._is_spa_site():
            self.use_selenium = True
            self._init_selenium()

    def _log(self, message):
        """Log visible dans Streamlit"""
        if self.log_callback:
            self.log_callback(message)

    def _is_spa_site(self):
        """Détecte si le site utilise un framework JS"""
        try:
            resp = self.session.get(self.base_url, timeout=5)
            html = resp.text.lower()
            spa_patterns = ['react', 'vue', 'angular', 'ng-app', 'data-reactroot', '<div id="root">', '<div id="app">', '__next']
            detected = any(pattern in html for pattern in spa_patterns)
            return detected
        except:
            return False

    def _init_selenium(self):
        """Initialise Selenium"""
        try:
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument(f'user-agent={self.session.headers["User-Agent"]}')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self._log("✅ Mode Selenium activé (React/SPA détecté)")
        except Exception as e:
            self._log(f"⚠️ Selenium non disponible: {e}")
            self.use_selenium = False

    def is_valid_url(self, url):
        """Vérifie si l'URL est pertinente"""
        for pattern in self.exclude_patterns:
            if pattern in url.lower():
                # Debug: voir ce qui est filtré
                if self.stats['links_filtered'] < 10:  # Log les 10 premiers seulement
                    print(f"   🚫 Filtré: {url[:60]}... (motif: {pattern})")
                return False
        return True

    def clean_title(self, title, h1, url):
        """Nettoie le titre"""
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
        """Scrape une page"""
        try:
            start_time = time.time()
            
            if self.use_selenium and self.driver:
                self.driver.get(url)
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(0.5)  # Réduit de 1s à 0.5s
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                response_time = time.time() - start_time
            else:
                resp = self.session.get(url, timeout=3)  # Réduit de 4s à 3s
                response_time = time.time() - start_time
                
                if resp.status_code != 200:
                    self.stats['errors'] += 1
                    return None
                
                soup = BeautifulSoup(resp.content, 'html.parser')
                html_content = str(soup)
            
            raw_title = soup.title.string.strip() if soup.title else ""
            h1 = soup.find('h1').get_text().strip() if soup.find('h1') else ""
            final_title = self.clean_title(raw_title, h1, url)
            
            meta_desc = ""
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag and meta_tag.get('content'):
                meta_desc = meta_tag['content'].strip()
            
            links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                
                if urlparse(full_url).netloc == self.domain and self.is_valid_url(full_url):
                    clean_link = full_url.split('#')[0].split('?')[0]
                    if clean_link != url:
                        links.append(clean_link)
                else:
                    self.stats['links_filtered'] += 1
            
            self.stats['links_discovered'] += len(links)
            
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
            self.stats['errors'] += 1
            return None

    def run_analysis(self, progress_callback=None, log_callback=None):
        """Lance l'analyse avec logs Streamlit"""
        self.log_callback = log_callback
        queue = [self.base_url]
        self.visited.add(self.base_url)
        crawled_count = 0
        
        print(f"\n{'='*80}")
        print(f"🚀 DÉBUT DU CRAWL: {self.max_urls} pages demandées")
        print(f"URL: {self.base_url}")
        print(f"{'='*80}\n")
        
        try:
            while queue and crawled_count < self.max_urls:
                current_url = queue.pop(0)
                
                # ✅ MISE À JOUR EN TEMPS RÉEL (chaque page)
                percent = min(crawled_count / self.max_urls, 0.99)
                
                if progress_callback:
                    progress_callback(
                        f"🔍 {crawled_count}/{self.max_urls} pages | Queue: {len(queue)} | Liens: {self.stats['links_discovered']}", 
                        percent
                    )
                
                # Log console tous les 10 crawls
                if crawled_count % 10 == 0:
                    print(f"📊 {crawled_count}/{self.max_urls} | Queue: {len(queue)} | Visitées: {len(self.visited)} | Liens: {self.stats['links_discovered']}")
                
                data = self.get_page_details(current_url)
                
                if data:
                    self.results.append(data)
                    crawled_count += 1
                    self.stats['pages_crawled'] += 1
                    
                    # Ajout des liens avec comptage détaillé
                    links_added = 0
                    for link in data['links']:
                        if link in self.visited:
                            self.stats['links_duplicate'] += 1
                        elif len(queue) >= 5000:
                            self.stats['queue_full_blocks'] += 1
                        else:
                            self.visited.add(link)
                            queue.append(link)
                            links_added += 1
                    
                    # Debug si problème de liens
                    if crawled_count % 50 == 0:
                        print(f"   → Page #{crawled_count}: {len(data['links'])} liens trouvés, {links_added} ajoutés")
                    
                    # DEBUG CRITIQUE: Si peu de liens découverts
                    if crawled_count == 5 and self.stats['links_discovered'] < 20:
                        print(f"\n⚠️ ALERTE: Seulement {self.stats['links_discovered']} liens découverts après 5 pages!")
                        print(f"   Exemples de liens sur la dernière page:")
                        for link in data['links'][:5]:
                            print(f"      • {link}")
                        print()
                else:
                    self.stats['pages_skipped'] += 1
                
                # Pause ultra-rapide
                time.sleep(0.005)  # 5ms seulement
        
        finally:
            if self.driver:
                self.driver.quit()
        
        # RAPPORT FINAL CONSOLE
        print(f"\n{'='*80}")
        print(f"✅ CRAWL TERMINÉ")
        print(f"{'='*80}")
        print(f"📈 RÉSULTATS:")
        print(f"   ├─ Pages crawlées: {self.stats['pages_crawled']} / {self.max_urls}")
        print(f"   ├─ Pages ignorées: {self.stats['pages_skipped']}")
        print(f"   ├─ URLs visitées: {len(self.visited)}")
        print(f"   ├─ Queue finale: {len(queue)} URLs restantes")
        print(f"   └─ Erreurs: {self.stats['errors']}")
        print(f"\n🔗 LIENS:")
        print(f"   ├─ Découverts: {self.stats['links_discovered']}")
        print(f"   ├─ Filtrés: {self.stats['links_filtered']}")
        print(f"   ├─ Doublons: {self.stats['links_duplicate']}")
        print(f"   └─ Blocages queue: {self.stats['queue_full_blocks']}")
        
        # Diagnostic si arrêt anticipé
        if crawled_count < self.max_urls:
            print(f"\n⚠️ ARRÊT ANTICIPÉ: {crawled_count}/{self.max_urls} pages")
            if len(queue) == 0:
                print(f"   Raison: QUEUE VIDE")
                print(f"   → Le site a moins de {self.max_urls} pages accessibles")
                print(f"   → Ou les filtres sont trop stricts (vérifier exclude_patterns)")
            else:
                print(f"   Raison: Condition while rompue (bug logique)")
        
        print(f"{'='*80}\n")
        
        patterns = self.analyze_patterns(self.results)
        
        if progress_callback:
            progress_callback(f"✅ Terminé: {self.stats['pages_crawled']} pages crawlées", 1.0)
        
        return self.results, {
            "total_urls": len(self.results), 
            "patterns": len(patterns),
            "stats": self.stats
        }

    def analyze_patterns(self, pages):
        """Analyse les patterns d'URL"""
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
