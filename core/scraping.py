"""
SMART SCRAPER HYBRIDE (V8 - FIX JSON-LD SPA/REACT)
- Extraction JSON-LD via JavaScript pour sites SPA (React, Vue, Nuxt, Next.js)
- Logs visibles dans l'interface Streamlit
- Compteur de pages en temps réel
- Optimisation vitesse (threading + requests session)
- Support React/SPA
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
    def __init__(self, start_urls, max_urls=500, use_selenium=False):
        # Support ancien format (string unique) et nouveau (liste)
        if isinstance(start_urls, str):
            start_urls = [start_urls]

        self.domain = urlparse(start_urls[0]).netloc.lower()
        self.start_urls = [self.normalize_url(url) for url in start_urls]
        self.base_url = self.start_urls[0]  # Pour compatibilité
        self.max_urls = max_urls
        self.visited = set()
        self.results = []
        # Préférence utilisateur pour Selenium (peut être activé aussi automatiquement)
        self.use_selenium = use_selenium
        self.driver = None
        self.log_callback = None

        # Vérifier que toutes les URLs sont du même domaine
        for url in self.start_urls:
            if urlparse(url).netloc != self.domain:
                raise ValueError(
                    f"❌ Toutes les URLs doivent être du même domaine. Trouvé: {urlparse(url).netloc} au lieu de {self.domain}"
                )

        # Session requests pour réutiliser la connexion (+ rapide)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # Compteurs de debug
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

        # Journaux détaillés (URLs réelles, pas juste les compteurs)
        self.filtered_log = []  # [(url, motif)]
        self.duplicate_log = []  # [url]

        # Filtres anti-bruit réduits (seulement les vrais parasites)
        self.exclude_patterns = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".zip",
            ".doc",
            ".docx",
            "tel:",
            "mailto:",
            "javascript:",
            "void(0)",
        ]

        print(f"🔗 Mode multi-URLs activé: {len(self.start_urls)} point(s) d'entrée")
        for i, url in enumerate(self.start_urls, 1):
            print(f"   {i}. {url}")

        # Détection React/SPA + override par préférence utilisateur
        # Nouvelle logique : si use_selenium == True OU si _is_spa_site() == True → on active Selenium.
        spa_detected = False
        try:
            spa_detected = self._is_spa_site()
            if spa_detected:
                print("🔍 Site SPA/React détecté automatiquement")
        except Exception as e:
            print(f"⚠️ Erreur détection SPA: {e}")
            spa_detected = False

        if self.use_selenium or spa_detected:
            self.use_selenium = True
            self._init_selenium()

    def normalize_url(self, url):
        """Normalise une URL pour éviter les doublons (trailing slash, fragments, query params, casse)"""
        # Supprimer les fragments (#) et les paramètres de requête (?)
        url = url.split("#")[0].split("?")[0]
        # Supprimer le trailing slash (sauf pour la racine du domaine)
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        # Normaliser la casse du chemin
        path = path.lower()
        # Reconstruire l'URL normalisée
        normalized = urlunparse(
            (parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", "")
        )
        return normalized

    def _log(self, message):
        """Log visible dans Streamlit"""
        print(message)  # Toujours afficher en console
        if self.log_callback:
            self.log_callback(message)

    def _is_spa_site(self):
        """Détecte si le site utilise un framework JS"""
        try:
            resp = self.session.get(self.start_urls[0], timeout=5)
            html = resp.text.lower()
            spa_patterns = [
                "react",
                "vue",
                "angular",
                "ng-app",
                "data-reactroot",
                '<div id="root">',
                '<div id="app">',
                "__next",
                "nuxt",
                "_nuxt",
            ]
            detected = any(pattern in html for pattern in spa_patterns)
            return detected
        except Exception:
            return False

    def _init_selenium(self):
        """Initialise Selenium (avec undetected_chromedriver si disponible)."""
        try:
            # Tentative avec undetected_chromedriver (meilleure furtivité pour sites protégés)
            try:
                import undetected_chromedriver as uc  # type: ignore

                chrome_options = uc.ChromeOptions()
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument(
                    f'user-agent={self.session.headers.get("User-Agent", "Mozilla/5.0")}'
                )

                self.driver = uc.Chrome(options=chrome_options)
                self._log("✅ Mode Selenium (undetected_chromedriver) activé")
                return
            except Exception as e_uc:
                self._log(
                    f"⚠️ undetected_chromedriver indisponible ({e_uc}), fallback Selenium standard..."
                )

            # Fallback : Selenium classique + webdriver-manager
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument(
                f'user-agent={self.session.headers.get("User-Agent", "Mozilla/5.0")}'
            )

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self._log("✅ Mode Selenium standard activé")
        except Exception as e:
            self._log(f"⚠️ Selenium non disponible: {e}")
            self.use_selenium = False
            self.driver = None

    def is_valid_url(self, url):
        """Vérifie si l'URL est pertinente"""
        for pattern in self.exclude_patterns:
            if pattern in url.lower():
                self.filtered_log.append((url, pattern))
                return False
        return True

    def clean_title(self, title, h1, url):
        """Nettoie le titre"""
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
        """Scrape une page avec gestion avancée (Cookies + JS Links + JSON-LD dynamique pour sites SPA)"""
        try:
            start_time = time.time()
            json_ld_from_js = []  # Initialisation pour éviter les erreurs

            # --- MODE SELENIUM (Complexe) ---
            if self.use_selenium and self.driver:
                try:
                    self.driver.get(url)

                    # 1. Attendre le chargement du body
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    time.sleep(2)  # Stabilisation

                    # 2. TENTATIVE DE GESTION COOKIES (Boutons 'Accepter')
                    try:
                        self.driver.execute_script(
                            """
                            const buttons = document.querySelectorAll('button, a, div[role="button"]');
                            buttons.forEach(btn => {
                                if (btn.innerText.toLowerCase().includes('accepter') || btn.innerText.toLowerCase().includes('accept all')) {
                                    btn.click();
                                }
                            });
                            """
                        )
                        time.sleep(1)
                    except Exception:
                        pass

                    # 3. SCROLL OFFENSIF (Force le chargement du footer/liens cachés)
                    try:
                        self.driver.execute_script(
                            "window.scrollTo(0, document.body.scrollHeight);"
                        )
                        time.sleep(2)
                        self.driver.execute_script("window.scrollTo(0, 0);")
                    except Exception:
                        pass

                    # 4. EXTRACTION JSON-LD VIA JAVASCRIPT (CRUCIAL POUR LES SPA)
                    # Capture les scripts injectés dynamiquement par React/Vue/Nuxt
                    try:
                        json_ld_from_js = self.driver.execute_script(
                            """
                            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                            return Array.from(scripts).map(s => {
                                try { 
                                    return JSON.parse(s.textContent); 
                                } catch { 
                                    return null; 
                                }
                            }).filter(x => x);
                            """
                        )
                        if json_ld_from_js:
                            self._log(f"   ✅ JSON-LD extrait via JS: {len(json_ld_from_js)} bloc(s)")
                    except Exception as e:
                        self._log(f"   ⚠️ Erreur extraction JSON-LD JS: {e}")
                        json_ld_from_js = []

                    # 5. EXTRACTION LIENS VIA JAVASCRIPT (liens générés par le navigateur)
                    js_links = self.driver.execute_script(
                        """
                        return Array.from(document.querySelectorAll('a[href]')).map(a => a.href);
                        """
                    )

                    # On récupère aussi le HTML pour le texte
                    html_content = self.driver.page_source
                    soup = BeautifulSoup(html_content, "html.parser")
                    response_time = time.time() - start_time

                    # On utilise les liens JS prioritaires
                    raw_links = js_links or []

                except Exception as se:
                    self._log(f"⚠️ Erreur Selenium sur {url}: {se}")
                    # On laisse remonter pour que le bloc except global gère l'erreur proprement
                    raise

            # --- MODE REQUESTS (Simple) ---
            else:
                resp = self.session.get(url, timeout=5)
                response_time = time.time() - start_time
                if resp.status_code != 200:
                    self.stats["errors"] += 1
                    return None
                soup = BeautifulSoup(resp.content, "html.parser")
                html_content = str(soup)
                raw_links = [a["href"] for a in soup.find_all("a", href=True)]

            # --- NETTOYAGE ET STRUCTURATION DES DONNÉES ---

            raw_title = soup.title.string.strip() if soup.title else ""
            h1 = soup.find("h1").get_text().strip() if soup.find("h1") else ""
            final_title = self.clean_title(raw_title, h1, url)

            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag and meta_tag.get("content"):
                meta_desc = meta_tag["content"].strip()

            # Traitement des liens
            links = []
            normalized_current = self.normalize_url(url)

            for href in raw_links:
                if not href:
                    continue

                # Reconstitution URL complète
                full_url = urljoin(url, href)

                # Filtrage Domaine + Validité
                if (
                    urlparse(full_url).netloc.lower() == self.domain.lower()
                    and self.is_valid_url(full_url)
                ):
                    clean_link = self.normalize_url(full_url)
                    if clean_link != normalized_current:
                        links.append(clean_link)
                else:
                    self.stats["links_filtered"] += 1

            # Dédoublonnage final
            unique_links = list(set(links))
            self.stats["links_discovered"] += len(unique_links)

            # --- EXTRACTION JSON-LD ---
            # Priorité 1: Données extraites via JavaScript (pour les SPA)
            # Priorité 2: Parsing BeautifulSoup classique (pour sites statiques)
            if self.use_selenium and json_ld_from_js:
                json_ld_data = json_ld_from_js
            else:
                # Fallback: extraction via BeautifulSoup
                json_ld_data = []
                for script in soup.find_all("script"):
                    t = (script.get("type") or "").lower()
                    # Certains sites utilisent des variantes: "application/ld+json; charset=utf-8"
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
            self._log(f"⚠️ Erreur critique scraping {url}: {e}")
            return None

    def run_analysis(self, progress_callback=None, log_callback=None):
        """Lance l'analyse avec logs Streamlit"""
        self.log_callback = log_callback

        # ✅ CRAWL MULTI-URLs : Commence avec toutes les URLs de départ (normalisées)
        queue = list(self.start_urls)
        self.visited.update(self.start_urls)  # start_urls déjà normalisées dans __init__
        crawled_count = 0

        print(f"\n{'='*80}")
        print(f"🚀 DÉBUT DU CRAWL MULTI-URLs: {self.max_urls} pages demandées")
        print(f"Domaine: {self.domain}")
        print(f"Points d'entrée: {len(self.start_urls)}")
        for i, url in enumerate(self.start_urls, 1):
            print(f"   {i}. {url}")
        print(f"{'='*80}\n")

        try:
            while queue and crawled_count < self.max_urls:
                current_url = queue.pop(0)

                # ✅ MISE À JOUR EN TEMPS RÉEL (chaque page)
                percent = min(crawled_count / self.max_urls, 0.99)

                if progress_callback:
                    progress_callback(
                        f"🔍 {crawled_count}/{self.max_urls} pages | Queue: {len(queue)} | Liens: {self.stats['links_discovered']}",
                        percent,
                    )

                # Log console tous les 10 crawls
                if crawled_count % 10 == 0:
                    print(
                        f"📊 {crawled_count}/{self.max_urls} | Queue: {len(queue)} | Visitées: {len(self.visited)} | Liens: {self.stats['links_discovered']}"
                    )

                data = self.get_page_details(current_url)

                if data:
                    self.results.append(data)
                    crawled_count += 1
                    self.stats["pages_crawled"] += 1

                    # Ajout des liens avec comptage détaillé
                    links_added = 0
                    for link in data["links"]:
                        if link in self.visited:
                            self.stats["links_duplicate"] += 1
                            self.duplicate_log.append(link)
                        elif len(queue) >= 5000:
                            self.stats["queue_full_blocks"] += 1
                        else:
                            self.visited.add(link)
                            queue.append(link)
                            links_added += 1

                    # Debug si problème de liens
                    if crawled_count % 50 == 0:
                        print(
                            f"   → Page #{crawled_count}: {len(data['links'])} liens trouvés, {links_added} ajoutés"
                        )

                    # DEBUG CRITIQUE: Si peu de liens découverts
                    if crawled_count == 5 and self.stats["links_discovered"] < 20:
                        print(
                            f"\n⚠️ ALERTE: Seulement {self.stats['links_discovered']} liens découverts après 5 pages!"
                        )
                        print(f"   Exemples de liens sur la dernière page:")
                        for link in data["links"][:5]:
                            print(f"      • {link}")
                        print()
                else:
                    self.stats["pages_skipped"] += 1

                # Pause ultra-rapide
                time.sleep(0.005)  # 5ms seulement

        finally:
            if self.driver:
                self.driver.quit()

        # RAPPORT FINAL CONSOLE
        print(f"\n{'='*80}")
        print(f"✅ CRAWL MULTI-URLs TERMINÉ")
        print(f"{'='*80}")
        print(f"📈 RÉSULTATS:")
        print(f"   ├─ Points d'entrée: {self.stats['start_urls_count']}")
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
            progress_callback(
                f"✅ Terminé: {self.stats['pages_crawled']} pages crawlées", 1.0
            )

        return self.results, {
            "total_urls": len(self.results),
            "patterns": len(patterns),
            "stats": self.stats,
            "filtered_log": self.filtered_log,
            "duplicate_log": self.duplicate_log,
        }

    def analyze_patterns(self, pages):
        """Analyse les patterns d'URL"""
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
    """
    Récupère le HTML d'une seule page (sans crawler).
    Utilisé par eco_impact, authority, leaf, etc.
    Lève requests.RequestException en cas d'erreur.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


# --- TEST RAPIDE ---
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧪 TEST: Extraction JSON-LD sur site SPA (lamarinerecrute.gouv.fr)")
    print("=" * 80 + "\n")

    # Force Selenium pour ce test
    scraper = SmartScraper(
        "https://lamarinerecrute.gouv.fr/", max_urls=1, use_selenium=True
    )

    data = scraper.get_page_details("https://lamarinerecrute.gouv.fr/")

    if data:
        print(f"\n📄 Page: {data['url']}")
        print(f"   Titre: {data['title']}")
        print(f"   H1: {data['h1']}")
        print(f"   JSON-LD trouvé: {data['has_structured_data']}")

        if data["json_ld"]:
            print(f"\n✅ JSON-LD extrait ({len(data['json_ld'])} bloc(s)):")
            for i, block in enumerate(data["json_ld"], 1):
                print(f"\n--- Bloc {i} ---")
                print(json.dumps(block, indent=2, ensure_ascii=False)[:1000])
                if len(json.dumps(block)) > 1000:
                    print("... (tronqué)")
        else:
            print("\n❌ Aucun JSON-LD trouvé!")
    else:
        print("❌ Échec du scraping")

    # Cleanup
    if scraper.driver:
        scraper.driver.quit()