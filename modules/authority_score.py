# =============================================================================
# AUTHORITY SCORE - AI AUTHORITY INDEX
# Mesure la probabilite qu'une entite soit citee par les LLMs
# 5 piliers : Ancrage Knowledge Graph, Interoperabilite des donnees,
#              Autorite de citation, Densite vectorielle (Semantic Density),
#              Fraicheur de contenu
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
                try:
                    st.warning(
                        "Mode Vecteur indisponible, fallback lexical active. "
                        "Installez 'sentence_transformers' pour un scoring vectoriel precis."
                    )
                except Exception:
                    # En contexte non-UI (tests), on ignore le warning visuel
                    pass

        # Fallback lexical (sans embeddings) : simple recouvrement de tokens
        sim, score = self._lexical_fallback_similarity(site_text, details["target_sentence"])
        details["similarity"] = round(sim, 4)
        if not details["warning"]:
            details["warning"] = (
                "Mode Vecteur indisponible, fallback lexical active "
                "(similarite basee sur le recouvrement de tokens)."
            )
        try:
            st.warning(details["warning"])
        except Exception:
            pass

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
    """Rendu principal de l'onglet Authority Score (SaaS)."""

    st.markdown(
        '<h1 class="zen-title">AUTHORITY SCORE</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="zen-subtitle">'
        "AI AUTHORITY INDEX // MESURE LA COMPATIBILITE D'UNE MARQUE AVEC LES LLMS & SYSTEMES RAG</p>",
        unsafe_allow_html=True,
    )

    tab_analyse, tab_methodo = st.tabs(["Analyse", "Méthodologie"])
    with tab_analyse:
        _render_authority_analyse_content()
    with tab_methodo:
        from modules.methodologie_blocks import render_methodologie_for_module
        render_methodologie_for_module("authority")


def _render_authority_analyse_content():
    """Contenu de l'onglet Analyse (Authority Score)."""
    # === INPUTS ===
    st.markdown(
        '<p class="section-title">01 / ANALYSE</p>',
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

        with st.spinner("Analyse en cours (graphe de connaissances, JSON-LD, vecteurs)..."):
            progress = st.progress(0, "Pilier 1/5 : Ancrage Knowledge Graph...")

            progress.progress(0.10, "Pilier 1/5 : Ancrage Knowledge Graph (Wikidata)...")
            result = {"breakdown": {}}

            try:
                kg = analyzer._analyze_knowledge_graph()
            except Exception as e:
                kg = {"score": 0, "details": {}, "error": str(e)}
            result["breakdown"]["knowledge_graph"] = kg

            progress.progress(0.30, "Pilier 2/5 : Interopérabilité des Données (JSON-LD, sameAs)...")
            try:
                sd = analyzer._analyze_structured_data()
            except Exception as e:
                sd = {"score": 0, "details": {}, "error": str(e)}
            result["breakdown"]["structured_data"] = sd

            progress.progress(0.50, "Pilier 3/5 : Autorité de Citation (signaux externes)...")
            try:
                ca = analyzer._analyze_citation_authority()
            except Exception as e:
                ca = {"score": 0, "details": {}, "error": str(e)}
            result["breakdown"]["citation_authority"] = ca

            progress.progress(0.70, "Pilier 4/5 : Densité Vectorielle (Semantic Density)...")
            try:
                sc = analyzer._analyze_semantic_completeness()
            except Exception as e:
                sc = {"score": 0, "details": {}, "error": str(e)}
            result["breakdown"]["semantic_completeness"] = sc

            progress.progress(0.90, "Pilier 5/5 : Fraîcheur de Contenu...")
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
        '<p class="section-title">02 / DÉTAIL PAR PILIER</p>',
        unsafe_allow_html=True,
    )

    pillar_config = [
        ("Ancrage Knowledge Graph", "knowledge_graph", "30%"),
        ("Interopérabilité des Données", "structured_data", "25%"),
        ("Autorité de Citation", "citation_authority", "20%"),
        ("Densité Vectorielle (Semantic Density)", "semantic_completeness", "15%"),
        ("Fraîcheur de Contenu", "content_freshness", "10%"),
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
        '<p class="section-title">03 / DONNÉES DÉTAILLÉES</p>',
        unsafe_allow_html=True,
    )

    # Pilier 1 : Ancrage Knowledge Graph
    with st.expander(f"ANCRAGE KNOWLEDGE GRAPH  ({bd['knowledge_graph']['score']}/100)", expanded=False):
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

    # Pilier 2 : Interopérabilité des Données
    with st.expander(f"INTEROPÉRABILITÉ DES DONNÉES  ({bd['structured_data']['score']}/100)", expanded=False):
        sd_d = bd["structured_data"].get("details", {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("PAGES ANALYSEES", sd_d.get("pages_analyzed", 0))
        with col2:
            st.metric("PAGES AVEC JSON-LD", sd_d.get("pages_with_jsonld", 0))
        with col3:
            st.metric("% JSON-LD", f'{sd_d.get("jsonld_percentage", 0)}%')
        with col4:
            st.metric("LIENS sameAs", sd_d.get("same_as_count", 0))

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

        if sd_d.get("has_same_as"):
            st.markdown(
                '<p style="font-size:0.75rem;color:#000;font-weight:700;margin-top:4px;">'
                "Propriete <code>sameAs</code> detectee : le site est plus facilement resolu "
                "comme entite unique par les LLMs et les index RAG.</p>",
                unsafe_allow_html=True,
            )

    # Pilier 3 : Autorité de Citation
    with st.expander(f"AUTORITÉ DE CITATION  ({bd['citation_authority']['score']}/100)", expanded=False):
        ca_d = bd["citation_authority"].get("details", {})
        col1, col2 = st.columns(2)
        with col1:
            st.metric("REFERENCES WIKIPEDIA", ca_d.get("wikipedia_references", 0))
        with col2:
            st.metric("SIGNALUX DE CONFIANCE", ca_d.get("trust_signals", 0))

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

    # Pilier 4 : Densité Vectorielle (Semantic Density)
    with st.expander(f"DENSITÉ VECTORIELLE (SEMANTIC DENSITY)  ({bd['semantic_completeness']['score']}/100)", expanded=False):
        sc_d = bd["semantic_completeness"].get("details", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("MODE", sc_d.get("mode", "N/A"))
        with col2:
            st.metric("SIMILARITÉ COSINE", sc_d.get("similarity", 0.0))
        with col3:
            st.metric("TOKENS CONTENU", sc_d.get("site_tokens", 0))

        warning = sc_d.get("warning")
        if warning:
            st.info(
                f"🧠 {warning}"
            )

    # Pilier 5 : Fraîcheur de Contenu
    with st.expander(f"FRAÎCHEUR DE CONTENU  ({bd['content_freshness']['score']}/100)", expanded=False):
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
            '<p class="section-title">04 / RECOMMANDATIONS PRIORITAIRES</p>',
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
