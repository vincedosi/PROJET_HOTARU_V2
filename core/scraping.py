"""
SMART SCRAPER UNIVERSEL (core/scraping.py)
- Sites normaux : requests rapide.
- Sites protégés (ex. BMW) : use_selenium=True ou cascade timeout (requests → requests-html → Selenium non-headless).
- Proxy optionnel (requests + Selenium).
- JSON-LD : extraction double (soup + DOM Selenium) fusionnée sans doublons.
- Utilisé par audit, GEO, et tous les modules.
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
    def __init__(self, start_urls, max_urls=500, use_selenium=False, selenium_mode=None, log_callback=None, proxy=None):
        """
        Args:
            selenium_mode: "light" pour eager loading + wait JSON-LD, None sinon
            proxy: "http://ip:port" ou "http://user:pass@ip:port" pour requests et Selenium
        """
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
        self.selenium_mode = selenium_mode
        self.driver = None
        self.log_callback = log_callback
        self.proxy = proxy

        # Vérifier que toutes les URLs sont du même domaine
        for url in self.start_urls:
            if urlparse(url).netloc != self.domain:
                raise ValueError(
                    f"Toutes les URLs doivent être du même domaine. Trouvé: {urlparse(url).netloc} au lieu de {self.domain}"
                )

        # Session requests (headers simplifiés)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9",
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
            "protected_sites_detected": 0,
            "advanced_solutions_used": 0,
            "requests_html_successes": 0,
            "selenium_nonheadless_successes": 0,
            "proxy_used": self.proxy or "Aucun",
        }

        self.filtered_log = []
        self.duplicate_log = []

        # Filtres
        self.exclude_patterns = [
            ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip",
            ".doc", ".docx", "tel:", "mailto:", "javascript:", "void(0)",
        ]

        self._log(f"Initialisation : {len(self.start_urls)} URL(s)")
        for i, url in enumerate(self.start_urls, 1):
            self._log(f"   {i}. {url}")
        self._log(f"Proxy : {self.proxy if self.proxy else 'Aucun'}")

        if use_selenium:
            self._log("Mode Selenium activé")
            self.use_selenium = True
        else:
            self._log("Mode requests activé")
            self.use_selenium = False

        if self.use_selenium:
            self._init_selenium()
            if self.driver is None:
                self._log("Selenium échoué → Fallback requests")
                self.use_selenium = False

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

            if getattr(self, "selenium_mode", None) == "light":
                chrome_options.page_load_strategy = "eager"
                self._log("    Mode Selenium Light activé (eager loading)")

            if getattr(self, "proxy", None):
                self._log(f"   Proxy Selenium : {self.proxy}")
                chrome_options.add_argument(f"--proxy-server={self.proxy}")

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
                    self._log(f"   Chromium trouvé : {path}")
                    break

            if not chromium_binary:
                self._log("    Chromium NON trouvé - Vérifie packages.txt")
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
                    self._log(f"   ChromeDriver trouvé : {path}")
                    break

            if not chromedriver_binary:
                self._log("    ChromeDriver NON trouvé - Vérifie packages.txt")

            # Démarrage
            if chromedriver_binary:
                from selenium.webdriver.chrome.service import Service
                service = Service(chromedriver_binary)
                self._log("   → Démarrage Chromium avec service...")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self._log("   → Démarrage Chromium sans service...")
                self.driver = webdriver.Chrome(options=chrome_options)

            self._log("   Selenium OK !")
            return

        except Exception as e:
            self._log(f"    ÉCHEC : {str(e)[:300]}")
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

    def _extract_jsonld_from_soup(self, soup):
        """Extraction JSON-LD classique depuis les balises <script type=\"application/ld+json\"> du HTML."""
        out = []
        for script in soup.find_all("script"):
            t = (script.get("type") or "").lower()
            if "ld+json" not in t:
                continue
            try:
                raw = script.string or script.get_text(strip=True) or ""
                if not raw.strip():
                    continue
                out.append(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                continue
        return out

    def _merge_jsonld_no_duplicates(self, list_a, list_b=None):
        """Fusionne deux listes de blocs JSON-LD et supprime les doublons (comparaison canonique)."""
        list_b = list_b or []
        seen = set()
        merged = []
        for block in list_a + list_b:
            if block is None:
                continue
            try:
                canonical = json.dumps(block, sort_keys=True)
                if canonical in seen:
                    continue
                seen.add(canonical)
                merged.append(block)
            except (TypeError, ValueError):
                continue
        return merged

    def _build_page_result(self, url, soup, html_content, response_time, raw_links=None, json_ld_data=None):
        """Construit le dict de résultat standard à partir de HTML/soup."""
        if raw_links is None:
            raw_links = [a["href"] for a in soup.find_all("a", href=True)]
        if json_ld_data is None:
            json_ld_data = self._extract_jsonld_from_soup(soup)

        raw_title = soup.title.string.strip() if soup.title else ""
        h1 = soup.find("h1").get_text().strip() if soup.find("h1") else ""
        final_title = self.clean_title(raw_title, h1, url)
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        normalized_current = self.normalize_url(url)
        links = []
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

        return {
            "url": url,
            "title": final_title,
            "links": unique_links,
            "description": meta_desc,
            "h1": h1,
            "response_time": response_time,
            "html_content": html_content,
            "last_modified": "",
            "has_structured_data": bool(json_ld_data),
            "json_ld": json_ld_data,
            "h2_count": len(soup.find_all("h2")),
            "lists_count": len(soup.find_all(["ul", "ol"])),
        }

    def _get_with_requests(self, url):
        """Méthode A : requests classique. Retourne le dict résultat ou lève Timeout/RequestException."""
        start_time = time.time()
        self._log(f" [Requests] {url}")
        request_proxies = {}
        if self.proxy:
            request_proxies = {"http": self.proxy, "https": self.proxy}
            self._log(f"   Proxy : {self.proxy}")
        resp = self.session.get(url, timeout=15, proxies=request_proxies)
        response_time = time.time() - start_time
        if resp.status_code != 200:
            self._log(f"   HTTP {resp.status_code}")
            self.stats["errors"] += 1
            raise requests.exceptions.HTTPError(f"HTTP {resp.status_code}")
        soup = BeautifulSoup(resp.content, "html.parser")
        html_content = str(soup)
        raw_links = [a["href"] for a in soup.find_all("a", href=True)]
        self._log(f"   {len(html_content)} chars")
        return self._build_page_result(url, soup, html_content, response_time, raw_links=raw_links)

    def _get_with_requests_html(self, url):
        """
        Méthode B : requests-html (JavaScript rendu).
        Idéal pour CloudFlare et sites protégés.
        Retourne dict avec html_content, soup, raw_links, response_time pour _build_page_result.
        """
        try:
            from requests_html import HTMLSession
        except ImportError:
            raise RuntimeError("requests-html non installé. pip install requests-html")

        start_time = time.time()
        session = HTMLSession()
        resp = session.get(url, timeout=15)
        resp.html.render()
        response_time = time.time() - start_time
        html = resp.html.html
        soup = BeautifulSoup(html, "html.parser")
        raw_links = [a.get("href", "") for a in soup.find_all("a", href=True)]
        return {
            "html_content": html,
            "soup": soup,
            "raw_links": raw_links,
            "response_time": response_time,
        }

    def _get_with_selenium_nonheadless(self, url):
        """
        Méthode C : Selenium en mode graphique (pas headless).
        Dernier recours avant abandon.
        """
        start_time = time.time()
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.set_page_load_timeout(60)
            driver.get(url)
            time.sleep(10)
            html = driver.page_source
            response_time = time.time() - start_time
            soup = BeautifulSoup(html, "html.parser")
            raw_links = [a.get("href", "") for a in soup.find_all("a", href=True)]
            return {
                "html_content": html,
                "soup": soup,
                "raw_links": raw_links,
                "response_time": response_time,
            }
        finally:
            driver.quit()

    def _is_timeout_error(self, e):
        """Détecte si l'exception est un timeout (Read timed out, ConnectTimeout, etc.)."""
        msg = str(e).lower()
        if "read timed out" in msg or "readtimeout" in msg or "connecttimeout" in msg or "timed out" in msg:
            return True
        return isinstance(e, (requests.exceptions.Timeout, TimeoutError))

    def get_page_details(self, url):
        """Scrape une page. Cascade automatique vers solutions avancées si timeout (sites protégés type BMW)."""
        try:
            start_time = time.time()
            json_ld_from_js = []

            # ========== MODE SELENIUM (déjà initialisé au démarrage) ==========
            if self.use_selenium and self.driver:
                try:
                    self._log(f" [Selenium] {url}")
                    self.driver.get(url)

                    if getattr(self, "selenium_mode", None) == "light":
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((
                                    By.XPATH,
                                    "//script[@type='application/ld+json']",
                                ))
                            )
                            elapsed = time.time() - start_time
                            self._log(f"   JSON-LD injecté après {elapsed:.2f}s")
                        except Exception:
                            elapsed = time.time() - start_time
                            self._log(f"    JSON-LD non détecté après {elapsed:.2f}s")
                    else:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        self._log("   Attente JSON-LD...")
                        try:
                            WebDriverWait(self.driver, 10).until(
                                lambda d: d.execute_script(
                                    'return document.querySelectorAll(\'script[type*="ld+json" i]\').length > 0'
                                )
                            )
                            self._log("   JSON-LD dans DOM")
                        except Exception:
                            self._log("    Timeout JSON-LD")
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
                        self._log("    Extraction JSON-LD...")
                        
                        script_count = self.driver.execute_script(
                            'return document.querySelectorAll(\'script[type*="ld+json" i]\').length'
                        )
                        self._log(f"    {script_count} script(s) JSON-LD")
                        
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
                            self._log(f"   {len(json_ld_from_js)} bloc(s) extrait(s)")
                            for i, block in enumerate(json_ld_from_js):
                                block_type = block.get('@type', 'Unknown') if isinstance(block, dict) else f'Array[{len(block)}]'
                                self._log(f"      • Bloc {i+1}: {block_type}")
                        else:
                            self._log("    Aucun bloc extrait")
                            
                    except Exception as e:
                        self._log(f"    Erreur extraction : {e}")
                        json_ld_from_js = []

                    js_links = self.driver.execute_script(
                        "return Array.from(document.querySelectorAll('a[href]')).map(a => a.href);"
                    )

                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, "html.parser")
                    response_time = time.time() - start_time
                    raw_links = js_links or []

                except Exception as se:
                    self._log(f"Erreur Selenium : {se}")
                    raise

            # ========== MODE REQUESTS (priorité) ou CASCADE si timeout ==========
            else:
                # ESSAI 1 : requests normal
                try:
                    return self._get_with_requests(url)
                except Exception as e1:
                    if not self._is_timeout_error(e1):
                        self.stats["errors"] += 1
                        self._log(f"Erreur requests : {e1}")
                        return None
                    self.stats["protected_sites_detected"] += 1
                    self.stats["advanced_solutions_used"] += 1
                    self._log("Site protégé détecté (timeout) → Basculement solution avancée")
                    self._log(f"Timeout détecté : {e1}")
                    self._log("Basculement vers solution avancée...")

                # ESSAI 2 : requests-html (JavaScript rendu)
                try:
                    raw = self._get_with_requests_html(url)
                    self.stats["requests_html_successes"] += 1
                    self._log("requests-html fonctionne")
                    return self._build_page_result(
                        url,
                        raw["soup"],
                        raw["html_content"],
                        raw["response_time"],
                        raw_links=raw["raw_links"],
                    )
                except Exception as e2:
                    self._log(f"requests-html échoué : {e2}")
                    self._log("Essai suivant...")

                # ESSAI 3 : Selenium non-headless
                try:
                    raw = self._get_with_selenium_nonheadless(url)
                    self.stats["selenium_nonheadless_successes"] += 1
                    self._log("Selenium non-headless fonctionne")
                    return self._build_page_result(
                        url,
                        raw["soup"],
                        raw["html_content"],
                        raw["response_time"],
                        raw_links=raw["raw_links"],
                    )
                except Exception as e3:
                    self._log(f"Selenium non-headless échoué : {e3}")

                # ESSAI 4 : Abandon
                self._log(f"Impossible d'accéder à {url}")
                self.stats["errors"] += 1
                return None

            # ========== EXTRACTION DONNÉES (après bloc Selenium) ==========
            raw_title = soup.title.string.strip() if soup.title else ""
            h1 = soup.find("h1").get_text().strip() if soup.find("h1") else ""
            final_title = self.clean_title(raw_title, h1, url)

            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and meta_tag.get("content"):
                meta_desc = meta_tag["content"].strip()

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

            # Fusion des deux méthodes d'extraction JSON-LD (soup + Selenium DOM si utilisé)
            json_ld_classic = self._extract_jsonld_from_soup(soup)
            json_ld_data = self._merge_jsonld_no_duplicates(json_ld_classic, json_ld_from_js)

            return {
                "url": url,
                "title": final_title,
                "links": unique_links,
                "description": meta_desc,
                "h1": h1,
                "response_time": response_time,
                "html_content": html_content,
                "last_modified": "",
                "has_structured_data": bool(json_ld_data),
                "json_ld": json_ld_data,
                "h2_count": len(soup.find_all("h2")),
                "lists_count": len(soup.find_all(["ul", "ol"])),
            }

        except Exception as e:
            self.stats["errors"] += 1
            self._log(f"Erreur critique : {e}")
            return None

    def run_analysis(self, progress_callback=None, log_callback=None):
        """Lance l'analyse."""
        if log_callback:
            self.log_callback = log_callback

        queue = list(self.start_urls)
        self.visited.update(self.start_urls)
        crawled_count = 0

        print(f"\n{'='*80}")
        print(f"CRAWL: {self.max_urls} pages")
        print(f"{'='*80}\n")

        try:
            while queue and crawled_count < self.max_urls:
                current_url = queue.pop(0)
                percent = min(crawled_count / self.max_urls, 0.99)

                if progress_callback:
                    progress_callback(
                        f"{crawled_count}/{self.max_urls} | Queue: {len(queue)}",
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

        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self._log("Driver fermé")
                except Exception:
                    pass

        print(f"\nTERMINÉ: {self.stats['pages_crawled']} pages\n")

        patterns = self.analyze_patterns(self.results)

        if progress_callback:
            progress_callback(f"Terminé: {self.stats['pages_crawled']}", 1.0)

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