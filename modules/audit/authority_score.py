# =============================================================================
# AUTHORITY SCORE - AI AUTHORITY INDEX (Logique pure, sans Streamlit)
# Mesure la probabilite qu'une entite soit citee par les LLMs
# 5 piliers : Ancrage Knowledge Graph, Interoperabilite des donnees,
#              Autorite de citation, Densite vectorielle (Semantic Density),
#              Fraicheur de contenu
# =============================================================================

import logging
import requests
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from collections import Counter
from bs4 import BeautifulSoup

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None  # type: ignore
    HAS_SENTENCE_TRANSFORMERS = False


# =============================================================================
# CONSTANTES
# =============================================================================
HTTP_TIMEOUT = 10
MAX_CRAWL_PAGES = 50
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

PILLAR_WEIGHTS = {
    "knowledge_graph": 0.30,
    "structured_data": 0.25,
    "citation_authority": 0.20,
    "semantic_completeness": 0.15,
    "content_freshness": 0.10,
}

INTERPRETATION_THRESHOLDS = [
    (80, "Autorite Forte", "Tres probablement cite par les LLMs"),
    (60, "Autorite Moyenne", "Citation occasionnelle par les LLMs"),
    (40, "Autorite Faible", "Rarement cite par les LLMs"),
    (0, "Autorite Tres Faible", "Invisible pour les LLMs"),
]


# =============================================================================
# CLASSE PRINCIPALE
# =============================================================================
class AuthorityScoreAnalyzer:
    """Calcule l'AI Authority Index d'une entite"""

    def __init__(self, entity_name, website_url, competitors=None):
        self.entity_name = entity_name.strip()
        self.website_url = website_url.strip().rstrip("/")
        self.competitors = [c.strip() for c in (competitors or []) if c.strip()]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; HotaruBot/2.0)"
        })

    # =========================================================================
    # SCORE GLOBAL
    # =========================================================================
    def compute_full_score(self):
        """Calcule le score complet et retourne un dict structure"""
        breakdown = {}
        errors = []

        # Pilier 1 : Ancrage Knowledge Graph (30%)
        try:
            kg = self._analyze_knowledge_graph()
        except Exception as e:
            kg = {"score": 0, "details": {}, "error": str(e)}
            errors.append(("Knowledge Graph", str(e)))
        breakdown["knowledge_graph"] = kg

        # Pilier 2 : Interoperabilite des donnees (25%)
        try:
            sd = self._analyze_structured_data()
        except Exception as e:
            sd = {"score": 0, "details": {}, "error": str(e)}
            errors.append(("Structured Data", str(e)))
        breakdown["structured_data"] = sd

        # Pilier 3 : Citation Authority (20%)
        try:
            ca = self._analyze_citation_authority()
        except Exception as e:
            ca = {"score": 0, "details": {}, "error": str(e)}
            errors.append(("Citation Authority", str(e)))
        breakdown["citation_authority"] = ca

        # Pilier 4 : Densite vectorielle (Semantic Density) (15%)
        try:
            sc = self._analyze_semantic_completeness()
        except Exception as e:
            sc = {"score": 0, "details": {}, "error": str(e)}
            errors.append(("Densite vectorielle (Semantic Density)", str(e)))
        breakdown["semantic_completeness"] = sc

        # Pilier 5 : Content Freshness (10%)
        try:
            cf = self._analyze_content_freshness()
        except Exception as e:
            cf = {"score": 0, "details": {}, "error": str(e)}
            errors.append(("Content Freshness", str(e)))
        breakdown["content_freshness"] = cf

        # Score final pondere
        overall = (
            breakdown["knowledge_graph"]["score"] * PILLAR_WEIGHTS["knowledge_graph"]
            + breakdown["structured_data"]["score"] * PILLAR_WEIGHTS["structured_data"]
            + breakdown["citation_authority"]["score"] * PILLAR_WEIGHTS["citation_authority"]
            + breakdown["semantic_completeness"]["score"] * PILLAR_WEIGHTS["semantic_completeness"]
            + breakdown["content_freshness"]["score"] * PILLAR_WEIGHTS["content_freshness"]
        )
        overall = round(overall, 1)

        # Interpretation
        interpretation = ""
        for threshold, label, desc in INTERPRETATION_THRESHOLDS:
            if overall >= threshold:
                interpretation = f"{label} - {desc}"
                break

        # Recommandations prioritaires
        recommendations = self._generate_recommendations(breakdown)

        return {
            "overall_score": overall,
            "breakdown": breakdown,
            "interpretation": interpretation,
            "recommendations": recommendations,
            "errors": errors,
        }

    # =========================================================================
    # PILIER 1 : KNOWLEDGE GRAPH COVERAGE (30%)
    # =========================================================================
    def _analyze_knowledge_graph(self):
        """Analyse la presence de l'entite dans Wikidata"""
        details = {
            "qid": None,
            "nb_properties": 0,
            "nb_references": 0,
            "has_wikipedia": False,
            "nb_external_ids": 0,
            "label": "",
        }

        # Recherche dans Wikidata
        qid = self._search_wikidata(self.entity_name)
        if not qid:
            return {"score": 0, "details": details}

        details["qid"] = qid

        # Recuperer les donnees de l'entite
        entity_data = self._get_wikidata_entity(qid)
        if not entity_data:
            return {"score": 5, "details": details}

        claims = entity_data.get("claims", {})
        sitelinks = entity_data.get("sitelinks", {})
        labels = entity_data.get("labels", {})

        details["label"] = labels.get("fr", labels.get("en", {})).get("value", "")
        details["nb_properties"] = len(claims)

        # Compter les references dans les claims
        nb_refs = 0
        nb_external_ids = 0
        for prop_id, prop_claims in claims.items():
            for claim in prop_claims:
                refs = claim.get("references", [])
                nb_refs += len(refs)
                # Detecter les identifiants externes (proprietes P commencant par un external-id)
                mainsnak = claim.get("mainsnak", {})
                if mainsnak.get("datatype") == "external-id":
                    nb_external_ids += 1

        details["nb_references"] = nb_refs
        details["nb_external_ids"] = nb_external_ids

        # Presence Wikipedia
        has_wiki = any(k.endswith("wiki") for k in sitelinks)
        details["has_wikipedia"] = has_wiki

        # Formule du score
        score = min(100, (
            details["nb_properties"] * 2
            + (20 if has_wiki else 0)
            + details["nb_references"] * 5
            + details["nb_external_ids"] * 2
        ))

        return {"score": score, "details": details}

    def _search_wikidata(self, query):
        """Cherche une entite sur Wikidata et retourne le QID"""
        params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "fr",
            "uselang": "fr",
            "format": "json",
            "limit": 5,
        }
        try:
            r = self.session.get(WIKIDATA_API, params=params, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            results = data.get("search", [])
            if results:
                return results[0]["id"]
        except Exception:
            pass

        # Fallback en anglais
        params["language"] = "en"
        params["uselang"] = "en"
        try:
            r = self.session.get(WIKIDATA_API, params=params, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            results = data.get("search", [])
            if results:
                return results[0]["id"]
        except Exception:
            pass

        return None

    def _get_wikidata_entity(self, qid):
        """Recupere les donnees completes d'une entite Wikidata"""
        params = {
            "action": "wbgetentities",
            "ids": qid,
            "format": "json",
        }
        try:
            r = self.session.get(WIKIDATA_API, params=params, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            return data.get("entities", {}).get(qid, {})
        except Exception:
            return None

    # =========================================================================
    # PILIER 2 : STRUCTURED DATA FOOTPRINT (25%)
    # =========================================================================
    def _analyze_structured_data(self):
        """Analyse la presence de donnees structurees sur le site"""
        details = {
            "pages_analyzed": 0,
            "pages_with_jsonld": 0,
            "schema_types": [],
            "has_organization": False,
            "jsonld_percentage": 0.0,
            # Nouveaux indicateurs AI-native
            "has_same_as": False,
            "same_as_count": 0,
        }

        # Collecter les URLs a analyser
        urls = self._collect_site_urls()
        if not urls:
            urls = [self.website_url]

        pages_with_jsonld = 0
        all_types = set()
        has_org = False

        for url in urls[:MAX_CRAWL_PAGES]:
            try:
                r = self.session.get(url, timeout=HTTP_TIMEOUT)
                if r.status_code != 200:
                    continue
                details["pages_analyzed"] += 1

                soup = BeautifulSoup(r.text, "html.parser")
                # Accepte toutes les variantes de type contenant "ld+json"
                scripts = soup.find_all(
                    "script",
                    type=lambda t: isinstance(t, str) and "ld+json" in t.lower(),
                )

                if scripts:
                    pages_with_jsonld += 1

                for script in scripts:
                    try:
                        ld_raw = script.string or script.text or ""
                        if not ld_raw.strip():
                            continue
                        ld_data = json.loads(ld_raw)
                        types = self._extract_schema_types(ld_data)
                        all_types.update(types)
                        if "Organization" in types:
                            has_org = True
                        same_as_count = self._count_same_as(ld_data)
                        if same_as_count > 0:
                            details["has_same_as"] = True
                            details["same_as_count"] += same_as_count
                    except (json.JSONDecodeError, TypeError):
                        continue
            except Exception:
                continue

        details["pages_with_jsonld"] = pages_with_jsonld
        details["schema_types"] = sorted(all_types)
        details["has_organization"] = has_org

        analyzed = details["pages_analyzed"]
        if analyzed > 0:
            details["jsonld_percentage"] = round(
                pages_with_jsonld / analyzed * 100, 1
            )

        # Formule du score (AI-native) :
        # - couverture JSON-LD
        # - diversite des types Schema.org
        # - presence d'une Organization racine
        # - BONUS sameAs pour la resolution d'entite / RAG
        score = (
            pages_with_jsonld * 2
            + len(all_types) * 8
            + (40 if has_org else 0)
        )
        if details["has_same_as"]:
            score += 10

        score = min(100, score)

        return {"score": score, "details": details}

    def _extract_schema_types(self, ld_data):
        """Extrait les types Schema.org d'un objet JSON-LD"""
        types = set()
        if isinstance(ld_data, dict):
            t = ld_data.get("@type", "")
            if isinstance(t, str) and t:
                types.add(t)
            elif isinstance(t, list):
                types.update(t)
            # Gerer @graph
            graph = ld_data.get("@graph", [])
            if isinstance(graph, list):
                for item in graph:
                    types.update(self._extract_schema_types(item))
        elif isinstance(ld_data, list):
            for item in ld_data:
                types.update(self._extract_schema_types(item))
        return types

    def _count_same_as(self, ld_data):
        """Compte le nombre de liens sameAs dans un bloc JSON-LD."""
        count = 0
        if isinstance(ld_data, dict):
            for key, value in ld_data.items():
                if key == "sameAs":
                    if isinstance(value, list):
                        count += len(value)
                    elif isinstance(value, str):
                        count += 1
                else:
                    count += self._count_same_as(value)
        elif isinstance(ld_data, list):
            for item in ld_data:
                count += self._count_same_as(item)
        return count

    def _collect_site_urls(self):
        """Collecte les URLs du site via sitemap ou crawl leger"""
        urls = set()

        # Essayer le sitemap
        sitemap_candidates = [
            f"{self.website_url}/sitemap.xml",
            f"{self.website_url}/sitemap_index.xml",
            f"{self.website_url}/sitemap/",
        ]

        for sitemap_url in sitemap_candidates:
            try:
                r = self.session.get(sitemap_url, timeout=HTTP_TIMEOUT)
                if r.status_code == 200 and "xml" in r.headers.get("content-type", ""):
                    parsed_urls = self._parse_sitemap(r.text)
                    urls.update(parsed_urls)
                    if urls:
                        break
            except Exception:
                continue

        # Si pas de sitemap, crawl leger de la homepage
        if not urls:
            try:
                r = self.session.get(self.website_url, timeout=HTTP_TIMEOUT)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    domain = urlparse(self.website_url).netloc
                    for a in soup.find_all("a", href=True):
                        full_url = urljoin(self.website_url, a["href"])
                        if urlparse(full_url).netloc == domain:
                            urls.add(full_url.split("#")[0].split("?")[0])
            except Exception:
                pass

        # Toujours inclure la homepage
        urls.add(self.website_url)
        return list(urls)[:MAX_CRAWL_PAGES]

    def _parse_sitemap(self, xml_content):
        """Parse un sitemap XML et retourne les URLs"""
        urls = set()
        try:
            root = ET.fromstring(xml_content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Sitemap index
            for sitemap in root.findall(".//sm:sitemap/sm:loc", ns):
                if sitemap.text:
                    try:
                        r = self.session.get(sitemap.text.strip(), timeout=HTTP_TIMEOUT)
                        if r.status_code == 200:
                            child_urls = self._parse_sitemap(r.text)
                            urls.update(child_urls)
                            if len(urls) >= MAX_CRAWL_PAGES:
                                break
                    except Exception:
                        continue

            # URLs directes
            for url_elem in root.findall(".//sm:url/sm:loc", ns):
                if url_elem.text:
                    urls.add(url_elem.text.strip())
                    if len(urls) >= MAX_CRAWL_PAGES:
                        break

        except ET.ParseError:
            pass
        return urls

    # =========================================================================
    # PILIER 3 : CITATION AUTHORITY (20%)
    # =========================================================================
    def _analyze_citation_authority(self):
        """Evalue l'autorite de citation via signaux externes et signaux de confiance."""
        details = {
            "domain_mentions": 0,
            "trust_signals": 0,
            "wikipedia_references": 0,
            "social_presence": {},
        }

        domain = urlparse(self.website_url).netloc

        # 1. Verifier les references Wikipedia
        wiki_refs = self._count_wikipedia_references()
        details["wikipedia_references"] = wiki_refs

        # 2. Signaux de confiance (page d'accueil) — remplace l'ancienne estimation backlinks
        soup_home = None
        try:
            r = self.session.get(self.website_url, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                soup_home = BeautifulSoup(r.text, "html.parser")
        except Exception:
            pass
        trust_score = self._analyze_trust_signals(domain, soup_home)
        details["trust_signals"] = trust_score

        # 3. Presence sociale / mentions
        social = self._check_social_presence()
        details["social_presence"] = social

        # Score composite
        wiki_component = min(40, wiki_refs * 10)
        trust_component = min(40, trust_score)
        social_component = min(20, sum(1 for v in social.values() if v) * 5)

        score = min(100, wiki_component + trust_component + social_component)

        return {"score": score, "details": details}

    def _count_wikipedia_references(self):
        """Compte le nombre de references a l'entite sur Wikipedia"""
        try:
            # Recherche Wikipedia
            params = {
                "action": "query",
                "list": "search",
                "srsearch": self.entity_name,
                "format": "json",
                "srlimit": 10,
            }
            r = self.session.get(
                "https://fr.wikipedia.org/w/api.php",
                params=params,
                timeout=HTTP_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("query", {}).get("search", [])
            return len(results)
        except Exception:
            return 0

    def _analyze_trust_signals(self, domain, soup):
        """
        Score de confiance (sur 40 pts) basé sur les éléments de réassurance
        sur la page d'accueil. soup peut être None (retourne 0).
        """
        if soup is None:
            return 0

        score = 0
        html_lower = soup.get_text().lower() if soup else ""
        all_links = " ".join(
            (a.get("href") or "") + " " + (a.get_text() or "")
            for a in soup.find_all("a", href=True)
        ).lower()

        # +10 pts : Mentions Légales / Politique de confidentialité
        legal_patterns = [
            "mentions", "legal", "légal", "confidentialité", "privacy",
            "terms", "conditions", "cgv", "cgu", "mentions-legales",
        ]
        if any(p in all_links or p in html_lower for p in legal_patterns):
            score += 10

        # +10 pts : Contact / À propos
        contact_patterns = ["contact", "about", "propos", "nous-contacter", "a-propos"]
        if any(p in all_links or p in html_lower for p in contact_patterns):
            score += 10

        # +10 pts : Email visible (mailto: ou pattern textuel)
        email_re = re.compile(
            r"(?:mailto:)?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            re.IGNORECASE,
        )
        if email_re.search(html_lower) or email_re.search(all_links):
            score += 10

        # +10 pts : Téléphone visible (format intl ou local)
        phone_re = re.compile(
            r"(?:\+33|0)[\s.-]?[1-9](?:[\s.-]?\d{2}){4}|"
            r"\+?\d{1,4}[\s.-]?\(?\d{2,3}\)?[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}",
        )
        if phone_re.search(html_lower) or phone_re.search(all_links):
            score += 10

        return min(40, score)

    def _check_social_presence(self):
        """Verifie la presence sur les reseaux sociaux via les liens du site"""
        platforms = {
            "linkedin": False,
            "twitter": False,
            "facebook": False,
            "youtube": False,
            "instagram": False,
        }
        try:
            r = self.session.get(self.website_url, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].lower()
                    for platform in platforms:
                        if platform in href:
                            platforms[platform] = True
        except Exception:
            pass
        return platforms

    def _similarity_to_score(self, similarity: float) -> float:
        """
        Mapping non-lineaire de la similarite cosine vers un score 0-100.
        - < 0.3  : tres faible alignement
        - 0.3-0.6 : zone de progression
        - 0.6-0.85 : bon alignement
        - > 0.85 : excellent alignement
        """
        sim = max(0.0, min(similarity, 1.0))
        if sim <= 0.3:
            return sim / 0.3 * 40.0
        elif sim <= 0.6:
            return 40.0 + (sim - 0.3) / 0.3 * 30.0
        elif sim <= 0.85:
            return 70.0 + (sim - 0.6) / 0.25 * 20.0
        else:
            return 90.0 + (sim - 0.85) / 0.15 * 10.0

    # =========================================================================
    # PILIER 4 : DENSITE VECTORIELLE (Semantic Density) (15%)
    # =========================================================================
    def _analyze_semantic_completeness(self):
        """
        Analyse la densite vectorielle (Semantic Density) du contenu.

        Objectif : mesurer dans l'espace d'embeddings a quel point le contenu
        du site est aligne avec une phrase cible representant l'identite
        et l'offre officielle de la marque.
        """
        details = {
            "mode": "vector" if HAS_SENTENCE_TRANSFORMERS else "lexical_fallback",
            "similarity": 0.0,
            "target_sentence": "",
            "site_tokens": 0,
            "warning": None,
        }

        # Extraire le contenu du site (texte brut aggrege sur quelques pages)
        site_text = self._extract_site_text()
        if not site_text:
            return {"score": 0, "details": details}

        tokens = re.findall(r"\w+", site_text)
        details["site_tokens"] = len(tokens)

        # Phrase cible qui encode l'identite de la marque dans un espace vectoriel
        target_sentence = (
            f"""Expertise technique, mission officielle et services de {self.entity_name}.
            Informations factuelles, produits, services, secteurs couverts et preuves sociales
            destinees a entrainer des modeles de langage et des systemes RAG."""
        )
        details["target_sentence"] = target_sentence.strip()

        # Mode vecteur (sentence_transformers) si disponible
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                if not hasattr(self, "_st_model"):
                    # Modele generaliste, leger et largement supporte
                    self._st_model = SentenceTransformer("all-MiniLM-L6-v2")

                embeddings = self._st_model.encode(
                    [site_text, details["target_sentence"]],
                    normalize_embeddings=True,
                )
                site_vec, target_vec = embeddings

                # Produit scalaire car vecteurs normalises => cosine similarity
                similarity = float((site_vec * target_vec).sum())
                similarity = max(min(similarity, 1.0), -1.0)
                details["similarity"] = round(similarity, 4)

                # Mapping non-lineaire cosine -> score 0-100 (plus discriminant)
                score = round(self._similarity_to_score(similarity), 1)

                return {"score": score, "details": details}

            except Exception as e:
                details["warning"] = f"Erreur mode vecteur: {e}"
                details["mode"] = "lexical_fallback"
                logging.warning(
                    "Mode Vecteur indisponible, fallback lexical actif. "
                    "Installez 'sentence_transformers' pour un scoring vectoriel precis."
                )

        # Fallback lexical (sans embeddings) : simple recouvrement de tokens
        sim, score = self._lexical_fallback_similarity(site_text, details["target_sentence"])
        details["similarity"] = round(sim, 4)
        if not details["warning"]:
            details["warning"] = (
                "Mode Vecteur indisponible, fallback lexical actif "
                "(similarite basee sur le recouvrement de tokens)."
            )
        logging.warning(details["warning"])
        return {"score": score, "details": details}

    def _extract_site_text(self):
        """Extrait le texte principal du site"""
        texts = []
        urls = self._collect_site_urls()[:10]  # Limiter a 10 pages

        for url in urls:
            text = self._extract_text_from_url(url)
            if text:
                texts.append(text)

        return " ".join(texts)

    def _extract_text_from_url(self, url):
        """Extrait le contenu principal propre (trafilatura), fallback soup.get_text()."""
        try:
            if not url.startswith("http"):
                url = "https://" + url
            r = self.session.get(url, timeout=HTTP_TIMEOUT)
            if r.status_code != 200:
                return ""
            text = None
            if HAS_TRAFILATURA:
                text = trafilatura.extract(r.text)
            if text and text.strip():
                return text.strip()
            # Fallback : ancienne méthode (soup sans nav/footer/header)
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)
        except Exception:
            return ""

    def _lexical_fallback_similarity(self, site_text, target_sentence):
        """
        Fallback sans embeddings : similarite basee sur le recouvrement de tokens.

        Utilise un simple ratio d'intersection de vocabulaire pour approximer
        la proximite entre le contenu du site et la phrase cible.
        """
        site_tokens = set(
            re.findall(r"\w+", site_text.lower())
        )
        target_tokens = set(
            re.findall(r"\w+", target_sentence.lower())
        )

        if not site_tokens or not target_tokens:
            return 0.0, 0.0

        overlap = site_tokens & target_tokens
        sim = len(overlap) / len(target_tokens) if target_tokens else 0.0
        sim = max(0.0, min(sim, 1.0))
        score = round(sim * 100, 1)
        return sim, score

    # =========================================================================
    # PILIER 5 : CONTENT FRESHNESS (10%)
    # =========================================================================
    def _analyze_content_freshness(self):
        """Analyse la fraicheur du contenu via sitemap.xml"""
        details = {
            "avg_age_days": None,
            "last_publication": None,
            "pages_with_dates": 0,
            "total_pages_checked": 0,
        }

        dates = []

        # Parser le sitemap pour les dates lastmod
        sitemap_candidates = [
            f"{self.website_url}/sitemap.xml",
            f"{self.website_url}/sitemap_index.xml",
            f"{self.website_url}/sitemap/",
        ]

        for sitemap_url in sitemap_candidates:
            try:
                r = self.session.get(sitemap_url, timeout=HTTP_TIMEOUT)
                if r.status_code == 200 and "xml" in r.headers.get("content-type", ""):
                    sitemap_dates = self._extract_sitemap_dates(r.text)
                    dates.extend(sitemap_dates)
                    if dates:
                        break
            except Exception:
                continue

        # Fallback : verifier les headers HTTP Last-Modified
        if not dates:
            try:
                r = self.session.head(self.website_url, timeout=HTTP_TIMEOUT)
                last_mod = r.headers.get("Last-Modified")
                if last_mod:
                    try:
                        dt = datetime.strptime(last_mod, "%a, %d %b %Y %H:%M:%S GMT")
                        dates.append(dt)
                    except ValueError:
                        pass
            except Exception:
                pass

        details["total_pages_checked"] = len(dates)
        details["pages_with_dates"] = len(dates)

        if not dates:
            return {"score": 0, "details": details}

        now = datetime.now()
        ages = [(now - d).days for d in dates if d < now]

        if not ages:
            return {"score": 0, "details": details}

        avg_age = sum(ages) / len(ages)
        details["avg_age_days"] = round(avg_age, 1)
        details["last_publication"] = max(dates).strftime("%Y-%m-%d")

        # Formule : max(0, 100 - (avg_age_days / 10))
        score = max(0, min(100, 100 - (avg_age / 10)))

        return {"score": round(score, 1), "details": details}

    def _extract_sitemap_dates(self, xml_content):
        """Extrait les dates lastmod d'un sitemap"""
        dates = []
        try:
            root = ET.fromstring(xml_content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Sitemap index : aller chercher les sous-sitemaps
            for sitemap in root.findall(".//sm:sitemap/sm:loc", ns):
                if sitemap.text and len(dates) < MAX_CRAWL_PAGES:
                    try:
                        r = self.session.get(sitemap.text.strip(), timeout=HTTP_TIMEOUT)
                        if r.status_code == 200:
                            child_dates = self._extract_sitemap_dates(r.text)
                            dates.extend(child_dates)
                    except Exception:
                        continue

            # Dates directes
            for lastmod in root.findall(".//sm:url/sm:lastmod", ns):
                if lastmod.text:
                    dt = self._parse_date(lastmod.text.strip())
                    if dt:
                        dates.append(dt)
                    if len(dates) >= MAX_CRAWL_PAGES:
                        break

        except ET.ParseError:
            pass

        return dates

    def _parse_date(self, date_str):
        """Parse differents formats de date"""
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str[:19], fmt[:len(date_str) + 2] if "%" in fmt else fmt)
                return dt.replace(tzinfo=None) if hasattr(dt, "tzinfo") else dt
            except (ValueError, TypeError):
                continue
        # Dernier essai generique
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
        return None

    # =========================================================================
    # RECOMMANDATIONS
    # =========================================================================
    def _generate_recommendations(self, breakdown):
        """Genere les 2-3 recommandations prioritaires basees sur les piliers les plus faibles"""
        pillar_scores = [
            ("Ancrage Knowledge Graph", breakdown["knowledge_graph"]["score"], "knowledge_graph"),
            ("Interopérabilité des Données", breakdown["structured_data"]["score"], "structured_data"),
            ("Autorité de Citation", breakdown["citation_authority"]["score"], "citation_authority"),
            ("Densité Vectorielle", breakdown["semantic_completeness"]["score"], "semantic_completeness"),
            ("Fraîcheur de Contenu", breakdown["content_freshness"]["score"], "content_freshness"),
        ]

        # Trier par score croissant
        pillar_scores.sort(key=lambda x: x[1])

        recommendations = []

        for name, score, key in pillar_scores[:3]:
            if score >= 80:
                continue

            if key == "knowledge_graph":
                if score == 0:
                    recommendations.append(
                        f"Creer une fiche Wikidata pour '{self.entity_name}' avec les proprietes essentielles "
                        "(site web officiel, identifiants externes, description factuelle). "
                        "C'est un point d'ancrage central pour les LLMs et les systemes RAG."
                    )
                else:
                    recommendations.append(
                        "Enrichir la fiche Wikidata : ajouter des references, identifiants externes "
                        "(ISNI, SIREN, etc.) et des liens vers Wikipedia pour renforcer l'ancrage Knowledge Graph "
                        "dans les jeux de donnees d'entrainement."
                    )

            elif key == "structured_data":
                if score < 30:
                    recommendations.append(
                        "Implementer un JSON-LD propre et complet (Organization, WebSite, WebPage) sur les pages strategiques. "
                        "Les donnees structurees sont le langage d'interoperabilite natif des LLMs."
                    )
                else:
                    recommendations.append(
                        "Renforcer l'interoperabilite : "
                        "utiliser la propriete sameAs pour lier le site aux profils officiels (Wikidata, Wikipedia, reseaux sociaux) "
                        "et diversifier les types Schema.org (FAQPage, HowTo, Product) sur les pages idoines."
                    )

            elif key == "citation_authority":
                recommendations.append(
                    "Renforcer l'autorite de citation : creer/enrichir la page Wikipedia, "
                    "multiplier les citations dans des sources de reference (medias, organismes officiels) "
                    "et maintenir une presence active sur les reseaux sociaux relies au site officiel."
                )

            elif key == "semantic_completeness":
                recommendations.append(
                    "Augmenter la densite vectorielle : clarifier la proposition de valeur, "
                    "structurer les pages autour de blocs d'information factuels (qui, quoi, ou, preuves, donnees chiffrées) "
                    "et injecter des exemples concrets pour faciliter l'encodage en embeddings utiles au RAG."
                )

            elif key == "content_freshness":
                recommendations.append(
                    "Publier du contenu frais regulierement, mettre a jour les pages existantes et exposer les dates "
                    "de mise a jour via sitemap.xml (lastmod). Des contenus recents sont sur-representees dans les "
                    "datasets recents et les index RAG."
                )

        return recommendations[:3]


# =============================================================================
# API PUBLIQUE (sans Streamlit)
# =============================================================================
def compute_authority_score(entity_name: str, website_url: str, competitors: list = None) -> dict:
    """
    Calcule l'AI Authority Index d'une entite.
    Retourne un dict avec overall_score, breakdown, interpretation, recommendations, errors.
    """
    url = website_url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    comp_list = [c.strip() for c in (competitors or []) if c.strip()]
    analyzer = AuthorityScoreAnalyzer(entity_name.strip(), url, comp_list)
    return analyzer.compute_full_score()
