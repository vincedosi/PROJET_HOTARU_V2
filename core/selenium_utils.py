"""
Utilitaires Selenium - Éliminer la duplication (70+ LOC)
Extraction de core/scraping.py lines 143-221 + 401-425
"""
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def get_chrome_options(
    headless: bool = True,
    proxy: str = None,
    no_images: bool = True,
    eager_loading: bool = True,
) -> Options:
    """
    Configure les options Chrome de manière centralisée.

    Args:
        headless: Mode headless (par défaut True)
        proxy: URL proxy optionnelle (http://ip:port)
        no_images: Désactiver les images (plus rapide)
        eager_loading: Page load strategy = eager (interactive, pas images)

    Returns:
        Options configurées pour Chrome/Chromium
    """
    options = Options()

    # Headless mode
    if headless:
        options.add_argument("--headless=new")

    # Sécurité et stabilité (Streamlit Cloud)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")

    # Performance: ne pas charger images
    if no_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

    # Page load strategy
    if eager_loading:
        options.page_load_strategy = "eager"

    # Proxy (si fourni)
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    return options


def find_chromium_binary() -> str:
    """
    Cherche le binaire Chromium installé.
    Recherche dans l'ordre: which(), chemins communs, fallback None.

    Returns:
        Chemin au binaire Chromium ou None
    """
    candidates = [
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for path in candidates:
        if path:
            return path
    return None


def find_chromedriver_binary() -> str:
    """
    Cherche le binaire ChromeDriver installé.

    Returns:
        Chemin au binaire ChromeDriver ou None
    """
    candidates = [
        shutil.which("chromedriver"),
        "/usr/bin/chromedriver",
    ]
    for path in candidates:
        if path:
            return path
    return None


def create_chrome_driver(
    headless: bool = True,
    proxy: str = None,
    no_images: bool = True,
    log_callback=None,
) -> webdriver.Chrome:
    """
    Factory pour créer un driver Chrome/Chromium.
    Gère la recherche des binaires et la configuration.

    Args:
        headless: Mode headless
        proxy: URL proxy optionnelle
        no_images: Désactiver images
        log_callback: Callback pour logs (optionnel)

    Returns:
        WebDriver Chrome configuré

    Raises:
        RuntimeError: Si Chromium/ChromeDriver non trouvé
    """
    # Configure options
    options = get_chrome_options(headless, proxy, no_images)

    # Find Chromium
    chromium_binary = find_chromium_binary()
    if chromium_binary:
        if log_callback:
            log_callback(f"Chromium trouvé: {chromium_binary}")
        options.binary_location = chromium_binary
    else:
        if log_callback:
            log_callback("⚠️ Chromium NOT found - using system default")

    # Find ChromeDriver
    chromedriver_binary = find_chromedriver_binary()
    if chromedriver_binary:
        if log_callback:
            log_callback(f"ChromeDriver trouvé: {chromedriver_binary}")
        service = Service(chromedriver_binary)
        return webdriver.Chrome(service=service, options=options)
    else:
        if log_callback:
            log_callback("⚠️ ChromeDriver NOT found - using webdriver discovery")
        return webdriver.Chrome(options=options)


__all__ = [
    "get_chrome_options",
    "find_chromium_binary",
    "find_chromedriver_binary",
    "create_chrome_driver",
]
