"""
SMART SCRAPER HYBRIDE (V6 - DEBUG MODE avec LOGS DÉTAILLÉS)
- Support des SPA React/Vue/Angular
- Limite 10 000 pages FONCTIONNELLE (fix queue bug)
- Auto-install ChromeDriver
- Filtres anti-bruit
- Capture HTML complète pour GEO
- LOGS DÉTAILLÉS pour debugging
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
        
        # Compteurs de debug
        self.stats = {
            'pages_crawled': 0,
            'pages_skipped': 0,
            'links_discovered': 0,
            'links_filtered': 0,
            'errors': 0
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        self.exclude_patterns = [
            'login', 'signin', 'signup', 'register', 'cart', 'checkout', 
            'account', 'admin', 'wp-', 'feed', '.pdf', '.jpg', '.png', 
            'tel:', 'mailto:', 'javascript:', '#'
        ]
        
        print(f"\n{'='*80}")
        print(f"🚀 INITIALISATION SMART SCRAPER")
        print(f"{'='*80}")
        print(f"URL cible: {self.base_url}")
        print(f"Domaine: {self.domain}")
        print(f"Limite demandée: {self.max_urls} pages")
        print(f"{'='*80}\n")
        
        # Détecter si le site est en React/SPA
        if self._is_spa_site():
            self.use_selenium = True
            self._init_selenium()

    def _is_spa_site(self):
        """Détecte si le site utilise un framework JS (React, Vue, Angular)"""
        print("🔍 Détection du type de site (SPA/React)...")
        try:
            resp = requests.get(self.base_url, headers=self.headers, timeout=5)
            html = resp.text.lower()
            
            # Patterns typiques des SPA
            spa_patterns = [
                'react', 'vue', 'angular', 'ng-app', 'data-reactroot',
                '<div id="root">', '<div id="app">', '__next'
            ]
            
            detected = any(pattern in html for pattern in spa_patterns)
            if detected:
                print("✅ Site SPA détecté (React/Vue/Angular) → Mode Selenium activé")
            else:
                print("ℹ️ Site statique détecté → Mode requests classique")
            return detected
        except Exception as e:
            print(f"⚠️ Erreur détection SPA: {e}")
            return False

    def _init_selenium(self):
        """Initialise Selenium pour les sites React avec auto-install ChromeDriver"""
        print("🔧 Initialisation de Selenium...")
        try:
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            # Auto-install ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Selenium initialisé avec succès")
        except Exception as e:
            print(f"⚠️ Impossible d'initialiser Selenium: {e}")
            print("→ Installation de webdriver-manager requise: pip install webdriver-manager")
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
                    self.stats['errors'] += 1
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
                else:
                    self.stats['links_filtered'] += 1
            
            self.stats['links_discovered'] += len(links)
            
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
            print(f"❌ Erreur scraping {url}: {e}")
            self.stats['errors'] += 1
            return None

    def run_analysis(self, progress_callback=None):
        queue = [self.base_url]
        self.visited.add(self.base_url)
        crawled_count = 0
        
        print(f"\n{'='*80}")
        print(f"🔄 DÉBUT DU CRAWL")
        print(f"{'='*80}")
        print(f"Objectif: {self.max_urls} pages")
        print(f"URL de départ: {self.base_url}")
        print(f"{'='*80}\n")
        
        try:
            while queue and crawled_count < self.max_urls:
                current_url = queue.pop(0)
                
                # Log tous les 10 crawls
                if crawled_count % 10 == 0:
                    percent = min(crawled_count / self.max_urls, 0.95)
                    print(f"\n📊 PROGRESSION: {crawled_count}/{self.max_urls} pages ({percent*100:.1f}%)")
                    print(f"   Queue actuelle: {len(queue)} URLs en attente")
                    print(f"   URLs visitées: {len(self.visited)}")
                    print(f"   Liens découverts: {self.stats['links_discovered']}")
                    print(f"   Liens filtrés: {self.stats['links_filtered']}")
                    print(f"   Erreurs: {self.stats['errors']}")
                    
                    if progress_callback:
                        progress_callback(f"Exploration ({crawled_count}/{self.max_urls}): {current_url.split('/')[-1][:30]}", percent)
                
                # Log de la page en cours
                print(f"   → Crawl: {current_url[:80]}...")
                
                data = self.get_page_details(current_url)
                
                if data:
                    self.results.append(data)
                    crawled_count += 1
                    self.stats['pages_crawled'] += 1
                    
                    links_added = 0
                    links_duplicate = 0
                    links_queue_full = 0
                    
                    # ✅ FIX CRITIQUE : Retrait de la limite artificielle "max_urls * 2"
                    # ✅ AJOUT : Limite la queue à 5000 URLs pour éviter l'explosion mémoire
                    for link in data['links']:
                        if link in self.visited:
                            links_duplicate += 1
                        elif len(queue) >= 5000:
                            links_queue_full += 1
                        else:
                            self.visited.add(link)
                            queue.append(link)
                            links_added += 1
                    
                    # Log détaillé des liens
                    if links_added > 0 or links_duplicate > 0:
                        print(f"      ✓ {len(data['links'])} liens trouvés → {links_added} ajoutés, {links_duplicate} doublons, {links_queue_full} queue pleine")
                else:
                    self.stats['pages_skipped'] += 1
                    print(f"      ⚠️ Page ignorée (erreur ou statut non-200)")
                
                # Pause adaptative selon le nombre de pages
                if self.max_urls > 1000:
                    time.sleep(0.01)  # Très rapide pour gros volumes
                else:
                    time.sleep(0.05)
            
            # LOG DE FIN
            print(f"\n{'='*80}")
            print(f"✅ CRAWL TERMINÉ")
            print(f"{'='*80}")
            print(f"Pages crawlées avec succès: {self.stats['pages_crawled']}")
            print(f"Pages ignorées (erreurs): {self.stats['pages_skipped']}")
            print(f"URLs totales visitées: {len(self.visited)}")
            print(f"Queue finale: {len(queue)} URLs restantes")
            print(f"Liens découverts: {self.stats['links_discovered']}")
            print(f"Liens filtrés: {self.stats['links_filtered']}")
            print(f"Erreurs totales: {self.stats['errors']}")
            
            # Diagnostic de limitation
            if crawled_count < self.max_urls:
                print(f"\n⚠️ ARRÊT ANTICIPÉ: {crawled_count}/{self.max_urls} pages")
                if len(queue) == 0:
                    print(f"   Raison: Plus d'URLs dans la queue (site trop petit ou trop de filtres)")
                else:
                    print(f"   Raison: Condition d'arrêt atteinte (vérifier la logique while)")
            
            print(f"{'='*80}\n")
        
        finally:
            # Fermer Selenium
            if self.driver:
                self.driver.quit()
                print("🔌 Selenium fermé")
        
        patterns = self.analyze_patterns(self.results)
        
        if progress_callback:
            progress_callback(f"Analyse terminée ✓ ({self.stats['pages_crawled']} pages)", 1.0)
        
        return self.results, {
            "total_urls": len(self.results), 
            "patterns": len(patterns),
            "stats": self.stats
        }

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
