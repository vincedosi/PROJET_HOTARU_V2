"""
SMART SCRAPER HYBRIDE (V11 - FIX LOG CALLBACK)
- Log callback passé dès __init__ pour capturer tous les logs
- Détection SPA agressive avec logs détaillés
- Extraction JSON-LD via JavaScript pour sites SPA
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse
import time
import re
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed


class SmartScraper:
    def __init__(self, start_urls, max_urls=500, use_selenium=False, log_callback=None):
        # Support ancien format (string unique) et nouveau (liste)
        if isinstance(start_urls, str):
            start_urls = [start_urls]

        self.domain = urlparse(start_urls[0]).netloc.lower()
        self.start_urls = [self.normalize_url(url) for url in start_urls]
        self.base_url = self.start_urls[0]
        self.max_urls = max_urls
        self.visited = set()
        self.results = []
        self.use_selenium = use_selenium
        self.driver = None
        self.log_callback = log_callback  # ← CRITIQUE : dès le début

        # Vérifier que toutes les URLs sont du même domaine
        for url in self.start_urls:
            if urlparse(url).netloc != self.domain:
                raise ValueError(
                    f"❌ Toutes les URLs doivent être du même domaine. Trouvé: {urlparse(url).netloc} au lieu de {self.domain}"
                )

        # Session requests
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        # Compteurs
        self.stats = {
            "pages_crawled": 0,
            "pages_skipped": 0,
            "links_discovered": 0,
            "links_filtered": 0,
            "links_duplicate": 0,
            "errors": 0,
            "queue_full_blocks": 0,
            "start_urls_count": len(self.start_urls),
        }

        self.filtered_log = []
        self.duplicate_log = []

        # Filtres
        self.exclude_patterns = [
            ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip",
            ".doc", ".docx", "tel:", "mailto:", "javascript:", "void(0)",
        ]

        self._log(f"🔗 Initialisation : {len(self.start_urls)} URL(s)")
        for i, url in enumerate(self.start_urls, 1):
            self._log(f"   {i}. {url}")

        # ========== DÉTECTION SPA AUTOMATIQUE ==========
        spa_detected = False
        
        if self.use_selenium:
            self._log("⚙️ Selenium FORCÉ par l'utilisateur")
        else:
            self._log("🔍 Détection SPA automatique...")
            try:
                spa_detected = self._is_spa_site()
                
                if spa_detected:
                    self._log("✅ Site SPA détecté → Activation Selenium")
                    self.use_selenium = True
                else:
                    self._log("✅ Site classique → Mode requests")
                    
            except Exception as e:
                self._log(f"⚠️ Erreur détection SPA : {e}")
                spa_detected = False

        # ========== INITIALISATION SELENIUM ==========
        if self.use_selenium:
            self._log("🚗 Démarrage Selenium...")
            self._init_selenium()
            
            if self.driver is None:
                self._log("❌ Selenium ÉCHEC → Fallback requests")
                self.use_selenium = False
            else:
                self._log("✅ Selenium OK (Chromium / Streamlit Cloud)")
        else:
            self._log("📄 Mode requests activé")

    def normalize_url(self, url):
        """Normalise une URL pour éviter les doublons."""
        url = url.split("#")[0].split("?")[0]
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        path = path.lower()
        normalized = urlunparse(
            (parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", "")
        )
        return normalized

    def _log(self, message):
        """Log visible dans Streamlit ET console."""
        print(message)
        if self.log_callback:
            self.log_callback(message)

    def _is_spa_site(self):
        """Détecte si le site utilise un framework JS."""
        try:
            self._log("   → Téléchargement HTML...")
            resp = self.session.get(self.start_urls[0], timeout=5)
            html = resp.text
            
            self._log(f"   → HTML reçu ({len(html)} chars)")
            
            soup = BeautifulSoup(html, "html.parser")
            
            # ========== DÉTECTION 1 : SCRIPTS TYPE=MODULE ==========
            module_scripts = soup.find_all("script", type="module")
            if module_scripts:
                self._log(f"   🎯 {len(module_scripts)} script(s) ES module → SPA")
                return True
            
            # ========== DÉTECTION 2 : SCRIPTS SRC ==========
            self._log("   → Analyse scripts src...")
            spa_patterns = ["_nuxt/", "__next/", "webpack", "vite", "/build/", ".module."]
            
            for script in soup.find_all("script", src=True):
                src = script.get("src", "").lower()
                for pattern in spa_patterns:
                    if pattern in src:
                        self._log(f"   🎯 Pattern '{pattern}' → SPA")
                        return True
            
            # ========== DÉTECTION 3 : LINK MODULEPRELOAD ==========
            self._log("   → Analyse modulepreload...")
            for link in soup.find_all("link"):
                rel = link.get("rel", [])
                if isinstance(rel, str):
                    rel = [rel]
                
                if "modulepreload" in rel:
                    self._log(f"   🎯 modulepreload → SPA")
                    return True
            
            # ========== DÉTECTION 4 : PATTERNS TEXTE ==========
            self._log("   → Patterns texte...")
            html_lower = html.lower()
            
            critical_patterns = {
                "_nuxt": "Nuxt",
                "__next": "Next.js",
                "data-reactroot": "React",
            }
            
            for pattern, framework in critical_patterns.items():
                if pattern in html_lower:
                    self._log(f"   🎯 '{pattern}' ({framework}) → SPA")
                    return True
            
            self._log("   ❌ Pas de SPA détecté")
            return False
            
        except Exception as e:
            self._log(f"   ⚠️ Erreur : {e}")
            return False

    def _init_selenium(self):
        """Initialise Selenium - Compatible Streamlit Cloud."""
        try:
            self._log("   → Configuration pour Streamlit Cloud...")

            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")

            # Recherche chromium installé via packages.txt
            import shutil

            chromium_paths = [
                shutil.which("chromium"),
                shutil.which("chromium-browser"),
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
            ]

            chromium_binary = None
            for path in chromium_paths:
                if path:
                    chromium_binary = path
                    self._log(f"   ✅ Chromium trouvé : {path}")
                    break

            if not chromium_binary:
                self._log("   ❌ Chromium NON trouvé - Vérifie packages.txt")
            else:
                chrome_options.binary_location = chromium_binary

            # Recherche chromedriver
            chromedriver_paths = [
                shutil.which("chromedriver"),
                "/usr/bin/chromedriver",
            ]

            chromedriver_binary = None
            for path in chromedriver_paths:
                if path:
                    chromedriver_binary = path
                    self._log(f"   ✅ ChromeDriver trouvé : {path}")
                    break

            if not chromedriver_binary:
                self._log("   ❌ ChromeDriver NON trouvé - Vérifie packages.txt")

            # Démarrage
            if chromedriver_binary:
                from selenium.webdriver.chrome.service import Service
                service = Service(chromedriver_binary)
                self._log("   → Démarrage Chromium avec service...")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self._log("   → Démarrage Chromium sans service...")
                self.driver = webdriver.Chrome(options=chrome_options)

            self._log("   ✅ Selenium OK !")
            return

        except Exception as e:
            self._log(f"   ❌ ÉCHEC : {str(e)[:300]}")
            self.use_selenium = False
            self.driver = None

    def is_valid_url(self, url):
        """Vérifie si l'URL est pertinente."""
        for pattern in self.exclude_patterns:
            if pattern in url.lower():
                self.filtered_log.append((url, pattern))
                return False
        return True

    def clean_title(self, title, h1, url):
        """Nettoie le titre."""
        domain_name = urlparse(url).netloc.split(".")[0].lower()

        def is_useful(text):
            if not text or len(text) < 3:
                return False
            text_clean = text.lower().replace(" ", "").replace("-", "")
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
            separators = [" - ", " | ", " : ", " — ", " – ", " · "]
            for sep in separators:
                if sep in text:
                    parts = [p.strip() for p in text.split(sep)]
                    useful_parts = [p for p in parts if is_useful(p)]
                    if useful_parts:
                        text = max(useful_parts, key=len)
                    break

        if not is_useful(text):
            path = urlparse(url).path
            segments = [
                s for s in path.split("/") if s and s not in ["fr", "en", "de", "es", "www"]
            ]
            if segments:
                text = segments[-1].replace("-", " ").replace("_", " ").title()
            else:
                return "Accueil"

        text = text.strip()
        return text[:40] + ".." if len(text) > 40 else text

    def get_page_details(self, url):
        """Scrape une page."""
        try:
            start_time = time.time()
            json_ld_from_js = []

            # ========== MODE SELENIUM ==========
            if self.use_selenium and self.driver:
                try:
                    self._log(f"🔍 [Selenium] {url}")
                    self.driver.get(url)

                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    self._log("   ⏳ Attente JSON-LD...")
                    try:
                        WebDriverWait(self.driver, 10).until(
                            lambda d: d.execute_script(
                                'return document.querySelectorAll(\'script[type*="ld+json" i]\').length > 0'
                            )
                        )
                        self._log("   ✅ JSON-LD dans DOM")
                    except Exception:
                        self._log("   ⚠️ Timeout JSON-LD")
                    
                    time.sleep(2)

                    # Cookies
                    try:
                        self.driver.execute_script(
                            """
                            const buttons = document.querySelectorAll('button, a, div[role="button"]');
                            buttons.forEach(btn => {
                                const text = (btn.innerText || '').toLowerCase();
                                if (text.includes('accepter') || text.includes('accept all')) {
                                    btn.click();
                                }
                            });
                            """
                        )
                        time.sleep(1)
                    except Exception:
                        pass

                    # Scroll
                    try:
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                        self.driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(1)
                    except Exception:
                        pass

                    # EXTRACTION JSON-LD
                    try:
                        self._log("   🔍 Extraction JSON-LD...")
                        
                        script_count = self.driver.execute_script(
                            'return document.querySelectorAll(\'script[type*="ld+json" i]\').length'
                        )
                        self._log(f"   📊 {script_count} script(s) JSON-LD")
                        
                        json_ld_from_js = self.driver.execute_script(
                            """
                            const scripts = document.querySelectorAll('script[type*="ld+json" i]');
                            return Array.from(scripts).map((s, idx) => {
                                try {
                                    const content = s.textContent || s.innerText || '';
                                    if (!content.trim()) return null;
                                    return JSON.parse(content);
                                } catch (err) {
                                    console.error('Script', idx, 'erreur:', err.message);
                                    return null;
                                }
                            }).filter(x => x !== null);
                            """
                        )
                        
                        if json_ld_from_js:
                            self._log(f"   ✅ {len(json_ld_from_js)} bloc(s) extrait(s)")
                            for i, block in enumerate(json_ld_from_js):
                                block_type = block.get('@type', 'Unknown') if isinstance(block, dict) else f'Array[{len(block)}]'
                                self._log(f"      • Bloc {i+1}: {block_type}")
                        else:
                            self._log("   ❌ Aucun bloc extrait")
                            
                    except Exception as e:
                        self._log(f"   ⚠️ Erreur extraction : {e}")
                        json_ld_from_js = []

                    js_links = self.driver.execute_script(
                        "return Array.from(document.querySelectorAll('a[href]')).map(a => a.href);"
                    )

                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, "html.parser")
                    response_time = time.time() - start_time
                    raw_links = js_links or []

                except Exception as se:
                    self._log(f"⚠️ Erreur Selenium : {se}")
                    raise

            # ========== MODE REQUESTS ==========
            else:
                self._log(f"📄 [Requests] {url}")
                resp = self.session.get(url, timeout=5)
                response_time = time.time() - start_time
                
                if resp.status_code != 200:
                    self._log(f"   ❌ HTTP {resp.status_code}")
                    self.stats["errors"] += 1
                    return None
                    
                soup = BeautifulSoup(resp.content, "html.parser")
                html_content = str(soup)
                raw_links = [a["href"] for a in soup.find_all("a", href=True)]
                self._log(f"   ✅ {len(html_content)} chars")

            # ========== EXTRACTION DONNÉES ==========
            raw_title = soup.title.string.strip() if soup.title else ""
            h1 = soup.find("h1").get_text().strip() if soup.find("h1") else ""
            final_title = self.clean_title(raw_title, h1, url)

            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and meta_tag.get("content"):
                meta_desc = meta_tag["content"].strip()

            # Liens
            links = []
            normalized_current = self.normalize_url(url)

            for href in raw_links:
                if not href:
                    continue
                full_url = urljoin(url, href)
                if (
                    urlparse(full_url).netloc.lower() == self.domain.lower()
                    and self.is_valid_url(full_url)
                ):
                    clean_link = self.normalize_url(full_url)
                    if clean_link != normalized_current:
                        links.append(clean_link)
                else:
                    self.stats["links_filtered"] += 1

            unique_links = list(set(links))
            self.stats["links_discovered"] += len(unique_links)

            # JSON-LD
            if self.use_selenium and json_ld_from_js:
                json_ld_data = json_ld_from_js
            else:
                json_ld_data = []
                for script in soup.find_all("script"):
                    t = (script.get("type") or "").lower()
                    if "ld+json" not in t:
                        continue
                    try:
                        raw = script.string or script.get_text(strip=True) or ""
                        raw = raw.strip()
                        if not raw:
                            continue
                        parsed = json.loads(raw)
                        json_ld_data.append(parsed)
                    except (json.JSONDecodeError, TypeError):
                        continue

            has_structured_data = bool(json_ld_data)
            h2_count = len(soup.find_all("h2"))
            lists_count = len(soup.find_all(["ul", "ol"]))

            return {
                "url": url,
                "title": final_title,
                "links": unique_links,
                "description": meta_desc,
                "h1": h1,
                "response_time": response_time,
                "html_content": html_content,
                "last_modified": "",
                "has_structured_data": has_structured_data,
                "json_ld": json_ld_data,
                "h2_count": h2_count,
                "lists_count": lists_count,
            }

        except Exception as e:
            self.stats["errors"] += 1
            self._log(f"⚠️ Erreur critique : {e}")
            return None

    def run_analysis(self, progress_callback=None, log_callback=None):
        """Lance l'analyse."""
        if log_callback:
            self.log_callback = log_callback

        queue = list(self.start_urls)
        self.visited.update(self.start_urls)
        crawled_count = 0

        print(f"\n{'='*80}")
        print(f"🚀 CRAWL: {self.max_urls} pages")
        print(f"{'='*80}\n")

        try:
            while queue and crawled_count < self.max_urls:
                current_url = queue.pop(0)
                percent = min(crawled_count / self.max_urls, 0.99)

                if progress_callback:
                    progress_callback(
                        f"🔍 {crawled_count}/{self.max_urls} | Queue: {len(queue)}",
                        percent,
                    )

                data = self.get_page_details(current_url)

                if data:
                    self.results.append(data)
                    crawled_count += 1
                    self.stats["pages_crawled"] += 1

                    for link in data["links"]:
                        if link in self.visited:
                            self.stats["links_duplicate"] += 1
                        elif len(queue) < 5000:
                            self.visited.add(link)
                            queue.append(link)
                else:
                    self.stats["pages_skipped"] += 1

                time.sleep(0.005)

        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self._log("🚗 Driver fermé")
                except Exception:
                    pass

        print(f"\n✅ TERMINÉ: {self.stats['pages_crawled']} pages\n")

        patterns = self.analyze_patterns(self.results)

        if progress_callback:
            progress_callback(f"✅ Terminé: {self.stats['pages_crawled']}", 1.0)

        return self.results, {
            "total_urls": len(self.results),
            "patterns": len(patterns),
            "stats": self.stats,
            "filtered_log": self.filtered_log,
            "duplicate_log": self.duplicate_log,
        }

    def analyze_patterns(self, pages):
        """Analyse les patterns d'URL."""
        groups = {}
        for p in pages:
            path = urlparse(p["url"]).path
            segments = [s for s in path.split("/") if s]

            if len(segments) > 0:
                group_key = segments[0]
                if group_key in ["fr", "en", "de", "es"] and len(segments) > 1:
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


def fetch_page(url: str, timeout: int = 15) -> str:
    """Récupère le HTML d'une seule page."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text