# =============================================================================
# AUTHORITY SCORE - AI AUTHORITY INDEX
# Mesure la probabilite qu'une entite soit citee par les LLMs
# 5 piliers : Knowledge Graph, Structured Data, Citation Authority,
#              Semantic Completeness, Content Freshness
# =============================================================================

import streamlit as st
import requests
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from collections import Counter
from bs4 import BeautifulSoup

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


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

        # Pilier 1 : Knowledge Graph Coverage (30%)
        try:
            kg = self._analyze_knowledge_graph()
        except Exception as e:
            kg = {"score": 0, "details": {}, "error": str(e)}
            errors.append(("Knowledge Graph", str(e)))
        breakdown["knowledge_graph"] = kg

        # Pilier 2 : Structured Data Footprint (25%)
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

        # Pilier 4 : Semantic Completeness (15%)
        try:
            sc = self._analyze_semantic_completeness()
        except Exception as e:
            sc = {"score": 0, "details": {}, "error": str(e)}
            errors.append(("Semantic Completeness", str(e)))
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
                scripts = soup.find_all("script", type="application/ld+json")

                if scripts:
                    pages_with_jsonld += 1

                for script in scripts:
                    try:
                        ld_data = json.loads(script.string or "{}")
                        types = self._extract_schema_types(ld_data)
                        all_types.update(types)
                        if "Organization" in types:
                            has_org = True
                    except (json.JSONDecodeError, TypeError):
                        pass
            except Exception:
                continue

        details["pages_with_jsonld"] = pages_with_jsonld
        details["schema_types"] = sorted(all_types)
        details["has_organization"] = has_org

        analyzed = details["pages_analyzed"]
        if analyzed > 0:
            details["jsonld_percentage"] = round(pages_with_jsonld / analyzed * 100, 1)

        # Formule du score
        score = min(100, (
            pages_with_jsonld * 2
            + len(all_types) * 10
            + (50 if has_org else 0)
        ))

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
        """Evalue l'autorite de citation via signaux externes"""
        details = {
            "domain_mentions": 0,
            "backlink_estimate": 0,
            "wikipedia_references": 0,
            "social_presence": {},
        }

        domain = urlparse(self.website_url).netloc

        # 1. Verifier les references Wikipedia
        wiki_refs = self._count_wikipedia_references()
        details["wikipedia_references"] = wiki_refs

        # 2. Estimation des backlinks via CommonCrawl index (gratuit)
        backlink_score = self._estimate_backlink_authority(domain)
        details["backlink_estimate"] = backlink_score

        # 3. Presence sociale / mentions
        social = self._check_social_presence()
        details["social_presence"] = social

        # Score composite
        wiki_component = min(40, wiki_refs * 10)
        backlink_component = min(40, backlink_score)
        social_component = min(20, sum(1 for v in social.values() if v) * 5)

        score = min(100, wiki_component + backlink_component + social_component)

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

    def _estimate_backlink_authority(self, domain):
        """Estime l'autorite des backlinks via des signaux indirects"""
        score = 0
        try:
            # Verifier la page d'accueil et ses indicateurs
            r = self.session.get(self.website_url, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")

                # Liens externes entrants mentionnes (hreflang, canonical, etc.)
                canonical = soup.find("link", rel="canonical")
                if canonical:
                    score += 10

                # Presence de hreflang (signe d'un site international)
                hreflangs = soup.find_all("link", rel="alternate", hreflang=True)
                if hreflangs:
                    score += min(15, len(hreflangs) * 3)

                # Presence de schema Organization avec sameAs (liens sociaux)
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        ld = json.loads(script.string or "{}")
                        same_as = ld.get("sameAs", [])
                        if isinstance(same_as, list) and same_as:
                            score += min(15, len(same_as) * 3)
                    except (json.JSONDecodeError, TypeError):
                        pass
        except Exception:
            pass

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

    # =========================================================================
    # PILIER 4 : SEMANTIC COMPLETENESS (15%)
    # =========================================================================
    def _analyze_semantic_completeness(self):
        """Analyse la completude semantique du contenu"""
        details = {
            "unique_concepts": 0,
            "coverage_score": 0.0,
            "top_terms": [],
            "competitor_overlap": 0.0,
        }

        # Extraire le contenu du site
        site_text = self._extract_site_text()
        if not site_text:
            return {"score": 0, "details": details}

        # Extraire les termes du site
        site_terms = self._extract_key_terms(site_text)
        details["unique_concepts"] = len(site_terms)
        details["top_terms"] = site_terms[:20]

        # Comparer avec les concurrents si disponibles
        if self.competitors:
            competitor_texts = []
            for comp_url in self.competitors[:3]:
                comp_text = self._extract_text_from_url(comp_url)
                if comp_text:
                    competitor_texts.append(comp_text)

            if competitor_texts and HAS_SKLEARN:
                coverage = self._compute_coverage(site_text, competitor_texts)
                details["coverage_score"] = round(coverage * 100, 1)
                details["competitor_overlap"] = round(coverage * 100, 1)
            else:
                # Sans concurrents ou sans sklearn, baser sur la richesse seule
                details["coverage_score"] = min(100, len(site_terms) * 2)
        else:
            details["coverage_score"] = min(100, len(site_terms) * 2)

        # Formule du score
        coverage_component = details["coverage_score"] * 0.7
        terms_component = min(100, len(site_terms) / 5 * 100) * 0.3
        score = min(100, coverage_component + terms_component)

        return {"score": round(score, 1), "details": details}

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
        """Extrait le texte d'une URL"""
        try:
            if not url.startswith("http"):
                url = "https://" + url
            r = self.session.get(url, timeout=HTTP_TIMEOUT)
            if r.status_code != 200:
                return ""
            soup = BeautifulSoup(r.text, "html.parser")
            # Retirer les scripts et styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)
        except Exception:
            return ""

    def _extract_key_terms(self, text):
        """Extrait les termes cles d'un texte"""
        if not text:
            return []

        if HAS_SKLEARN:
            try:
                vectorizer = TfidfVectorizer(
                    max_features=100,
                    stop_words=None,
                    min_df=1,
                    ngram_range=(1, 2),
                )
                tfidf = vectorizer.fit_transform([text])
                terms = vectorizer.get_feature_names_out()
                scores = tfidf.toarray()[0]
                sorted_terms = sorted(
                    zip(terms, scores), key=lambda x: x[1], reverse=True
                )
                return [t[0] for t in sorted_terms if len(t[0]) > 3][:50]
            except Exception:
                pass

        # Fallback sans sklearn
        words = re.findall(r"\b[a-zA-ZàâéèêëïîôùûüÿçÀÂÉÈÊËÏÎÔÙÛÜŸÇ]{4,}\b", text.lower())
        counter = Counter(words)
        return [w for w, _ in counter.most_common(50)]

    def _compute_coverage(self, site_text, competitor_texts):
        """Calcule la couverture semantique par rapport aux concurrents"""
        try:
            all_texts = [site_text] + competitor_texts
            vectorizer = TfidfVectorizer(max_features=200, ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform(all_texts)

            # Termes des concurrents
            competitor_terms = set()
            feature_names = vectorizer.get_feature_names_out()
            for i in range(1, len(all_texts)):
                scores = tfidf_matrix[i].toarray()[0]
                top_indices = scores.argsort()[-50:]
                for idx in top_indices:
                    if scores[idx] > 0:
                        competitor_terms.add(feature_names[idx])

            if not competitor_terms:
                return 0.5

            # Termes du site
            site_scores = tfidf_matrix[0].toarray()[0]
            site_terms = set()
            for idx, score in enumerate(site_scores):
                if score > 0:
                    site_terms.add(feature_names[idx])

            overlap = site_terms & competitor_terms
            return len(overlap) / len(competitor_terms) if competitor_terms else 0.5

        except Exception:
            return 0.5

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
            ("Knowledge Graph", breakdown["knowledge_graph"]["score"], "knowledge_graph"),
            ("Structured Data", breakdown["structured_data"]["score"], "structured_data"),
            ("Citation Authority", breakdown["citation_authority"]["score"], "citation_authority"),
            ("Semantic Completeness", breakdown["semantic_completeness"]["score"], "semantic_completeness"),
            ("Content Freshness", breakdown["content_freshness"]["score"], "content_freshness"),
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
                        "(site web, identifiants, description). C'est le facteur #1 de citation par les LLMs."
                    )
                else:
                    recommendations.append(
                        "Enrichir la fiche Wikidata : ajouter des references, identifiants externes "
                        "et liens vers Wikipedia pour renforcer la couverture Knowledge Graph."
                    )

            elif key == "structured_data":
                if score < 30:
                    recommendations.append(
                        "Implementer le balisage JSON-LD sur toutes les pages (Organization, Article, FAQPage). "
                        "Les donnees structurees sont le langage natif des LLMs."
                    )
                else:
                    recommendations.append(
                        "Diversifier les types Schema.org (ajouter FAQPage, HowTo, Product) "
                        "et assurer la presence du type Organization sur la homepage."
                    )

            elif key == "citation_authority":
                recommendations.append(
                    "Renforcer l'autorite de citation : creer/enrichir la page Wikipedia, "
                    "obtenir des backlinks depuis des sources autoritaires, "
                    "et assurer une presence active sur les reseaux sociaux."
                )

            elif key == "semantic_completeness":
                if self.competitors:
                    recommendations.append(
                        "Ameliorer la couverture semantique : analyser les termes utilises par les concurrents "
                        "et enrichir le contenu avec les concepts manquants."
                    )
                else:
                    recommendations.append(
                        "Enrichir le contenu avec plus de concepts uniques, "
                        "de donnees factuelles et de termes du domaine d'expertise."
                    )

            elif key == "content_freshness":
                recommendations.append(
                    "Publier du contenu frais regulierement et mettre a jour les pages existantes. "
                    "Ajouter un sitemap.xml avec les dates lastmod pour signaler la fraicheur aux crawlers."
                )

        return recommendations[:3]


# =============================================================================
# INTERFACE STREAMLIT
# =============================================================================
def _score_color(score):
    """Retourne la couleur selon le score - monochrome"""
    if score >= 70:
        return "#000000"
    elif score >= 40:
        return "rgba(0,0,0,0.55)"
    else:
        return "rgba(0,0,0,0.25)"


def _score_status(score):
    """Retourne le statut"""
    if score >= 70:
        return "FORT"
    elif score >= 40:
        return "MOYEN"
    else:
        return "FAIBLE"


def _interpretation_color(score):
    """Couleur pour l'interpretation globale - monochrome"""
    return "#000000"


def render_authority_score():
    """Rendu principal de l'onglet Authority Score"""

    st.markdown(
        '<h1 class="zen-title">AUTHORITY SCORE</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="zen-subtitle">'
        "AI AUTHORITY INDEX // MESURE LA PROBABILITE DE CITATION PAR LES LLMS</p>",
        unsafe_allow_html=True,
    )

    # === INPUTS ===
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">'
        '<span class="step-badge">01</span>'
        '<span class="section-title" style="margin-bottom:0;">ANALYSE</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-container">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        entity_name = st.text_input(
            "ENTITY NAME",
            placeholder="Ex: Nike, Coca-Cola, LVMH...",
            key="authority_entity_name",
        )
    with col2:
        website_url = st.text_input(
            "WEBSITE",
            placeholder="https://www.example.com",
            key="authority_website_url",
        )

    competitors = st.text_area(
        "COMPETITORS (ONE URL PER LINE)",
        placeholder="https://www.concurrent1.com\nhttps://www.concurrent2.com",
        height=80,
        key="authority_competitors",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("CALCULER L'AUTHORITY SCORE", use_container_width=True, type="primary"):
        if not entity_name or not website_url:
            st.warning("Veuillez renseigner le nom de l'entite et le site web.")
            return

        url = website_url.strip()
        if not url.startswith("http"):
            url = "https://" + url

        comp_list = [c.strip() for c in competitors.strip().split("\n") if c.strip()] if competitors else []

        analyzer = AuthorityScoreAnalyzer(entity_name, url, comp_list)

        with st.spinner("Analyse en cours..."):
            progress = st.progress(0, "Pilier 1/5 : Knowledge Graph Coverage...")

            progress.progress(0.10, "Pilier 1/5 : Knowledge Graph (Wikidata)...")
            result = {"breakdown": {}}

            try:
                kg = analyzer._analyze_knowledge_graph()
            except Exception as e:
                kg = {"score": 0, "details": {}, "error": str(e)}
            result["breakdown"]["knowledge_graph"] = kg

            progress.progress(0.30, "Pilier 2/5 : Structured Data (JSON-LD)...")
            try:
                sd = analyzer._analyze_structured_data()
            except Exception as e:
                sd = {"score": 0, "details": {}, "error": str(e)}
            result["breakdown"]["structured_data"] = sd

            progress.progress(0.50, "Pilier 3/5 : Citation Authority...")
            try:
                ca = analyzer._analyze_citation_authority()
            except Exception as e:
                ca = {"score": 0, "details": {}, "error": str(e)}
            result["breakdown"]["citation_authority"] = ca

            progress.progress(0.70, "Pilier 4/5 : Semantic Completeness...")
            try:
                sc = analyzer._analyze_semantic_completeness()
            except Exception as e:
                sc = {"score": 0, "details": {}, "error": str(e)}
            result["breakdown"]["semantic_completeness"] = sc

            progress.progress(0.90, "Pilier 5/5 : Content Freshness...")
            try:
                cf = analyzer._analyze_content_freshness()
            except Exception as e:
                cf = {"score": 0, "details": {}, "error": str(e)}
            result["breakdown"]["content_freshness"] = cf

            bd = result["breakdown"]
            overall = round(
                bd["knowledge_graph"]["score"] * 0.30
                + bd["structured_data"]["score"] * 0.25
                + bd["citation_authority"]["score"] * 0.20
                + bd["semantic_completeness"]["score"] * 0.15
                + bd["content_freshness"]["score"] * 0.10,
                1,
            )

            interpretation = ""
            for threshold, label, desc in INTERPRETATION_THRESHOLDS:
                if overall >= threshold:
                    interpretation = f"{label} - {desc}"
                    break

            recommendations = analyzer._generate_recommendations(bd)

            errors = []
            for key in bd:
                if "error" in bd[key]:
                    errors.append((key, bd[key]["error"]))

            result.update({
                "overall_score": overall,
                "interpretation": interpretation,
                "recommendations": recommendations,
                "errors": errors,
            })

            progress.progress(1.0, "Analyse terminee.")
            time.sleep(0.3)
            progress.empty()

        st.session_state["authority_result"] = result
        st.session_state["authority_entity"] = entity_name

    # === AFFICHAGE DES RESULTATS ===
    if "authority_result" not in st.session_state:
        return

    result = st.session_state["authority_result"]
    entity = st.session_state.get("authority_entity", "")
    overall = result["overall_score"]
    bd = result["breakdown"]

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    # === ERREURS ===
    for pillar_name, error_msg in result.get("errors", []):
        st.warning(f"Pilier {pillar_name} : analyse partielle ({error_msg})")

    # === SCORE GLOBAL ===
    st.markdown(
        f'<div style="text-align:center;padding:48px 0;">'
        f'<span class="label-caps" style="margin-bottom:16px;display:block;">AI AUTHORITY INDEX</span>'
        f'<div style="font-size:7rem;font-weight:900;line-height:1;color:#000;letter-spacing:-0.05em;font-style:italic;">'
        f'{overall}</div>'
        f'<div style="font-size:0.85rem;font-weight:600;color:rgba(0,0,0,0.4);margin-top:8px;">/100</div>'
        f'<div class="step-badge" style="margin-top:20px;padding:8px 24px;font-size:0.6rem;">'
        f'{result["interpretation"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if entity:
        st.markdown(
            f'<p style="text-align:center;font-size:0.8rem;color:rgba(0,0,0,0.4);margin-top:4px;">'
            f'Entite analysee : <strong style="color:#000;">{entity}</strong></p>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # === BREAKDOWN DES 5 PILIERS ===
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">'
        '<span class="step-badge">02</span>'
        '<span class="section-title" style="margin-bottom:0;">DETAIL PAR PILIER</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    pillar_config = [
        ("Knowledge Graph Coverage", "knowledge_graph", "30%"),
        ("Structured Data Footprint", "structured_data", "25%"),
        ("Citation Authority", "citation_authority", "20%"),
        ("Semantic Completeness", "semantic_completeness", "15%"),
        ("Content Freshness", "content_freshness", "10%"),
    ]

    for display_name, key, weight in pillar_config:
        pillar = bd[key]
        pscore = pillar["score"]
        color = _score_color(pscore)
        status = _score_status(pscore)
        pct = pscore / 100

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:16px;padding:16px 0;'
            f'border-bottom:1px solid rgba(0,0,0,0.08);">'
            f'<div style="min-width:220px;">'
            f'<span style="font-weight:800;font-size:0.7rem;color:#000;letter-spacing:0.05em;text-transform:uppercase;">{display_name}</span>'
            f'<span style="font-size:0.6rem;color:rgba(0,0,0,0.4);margin-left:8px;">({weight})</span>'
            f'</div>'
            f'<div style="flex:1;background:rgba(0,0,0,0.06);height:6px;position:relative;">'
            f'<div style="position:absolute;left:0;top:0;height:100%;width:{pct*100}%;background:{color};"></div>'
            f'</div>'
            f'<div style="min-width:50px;text-align:right;">'
            f'<span style="font-weight:900;font-size:0.9rem;color:#000;">{pscore}</span>'
            f'<span style="font-size:0.65rem;color:rgba(0,0,0,0.4);">/100</span>'
            f'</div>'
            f'<div style="min-width:70px;">'
            f'<span class="step-badge" style="font-size:0.55rem;">{status}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # === DETAILS PAR PILIER (EXPANDERS) ===
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">'
        '<span class="step-badge">03</span>'
        '<span class="section-title" style="margin-bottom:0;">DONNEES DETAILLEES</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Pilier 1 : Knowledge Graph
    with st.expander(f"KNOWLEDGE GRAPH COVERAGE  ({bd['knowledge_graph']['score']}/100)", expanded=False):
        kg_d = bd["knowledge_graph"].get("details", {})
        if kg_d.get("qid"):
            st.markdown(
                f'<div style="padding:12px;border:1px solid rgba(0,0,0,0.12);margin-bottom:12px;">'
                f'<span class="label-caps">QID WIKIDATA</span>'
                f'<div style="font-size:0.9rem;font-weight:700;color:#000;margin-top:4px;">'
                f'<a href="https://www.wikidata.org/wiki/{kg_d["qid"]}" target="_blank" '
                f'style="color:#000;border-bottom:1px solid #000;">'
                f'{kg_d["qid"]}</a></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("PROPRIETES", kg_d.get("nb_properties", 0))
            with col2:
                st.metric("REFERENCES", kg_d.get("nb_references", 0))
            with col3:
                st.metric("IDS EXTERNES", kg_d.get("nb_external_ids", 0))
            with col4:
                st.metric("WIKIPEDIA", "OUI" if kg_d.get("has_wikipedia") else "NON")
        else:
            st.markdown(
                '<p style="font-size:0.8rem;color:#000;font-weight:700;">'
                "Entite non trouvee dans Wikidata.</p>",
                unsafe_allow_html=True,
            )

    # Pilier 2 : Structured Data
    with st.expander(f"STRUCTURED DATA FOOTPRINT  ({bd['structured_data']['score']}/100)", expanded=False):
        sd_d = bd["structured_data"].get("details", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("PAGES ANALYSEES", sd_d.get("pages_analyzed", 0))
        with col2:
            st.metric("PAGES AVEC JSON-LD", sd_d.get("pages_with_jsonld", 0))
        with col3:
            st.metric("% JSON-LD", f'{sd_d.get("jsonld_percentage", 0)}%')

        types = sd_d.get("schema_types", [])
        if types:
            st.markdown(
                '<span class="label-caps" style="margin-top:12px;">TYPES SCHEMA.ORG</span>',
                unsafe_allow_html=True,
            )
            types_html = " ".join(
                f'<span style="display:inline-block;padding:3px 10px;margin:2px;font-size:0.65rem;'
                f'font-weight:700;border:1px solid rgba(0,0,0,0.12);color:#000;letter-spacing:0.05em;">{t}</span>'
                for t in types
            )
            st.markdown(types_html, unsafe_allow_html=True)

        if sd_d.get("has_organization"):
            st.markdown(
                '<p style="font-size:0.75rem;color:#000;font-weight:700;margin-top:8px;">'
                "Type Organization detecte</p>",
                unsafe_allow_html=True,
            )

    # Pilier 3 : Citation Authority
    with st.expander(f"CITATION AUTHORITY  ({bd['citation_authority']['score']}/100)", expanded=False):
        ca_d = bd["citation_authority"].get("details", {})
        col1, col2 = st.columns(2)
        with col1:
            st.metric("REFERENCES WIKIPEDIA", ca_d.get("wikipedia_references", 0))
        with col2:
            st.metric("SCORE BACKLINKS", ca_d.get("backlink_estimate", 0))

        social = ca_d.get("social_presence", {})
        if social:
            st.markdown(
                '<span class="label-caps" style="margin-top:12px;">PRESENCE SOCIALE</span>',
                unsafe_allow_html=True,
            )
            social_html = ""
            for platform, present in social.items():
                bg = "#000" if present else "transparent"
                text_c = "#fff" if present else "rgba(0,0,0,0.4)"
                border = "#000" if present else "rgba(0,0,0,0.12)"
                social_html += (
                    f'<span style="display:inline-block;padding:3px 10px;margin:2px;font-size:0.6rem;'
                    f'font-weight:800;letter-spacing:0.1em;text-transform:uppercase;'
                    f'background:{bg};color:{text_c};border:1px solid {border};">{platform}</span>'
                )
            st.markdown(social_html, unsafe_allow_html=True)

    # Pilier 4 : Semantic Completeness
    with st.expander(f"SEMANTIC COMPLETENESS  ({bd['semantic_completeness']['score']}/100)", expanded=False):
        sc_d = bd["semantic_completeness"].get("details", {})
        col1, col2 = st.columns(2)
        with col1:
            st.metric("CONCEPTS UNIQUES", sc_d.get("unique_concepts", 0))
        with col2:
            st.metric("SCORE COUVERTURE", f'{sc_d.get("coverage_score", 0)}%')

        top_terms = sc_d.get("top_terms", [])
        if top_terms:
            st.markdown(
                '<span class="label-caps" style="margin-top:12px;">TOP TERMES</span>',
                unsafe_allow_html=True,
            )
            terms_html = " ".join(
                f'<span style="display:inline-block;padding:2px 8px;margin:2px;font-size:0.65rem;'
                f'color:rgba(0,0,0,0.55);border:1px solid rgba(0,0,0,0.12);">{t}</span>'
                for t in top_terms[:15]
            )
            st.markdown(terms_html, unsafe_allow_html=True)

    # Pilier 5 : Content Freshness
    with st.expander(f"CONTENT FRESHNESS  ({bd['content_freshness']['score']}/100)", expanded=False):
        cf_d = bd["content_freshness"].get("details", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_age = cf_d.get("avg_age_days")
            st.metric("AGE MOYEN (JOURS)", round(avg_age) if avg_age is not None else "N/A")
        with col2:
            st.metric("DERNIERE PUBLICATION", cf_d.get("last_publication", "N/A"))
        with col3:
            st.metric("PAGES AVEC DATES", cf_d.get("pages_with_dates", 0))

    # === RECOMMANDATIONS ===
    recommendations = result.get("recommendations", [])
    if recommendations:
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">'
            '<span class="step-badge">04</span>'
            '<span class="section-title" style="margin-bottom:0;">RECOMMANDATIONS PRIORITAIRES</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        for i, reco in enumerate(recommendations, 1):
            st.markdown(
                f'<div style="padding:16px;border:1px solid rgba(0,0,0,0.12);border-left:3px solid #000;'
                f'margin-bottom:8px;">'
                f'<span class="label-caps">ACTION {i}</span>'
                f'<div style="font-size:0.85rem;color:#000;line-height:1.6;margin-top:6px;">{reco}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
