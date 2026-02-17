# =============================================================================
# ECO-SCORE - HOTARU
# Calculatrice d'impact carbone : réduction des tokens = sobriété numérique
# =============================================================================

import re
import json

from bs4 import BeautifulSoup

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False


# Constantes physiques (ordre de grandeur)
# E_Token : énergie moyenne (kWh) pour traiter 1000 tokens en inférence (NVIDIA H100)
KWH_PER_1K_TOKENS = 0.0004
# I_Carbone : intensité carbone moyenne mondiale (gCO2/kWh)
GCO2_PER_KWH = 475


class AIOImpactCalculator:
    """
    Calcule l'économie de tokens et l'impact carbone
    entre une page "brute" (HTML complet) et une page optimisée HOTARU (signal pur).
    """

    def __init__(self, timeout=15, engine: str = "v2"):
        self.timeout = timeout
        self.engine = engine
        self._enc = None

    def _fetch_page(self, url: str) -> str:
        """Récupère le HTML via le moteur choisi (v1/v2)."""
        if self.engine == "v2":
            from core.scraping_v2 import fetch_page as _fetch
        else:
            from core.scraping import fetch_page as _fetch
        return _fetch(url, timeout=self.timeout)

    def _get_encoding(self):
        if not HAS_TIKTOKEN:
            return None
        if self._enc is None:
            self._enc = tiktoken.get_encoding("cl100k_base")
        return self._enc

    def _count_tokens(self, text: str) -> int:
        if not text or not HAS_TIKTOKEN:
            return 0
        enc = self._get_encoding()
        return len(enc.encode(text))

    def get_dirty_tokens(self, url: str) -> int:
        """
        Récupère le HTML complet, extrait tout le texte visible (menu, footer, etc.)
        et compte les tokens (poids cognitif "sale").
        """
        try:
            html = self._fetch_page(url)
        except Exception:
            return 0
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return self._count_tokens(text)

    def _extract_jsonld(self, soup: BeautifulSoup) -> str:
        out = []
        for tag in soup.find_all("script", type="application/ld+json"):
            if tag.string:
                try:
                    data = json.loads(tag.string)
                    out.append(json.dumps(data, ensure_ascii=False))
                except (json.JSONDecodeError, TypeError):
                    pass
        return " ".join(out) if out else ""

    def _extract_main_content(self, html: str, url: str) -> str:
        if HAS_TRAFILATURA:
            try:
                main = trafilatura.extract(html, include_comments=False)
                if main and len(main.strip()) > 100:
                    return main.strip()
            except Exception:
                pass
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|main|article", re.I))
        if main:
            return main.get_text(separator=" ", strip=True)
        return soup.get_text(separator=" ", strip=True)

    def get_clean_tokens(self, url: str) -> int:
        """
        Simule une extraction HOTARU : Titre + H1 + Contenu principal + JSON-LD.
        Si pas de JSON-LD, on simule ~10% de la taille du texte brut comme "structure".
        """
        try:
            html = self._fetch_page(url)
        except Exception:
            return 0
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        parts = []

        title = soup.find("title")
        if title and title.string:
            parts.append(title.get_text(strip=True))

        h1 = soup.find("h1")
        if h1:
            parts.append(h1.get_text(separator=" ", strip=True))

        main_text = self._extract_main_content(html, url)
        if main_text:
            parts.append(main_text)

        jsonld = self._extract_jsonld(soup)
        if jsonld:
            parts.append(jsonld)
        else:
            raw_len = len(" ".join(parts))
            if raw_len > 0:
                simulated_ld = " ".join(parts)[: max(100, raw_len // 10)]
                parts.append(simulated_ld)

        clean_text = " ".join(parts)
        clean_text = re.sub(r"\s+", " ", clean_text)
        return self._count_tokens(clean_text)

    def calculate(
        self,
        url: str,
        total_pages: int = 1000,
        daily_views_per_page: int = 100,
    ) -> dict:
        """
        Calcule l'économie : tokens, kWh, gCO2 (par page et par vue).
        Total annuel = Economie_Par_Page * total_pages * daily_views_per_page * 365.
        Renvoie un dictionnaire avec métriques par vue + annuelles.
        """
        if not HAS_TIKTOKEN:
            return {
                "error": "tiktoken non installé. Installez avec: pip install tiktoken",
                "tokens_dirty": 0,
                "tokens_clean": 0,
                "tokens_saved": 0,
                "kwh_saved": 0.0,
                "co2_saved": 0.0,
                "annual_tokens_saved": 0,
                "annual_kwh_saved": 0.0,
                "annual_co2_grammes": 0.0,
            }
        try:
            tokens_dirty = self.get_dirty_tokens(url)
            tokens_clean = self.get_clean_tokens(url)
        except Exception as e:
            return {
                "error": str(e),
                "tokens_dirty": 0,
                "tokens_clean": 0,
                "tokens_saved": 0,
                "kwh_saved": 0.0,
                "co2_saved": 0.0,
                "annual_tokens_saved": 0,
                "annual_kwh_saved": 0.0,
                "annual_co2_grammes": 0.0,
            }
        tokens_saved = max(0, tokens_dirty - tokens_clean)
        kwh_saved = (tokens_saved / 1000.0) * KWH_PER_1K_TOKENS
        co2_saved = kwh_saved * GCO2_PER_KWH

        # Total annuel : Economie_Par_Page * total_pages * daily_views_per_page * 365
        annual_tokens_saved = tokens_saved * total_pages * daily_views_per_page * 365
        annual_kwh_saved = kwh_saved * total_pages * daily_views_per_page * 365
        annual_co2_grammes = co2_saved * total_pages * daily_views_per_page * 365

        return {
            "error": None,
            "tokens_dirty": tokens_dirty,
            "tokens_clean": tokens_clean,
            "tokens_saved": tokens_saved,
            "kwh_saved": round(kwh_saved, 6),
            "co2_saved": round(co2_saved, 2),
            "annual_tokens_saved": annual_tokens_saved,
            "annual_kwh_saved": round(annual_kwh_saved, 2),
            "annual_co2_grammes": round(annual_co2_grammes, 2),
        }
