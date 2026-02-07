# =============================================================================
# AUTHORITY SCORE - AI Authority Index
# Score composite mesurant la probabilite qu'une entite soit citee par les LLMs.
# 5 Piliers : Knowledge Graph, Structured Data, Citation, Semantic, Freshness
# =============================================================================

import streamlit as st
import requests
import re
import math
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from collections import Counter
from bs4 import BeautifulSoup

# =============================================================================
# CONSTANTES
# =============================================================================
HTTP_TIMEOUT = 10
MAX_CRAWL_PAGES = 50
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"


# =============================================================================
# CLASSE PRINCIPALE
# =============================================================================

class AuthorityScoreAnalyzer:
    """Analyse l'AI Authority Index d'une entite sur 5 piliers"""

    def __init__(self, entity_name, website_url, competitors=None):
        self.entity_name = entity_name.strip()
        self.website_url = website_url.strip().rstrip('/')
        self.competitors = [c.strip() for c in (competitors or []) if c.strip()]
        self.errors = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; HotaruBot/2.0; +https://hotaru.app)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })

    def compute_full_score(self):
        """Calcule le score complet et retourne un dict avec tous les resultats"""
        kg = self._analyze_knowledge_graph()
        sd = self._analyze_structured_data()
        ca = self._analyze_citation_authority()
        sc = self._analyze_semantic_completeness()
        cf = self._analyze_content_freshness()

        overall = (
            kg['score'] * 0.30 +
            sd['score'] * 0.25 +
            ca['score'] * 0.20 +
            sc['score'] * 0.15 +
            cf['score'] * 0.10
        )
        overall = round(overall, 1)

        if overall >= 80:
            interpretation = "Autorite Forte - Tres probablement cite par les LLMs"
        elif overall >= 60:
            interpretation = "Autorite Moyenne - Citation occasionnelle"
        elif overall >= 40:
            interpretation = "Autorite Faible - Rarement cite"
        else:
            interpretation = "Autorite Tres Faible - Invisible pour les LLMs"

        recommendations = self._generate_recommendations(kg, sd, ca, sc, cf)

        return {
            'overall_score': overall,
            'breakdown': {
                'knowledge_graph': kg,
                'structured_data': sd,
                'citation_authority': ca,
                'semantic_completeness': sc,
                'content_freshness': cf,
            },
            'interpretation': interpretation,
            'recommendations': recommendations,
            'errors': self.errors
        }

    # =========================================================================
    # PILIER 1 : Knowledge Graph Coverage (30%)
    # =========================================================================
    def _analyze_knowledge_graph(self):
        """Analyse la presence et la richesse sur Wikidata"""
        data = {
            'qid': None,
            'nb_properties': 0,
            'nb_references': 0,
            'has_wikipedia': False,
            'nb_external_ids': 0,
            'label': '',
            'description': '',
        }

        try:
            # Recherche de l'entite sur Wikidata
            params = {
                'action': 'wbsearchentities',
                'search': self.entity_name,
                'language': 'fr',
                'uselang': 'fr',
                'type': 'item',
                'limit': 5,
                'format': 'json'
            }
            r = self.session.get(WIKIDATA_API, params=params, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            results = r.json().get('search', [])

            if not results:
                # Essayer en anglais
                params['language'] = 'en'
                params['uselang'] = 'en'
                r = self.session.get(WIKIDATA_API, params=params, timeout=HTTP_TIMEOUT)
                r.raise_for_status()
                results = r.json().get('search', [])

            if not results:
                return {'score': 0, 'data': data, 'status': 'absent'}

            # Prendre le premier resultat
            qid = results[0]['id']
            data['qid'] = qid
            data['label'] = results[0].get('label', '')
            data['description'] = results[0].get('description', '')

            # Recuperer les details de l'entite
            params_entity = {
                'action': 'wbgetentities',
                'ids': qid,
                'format': 'json',
                'props': 'claims|sitelinks'
            }
            r = self.session.get(WIKIDATA_API, params=params_entity, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            entity = r.json().get('entities', {}).get(qid, {})

            # Compter les proprietes (claims)
            claims = entity.get('claims', {})
            data['nb_properties'] = len(claims)

            # Compter les references dans les claims
            nb_refs = 0
            nb_ext_ids = 0
            for prop_id, prop_values in claims.items():
                for val in prop_values:
                    nb_refs += len(val.get('references', []))
                    # Les identifiants externes ont un datatype "external-id"
                    mainsnak = val.get('mainsnak', {})
                    if mainsnak.get('datatype') == 'external-id':
                        nb_ext_ids += 1

            data['nb_references'] = nb_refs
            data['nb_external_ids'] = nb_ext_ids

            # Verifier la presence de liens Wikipedia
            sitelinks = entity.get('sitelinks', {})
            data['has_wikipedia'] = any(
                k.endswith('wiki') and not k.startswith('common')
                for k in sitelinks.keys()
            )

            # Calcul du score
            score = min(100, (
                data['nb_properties'] * 2 +
                (20 if data['has_wikipedia'] else 0) +
                data['nb_references'] * 5 +
                data['nb_external_ids'] * 2
            ))

            return {'score': score, 'data': data, 'status': 'found'}

        except Exception as e:
            self.errors.append(f"Knowledge Graph: {e}")
            return {'score': 0, 'data': data, 'status': 'error'}

    # =========================================================================
    # PILIER 2 : Structured Data Footprint (25%)
    # =========================================================================
    def _analyze_structured_data(self):
        """Analyse la presence de JSON-LD sur le site"""
        data = {
            'pages_crawled': 0,
            'pages_with_jsonld': 0,
            'schema_types': [],
            'has_organization': False,
            'jsonld_samples': [],
        }

        try:
            # Collecter les URLs a analyser
            urls_to_check = self._collect_site_urls()
            data['pages_crawled'] = len(urls_to_check)

            all_types = set()

            for url in urls_to_check:
                try:
                    r = self.session.get(url, timeout=HTTP_TIMEOUT)
                    if r.status_code != 200:
                        continue

                    soup = BeautifulSoup(r.content, 'html.parser')
                    ld_scripts = soup.find_all('script', type='application/ld+json')

                    if ld_scripts:
                        data['pages_with_jsonld'] += 1

                        for script in ld_scripts:
                            try:
                                import json
                                ld_data = json.loads(script.string)

                                # Extraire les types
                                if isinstance(ld_data, list):
                                    for item in ld_data:
                                        t = item.get('@type', '')
                                        if t:
                                            all_types.add(t if isinstance(t, str) else str(t))
                                elif isinstance(ld_data, dict):
                                    t = ld_data.get('@type', '')
                                    if t:
                                        all_types.add(t if isinstance(t, str) else str(t))

                                    # Verifier @graph
                                    for g in ld_data.get('@graph', []):
                                        t = g.get('@type', '')
                                        if t:
                                            all_types.add(t if isinstance(t, str) else str(t))

                                if len(data['jsonld_samples']) < 3:
                                    data['jsonld_samples'].append({
                                        'url': url,
                                        'types': list(all_types)[-3:]
                                    })
                            except Exception:
                                pass

                    time.sleep(0.05)

                except Exception:
                    continue

            data['schema_types'] = sorted(all_types)
            data['has_organization'] = 'Organization' in all_types

            # Calcul du score
            score = min(100, (
                data['pages_with_jsonld'] * 2 +
                len(all_types) * 10 +
                (50 if data['has_organization'] else 0)
            ))

            return {'score': score, 'data': data, 'status': 'ok'}

        except Exception as e:
            self.errors.append(f"Structured Data: {e}")
            return {'score': 0, 'data': data, 'status': 'error'}

    def _collect_site_urls(self):
        """Collecte les URLs du site via sitemap ou crawl leger"""
        urls = [self.website_url]

        # Essayer le sitemap d'abord
        sitemap_urls = self._parse_sitemap(f"{self.website_url}/sitemap.xml")
        if not sitemap_urls:
            sitemap_urls = self._parse_sitemap(f"{self.website_url}/sitemap_index.xml")
        if not sitemap_urls:
            sitemap_urls = self._parse_sitemap(f"{self.website_url}/sitemap/")

        if sitemap_urls:
            urls = list(set(sitemap_urls))[:MAX_CRAWL_PAGES]
        else:
            # Crawl leger de la page d'accueil pour trouver des liens
            try:
                r = self.session.get(self.website_url, timeout=HTTP_TIMEOUT)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.content, 'html.parser')
                    domain = urlparse(self.website_url).netloc
                    for a in soup.find_all('a', href=True):
                        full = urljoin(self.website_url, a['href'])
                        if urlparse(full).netloc == domain:
                            clean = full.split('#')[0].split('?')[0]
                            urls.append(clean)
                    urls = list(set(urls))[:MAX_CRAWL_PAGES]
            except Exception:
                pass

        return urls

    def _parse_sitemap(self, url):
        """Parse un sitemap XML et retourne les URLs"""
        try:
            r = self.session.get(url, timeout=HTTP_TIMEOUT)
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.content, 'lxml-xml')

            # Sitemap index -> recursion sur les sous-sitemaps
            sitemaps = soup.find_all('sitemap')
            if sitemaps:
                all_urls = []
                for sm in sitemaps[:3]:  # Max 3 sous-sitemaps
                    loc = sm.find('loc')
                    if loc:
                        all_urls.extend(self._parse_sitemap(loc.text.strip()))
                return all_urls[:MAX_CRAWL_PAGES]

            # Sitemap standard
            locs = soup.find_all('loc')
            return [loc.text.strip() for loc in locs][:MAX_CRAWL_PAGES]

        except Exception:
            return []

    # =========================================================================
    # PILIER 3 : Citation Authority (20%)
    # =========================================================================
    def _analyze_citation_authority(self):
        """Analyse l'autorite de citation via backlinks et mentions"""
        data = {
            'backlink_score': 0,
            'mention_score': 0,
            'domain_authority_estimate': 0,
            'external_references': 0,
        }

        try:
            domain = urlparse(self.website_url).netloc

            # Methode 1 : Verifier les headers de la page d'accueil pour des signaux d'autorite
            r = self.session.get(self.website_url, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                soup = BeautifulSoup(r.content, 'html.parser')

                # Compter les liens externes sortants (indicateur indirect de connectivite)
                external_links = 0
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith('http') and domain not in href:
                        external_links += 1
                data['external_references'] = external_links

                # Verifier la presence de signaux d'autorite
                # - Liens vers des reseaux sociaux
                # - Mentions de presse
                # - Certifications
                authority_signals = 0
                html_text = r.text.lower()
                social_platforms = ['linkedin.com', 'twitter.com', 'x.com', 'facebook.com',
                                    'youtube.com', 'github.com', 'instagram.com']
                for platform in social_platforms:
                    if platform in html_text:
                        authority_signals += 5

                press_keywords = ['press', 'presse', 'media', 'news', 'article', 'mention',
                                  'award', 'prix', 'certification', 'partner', 'partenaire']
                for kw in press_keywords:
                    if kw in html_text:
                        authority_signals += 3

                data['backlink_score'] = min(50, authority_signals)

            # Methode 2 : Verifier la presence sur Wikidata/Wikipedia (deja fait dans pilier 1)
            # On estime l'autorite via des heuristiques accessibles gratuitement

            # Methode 3 : Essayer de trouver des mentions via une recherche
            # sur le nom de l'entite (heuristique basee sur le contenu)
            mention_count = 0
            try:
                # Verifier les pages "a propos" / "about" pour des mentions de partenaires/clients
                about_paths = ['/about', '/a-propos', '/qui-sommes-nous', '/about-us', '/company']
                for path in about_paths:
                    try:
                        r_about = self.session.get(f"{self.website_url}{path}", timeout=5)
                        if r_about.status_code == 200:
                            text = r_about.text.lower()
                            # Compter les noms propres et references
                            mention_count += len(re.findall(r'(?:client|partner|reference|mention|cite)', text))
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            data['mention_score'] = min(50, mention_count * 5)
            data['domain_authority_estimate'] = min(100, data['backlink_score'] + data['mention_score'])

            score = min(100, data['domain_authority_estimate'])
            return {'score': score, 'data': data, 'status': 'ok'}

        except Exception as e:
            self.errors.append(f"Citation Authority: {e}")
            return {'score': 0, 'data': data, 'status': 'error'}

    # =========================================================================
    # PILIER 4 : Semantic Completeness (15%)
    # =========================================================================
    def _analyze_semantic_completeness(self):
        """Analyse la completude semantique via TF-IDF simplifie"""
        data = {
            'unique_concepts': 0,
            'coverage_score': 0,
            'top_terms': [],
            'competitor_gap': [],
        }

        try:
            # Extraire le texte du site principal
            site_terms = self._extract_site_terms(self.website_url)
            data['unique_concepts'] = len(site_terms)
            data['top_terms'] = [t[0] for t in site_terms.most_common(15)]

            # Comparer avec les concurrents si disponibles
            if self.competitors:
                competitor_terms = Counter()
                for comp_url in self.competitors[:3]:
                    try:
                        comp_terms = self._extract_site_terms(comp_url)
                        competitor_terms.update(comp_terms)
                    except Exception:
                        continue

                if competitor_terms:
                    # Calculer la couverture : combien de termes concurrents on couvre
                    comp_top = set(t[0] for t in competitor_terms.most_common(50))
                    site_top = set(t[0] for t in site_terms.most_common(100))
                    covered = comp_top.intersection(site_top)
                    coverage = len(covered) / max(len(comp_top), 1) * 100

                    data['coverage_score'] = round(coverage, 1)
                    data['competitor_gap'] = list(comp_top - site_top)[:10]
                else:
                    data['coverage_score'] = 50  # Score neutre sans concurrents
            else:
                # Sans concurrents, evaluer sur la richesse absolue
                data['coverage_score'] = min(100, len(site_terms) / 2)

            # Formule : (coverage * 0.7) + (unique_terms / 5 * 0.3)
            score = min(100, (
                data['coverage_score'] * 0.7 +
                (len(site_terms) / 5) * 0.3
            ))

            return {'score': round(score, 1), 'data': data, 'status': 'ok'}

        except Exception as e:
            self.errors.append(f"Semantic Completeness: {e}")
            return {'score': 0, 'data': data, 'status': 'error'}

    def _extract_site_terms(self, url):
        """Extrait les termes significatifs d'un site"""
        terms = Counter()
        # Stopwords francais + anglais basiques
        stopwords = {
            'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'en', 'est',
            'que', 'qui', 'dans', 'pour', 'pas', 'sur', 'au', 'aux', 'avec', 'son',
            'sa', 'ses', 'ce', 'cette', 'ces', 'nous', 'vous', 'ils', 'elles', 'par',
            'plus', 'ne', 'se', 'ou', 'mais', 'tout', 'tous', 'toutes', 'bien', 'aussi',
            'the', 'and', 'is', 'in', 'to', 'of', 'for', 'on', 'with', 'at', 'by',
            'from', 'or', 'an', 'be', 'this', 'that', 'are', 'was', 'were', 'has',
            'have', 'had', 'not', 'but', 'all', 'can', 'her', 'his', 'its', 'our',
            'your', 'their', 'which', 'each', 'she', 'he', 'how', 'been', 'other',
            'than', 'then', 'now', 'look', 'only', 'come', 'could', 'will', 'would',
            'about', 'into', 'some', 'them', 'may', 'more', 'nos', 'notre', 'votre',
            'vos', 'leur', 'leurs', 'dont', 'comme', 'fait', 'entre', 'etre', 'avoir',
            'dit', 'faire', 'peut', 'encore', 'apres', 'avant', 'depuis', 'lors', 'tres',
        }

        try:
            r = self.session.get(url, timeout=HTTP_TIMEOUT)
            if r.status_code != 200:
                return terms

            soup = BeautifulSoup(r.content, 'html.parser')

            # Supprimer les scripts et styles
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()

            text = soup.get_text(separator=' ')
            # Nettoyer et tokeniser
            words = re.findall(r'\b[a-zA-ZàâäéèêëïîôùûüÿçœæÀÂÄÉÈÊËÏÎÔÙÛÜŸÇŒÆ]{3,}\b', text.lower())
            for word in words:
                if word not in stopwords and len(word) > 3:
                    terms[word] += 1

        except Exception:
            pass

        return terms

    # =========================================================================
    # PILIER 5 : Content Freshness (10%)
    # =========================================================================
    def _analyze_content_freshness(self):
        """Analyse la fraicheur du contenu via sitemap.xml"""
        data = {
            'avg_age_days': None,
            'last_publication': None,
            'pages_analyzed': 0,
            'freshness_distribution': {},
        }

        try:
            dates = []

            # Essayer d'extraire les dates du sitemap
            for sitemap_url in [
                f"{self.website_url}/sitemap.xml",
                f"{self.website_url}/sitemap_index.xml",
                f"{self.website_url}/sitemap/"
            ]:
                try:
                    r = self.session.get(sitemap_url, timeout=HTTP_TIMEOUT)
                    if r.status_code != 200:
                        continue

                    soup = BeautifulSoup(r.content, 'lxml-xml')

                    # Chercher dans les sitemaps index
                    sitemaps = soup.find_all('sitemap')
                    if sitemaps:
                        for sm in sitemaps[:3]:
                            loc = sm.find('loc')
                            lastmod = sm.find('lastmod')
                            if lastmod:
                                dates.append(lastmod.text.strip())
                            if loc:
                                try:
                                    r_sub = self.session.get(loc.text.strip(), timeout=HTTP_TIMEOUT)
                                    if r_sub.status_code == 200:
                                        soup_sub = BeautifulSoup(r_sub.content, 'lxml-xml')
                                        for lm in soup_sub.find_all('lastmod'):
                                            dates.append(lm.text.strip())
                                except Exception:
                                    pass
                        break

                    # Sitemap standard
                    lastmods = soup.find_all('lastmod')
                    if lastmods:
                        dates = [lm.text.strip() for lm in lastmods]
                        break

                except Exception:
                    continue

            if not dates:
                # Fallback : verifier les headers Last-Modified de la homepage
                try:
                    r = self.session.head(self.website_url, timeout=HTTP_TIMEOUT)
                    last_mod = r.headers.get('Last-Modified', '')
                    if last_mod:
                        dates.append(last_mod)
                except Exception:
                    pass

            if not dates:
                return {'score': 0, 'data': data, 'status': 'no_dates'}

            # Parser les dates
            now = datetime.now()
            ages = []
            parsed_dates = []

            for date_str in dates[:200]:  # Limiter
                parsed = self._parse_date(date_str)
                if parsed:
                    parsed_dates.append(parsed)
                    age = (now - parsed).days
                    if age >= 0:
                        ages.append(age)

            if not ages:
                return {'score': 0, 'data': data, 'status': 'unparseable'}

            data['pages_analyzed'] = len(ages)
            data['avg_age_days'] = round(sum(ages) / len(ages), 1)
            data['last_publication'] = max(parsed_dates).strftime('%Y-%m-%d')

            # Distribution de fraicheur
            fresh = sum(1 for a in ages if a <= 30)
            recent = sum(1 for a in ages if 30 < a <= 90)
            old = sum(1 for a in ages if 90 < a <= 365)
            stale = sum(1 for a in ages if a > 365)
            total = len(ages)

            data['freshness_distribution'] = {
                'fresh_30j': round(fresh / total * 100, 1),
                'recent_90j': round(recent / total * 100, 1),
                'old_365j': round(old / total * 100, 1),
                'stale': round(stale / total * 100, 1),
            }

            # Formule : max(0, 100 - (avg_age_days / 10))
            score = max(0, 100 - (data['avg_age_days'] / 10))
            return {'score': round(score, 1), 'data': data, 'status': 'ok'}

        except Exception as e:
            self.errors.append(f"Content Freshness: {e}")
            return {'score': 0, 'data': data, 'status': 'error'}

    def _parse_date(self, date_str):
        """Parse une date depuis differents formats"""
        formats = [
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%a, %d %b %Y %H:%M:%S %Z',
            '%a, %d %b %Y %H:%M:%S %z',
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str[:30], fmt)
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
            except Exception:
                continue
        return None

    # =========================================================================
    # RECOMMANDATIONS
    # =========================================================================
    def _generate_recommendations(self, kg, sd, ca, sc, cf):
        """Genere les recommandations prioritaires basees sur les piliers faibles"""
        piliers = [
            ('Knowledge Graph', kg['score'], 0.30, [
                "Creer ou enrichir la fiche Wikidata de l'entite avec plus de proprietes et references.",
                "Ajouter des identifiants externes (SIREN, LinkedIn, site officiel) sur Wikidata.",
                "Creer ou completer la page Wikipedia de l'entite.",
            ]),
            ('Structured Data', sd['score'], 0.25, [
                "Implementer le balisage JSON-LD Organization sur la page d'accueil.",
                "Ajouter des schemas JSON-LD sur chaque page (Article, Product, FAQ, etc.).",
                "Diversifier les types Schema.org utilises pour enrichir le graphe de connaissances.",
            ]),
            ('Citation Authority', ca['score'], 0.20, [
                "Developper une strategie de backlinks vers des sites a forte autorite.",
                "Publier des etudes ou contenus citables par d'autres sites et LLMs.",
                "Renforcer la presence sur les reseaux sociaux et plateformes professionnelles.",
            ]),
            ('Semantic Completeness', sc['score'], 0.15, [
                "Enrichir le contenu avec les termes cles manquants identifies chez les concurrents.",
                "Creer du contenu factuel structure (tableaux, listes, donnees chiffrees).",
                "Couvrir les questions frequentes du secteur avec des pages FAQ structurees.",
            ]),
            ('Content Freshness', cf['score'], 0.10, [
                "Mettre a jour le sitemap.xml avec les dates de modification.",
                "Publier ou mettre a jour du contenu regulierement (objectif : < 90 jours).",
                "Ajouter des dates de publication et de mise a jour visibles sur les pages.",
            ]),
        ]

        # Trier par score (les plus faibles d'abord), ponderer par le poids
        piliers.sort(key=lambda x: x[1])

        recommendations = []
        for name, score, weight, recos in piliers[:3]:
            # Prendre la reco la plus pertinente du pilier le plus faible
            if score < 70:
                recommendations.append(f"[{name}] {recos[0]}")
            elif score < 40:
                recommendations.extend(f"[{name}] {r}" for r in recos[:2])

        if not recommendations:
            recommendations.append("Votre score est solide. Maintenez la fraicheur du contenu et enrichissez regulierement les donnees structurees.")

        return recommendations[:5]


# =============================================================================
# INTERFACE STREAMLIT
# =============================================================================

def _pillar_status_icon(score):
    """Retourne l'icone de statut selon le score"""
    if score >= 70:
        return "PASS", "#10b981"
    elif score >= 40:
        return "WARN", "#FFA500"
    else:
        return "FAIL", "#FF4B4B"


def _render_pillar_bar(name, score, weight_pct, details_data, pillar_key):
    """Affiche une barre de progression pour un pilier"""
    status_label, status_color = _pillar_status_icon(score)

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:16px;padding:16px 0;border-bottom:1px solid #f1f5f9;">'
        f'<span style="min-width:200px;font-size:0.85rem;font-weight:700;color:#0f172a;">{name}</span>'
        f'<span style="min-width:50px;font-size:0.6rem;font-weight:700;color:#94a3b8;letter-spacing:0.1em;">{weight_pct}%</span>'
        f'<div style="flex:1;background:#f1f5f9;height:8px;position:relative;">'
        f'<div style="width:{min(score, 100)}%;height:100%;background:{status_color};"></div>'
        f'</div>'
        f'<span style="min-width:45px;font-size:1rem;font-weight:900;color:{status_color};text-align:right;">{round(score)}</span>'
        f'<span style="display:inline-block;padding:2px 10px;font-size:0.55rem;font-weight:800;'
        f'letter-spacing:0.1em;background:{status_color};color:#fff;min-width:35px;text-align:center;">'
        f'{status_label}</span>'
        f'</div>',
        unsafe_allow_html=True
    )


def _render_pillar_detail_kg(data):
    """Detail du pilier Knowledge Graph"""
    d = data.get('data', {})
    status = data.get('status', 'error')

    if status == 'absent':
        st.markdown(
            '<p style="font-size:0.85rem;color:#FF4B4B;font-weight:600;">'
            'Entite non trouvee sur Wikidata. Aucun QID associe.</p>',
            unsafe_allow_html=True
        )
        return

    if status == 'error':
        st.markdown(
            '<p style="font-size:0.85rem;color:#FF4B4B;">Erreur lors de l\'analyse Wikidata.</p>',
            unsafe_allow_html=True
        )
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("QID", d.get('qid', 'N/A'))
    with col2:
        st.metric("Proprietes", d.get('nb_properties', 0))
    with col3:
        st.metric("References", d.get('nb_references', 0))
    with col4:
        st.metric("IDs Externes", d.get('nb_external_ids', 0))

    c1, c2 = st.columns(2)
    with c1:
        wiki_status = "Oui" if d.get('has_wikipedia') else "Non"
        st.markdown(f"**Wikipedia** : {wiki_status}")
    with c2:
        st.markdown(f"**Label** : {d.get('label', '')} - {d.get('description', '')}")


def _render_pillar_detail_sd(data):
    """Detail du pilier Structured Data"""
    d = data.get('data', {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pages crawlees", d.get('pages_crawled', 0))
    with col2:
        st.metric("Pages avec JSON-LD", d.get('pages_with_jsonld', 0))
    with col3:
        has_org = "Oui" if d.get('has_organization') else "Non"
        st.metric("Type Organization", has_org)

    types = d.get('schema_types', [])
    if types:
        st.markdown(f"**Types Schema.org detectes** : {', '.join(types)}")


def _render_pillar_detail_ca(data):
    """Detail du pilier Citation Authority"""
    d = data.get('data', {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score Backlinks", d.get('backlink_score', 0))
    with col2:
        st.metric("Score Mentions", d.get('mention_score', 0))
    with col3:
        st.metric("Refs Externes", d.get('external_references', 0))


def _render_pillar_detail_sc(data):
    """Detail du pilier Semantic Completeness"""
    d = data.get('data', {})
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Concepts Uniques", d.get('unique_concepts', 0))
    with col2:
        st.metric("Couverture (%)", f"{d.get('coverage_score', 0)}")

    top = d.get('top_terms', [])
    if top:
        st.markdown(f"**Top termes** : {', '.join(top[:10])}")

    gap = d.get('competitor_gap', [])
    if gap:
        st.markdown(f"**Termes concurrents manquants** : {', '.join(gap[:8])}")


def _render_pillar_detail_cf(data):
    """Detail du pilier Content Freshness"""
    d = data.get('data', {})

    if data.get('status') == 'no_dates':
        st.markdown(
            '<p style="font-size:0.85rem;color:#FFA500;">Aucune date trouvee dans le sitemap ou les headers.</p>',
            unsafe_allow_html=True
        )
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        avg = d.get('avg_age_days')
        st.metric("Age Moyen (jours)", round(avg) if avg else "N/A")
    with col2:
        st.metric("Derniere Publication", d.get('last_publication', 'N/A'))
    with col3:
        st.metric("Pages Analysees", d.get('pages_analyzed', 0))

    dist = d.get('freshness_distribution', {})
    if dist:
        st.markdown(
            f"**Distribution** : "
            f"< 30j : {dist.get('fresh_30j', 0)}% | "
            f"30-90j : {dist.get('recent_90j', 0)}% | "
            f"90-365j : {dist.get('old_365j', 0)}% | "
            f"> 1an : {dist.get('stale', 0)}%"
        )


# =============================================================================
# RENDER PRINCIPAL
# =============================================================================

def render_authority_score():
    """Interface Streamlit complete pour l'Authority Score"""

    st.markdown(
        '<p class="section-title">AI AUTHORITY INDEX</p>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="font-size:0.8rem;color:#94a3b8;font-style:italic;margin-bottom:24px;">'
        'Score composite mesurant la probabilite qu\'une entite soit citee par les LLMs (ChatGPT, Gemini, Claude).</p>',
        unsafe_allow_html=True
    )

    # === INPUTS ===
    st.markdown('<div class="zen-card">', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    entity_name = c1.text_input(
        "Nom de l'entite",
        placeholder="Ex: Nike, Coca-Cola, SNCF...",
        key="authority_entity_name"
    )
    website_url = c2.text_input(
        "Site web",
        placeholder="https://www.example.com",
        key="authority_website_url"
    )
    competitors_raw = st.text_area(
        "URLs concurrents (une par ligne, optionnel)",
        placeholder="https://concurrent1.com\nhttps://concurrent2.com",
        height=80,
        key="authority_competitors"
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("CALCULER L'AUTHORITY SCORE", use_container_width=True, type="primary", key="btn_authority"):
        if not entity_name or not website_url:
            st.markdown(
                '<p style="color:#FF4B4B;font-weight:700;font-size:0.85rem;">'
                'Veuillez renseigner le nom de l\'entite et le site web.</p>',
                unsafe_allow_html=True
            )
        else:
            # Normaliser l'URL
            if not website_url.startswith('http'):
                website_url = f"https://{website_url}"

            competitors = [c.strip() for c in competitors_raw.strip().split('\n') if c.strip()]

            with st.spinner("Analyse en cours... (5 piliers a evaluer, ~30 secondes)"):
                analyzer = AuthorityScoreAnalyzer(entity_name, website_url, competitors)
                result = analyzer.compute_full_score()
                st.session_state['authority_result'] = result
                st.session_state['authority_entity'] = entity_name
                st.session_state['authority_url'] = website_url

    st.markdown('</div>', unsafe_allow_html=True)

    # === RESULTATS ===
    if 'authority_result' not in st.session_state:
        return

    result = st.session_state['authority_result']
    entity = st.session_state.get('authority_entity', '')
    overall = result['overall_score']
    breakdown = result['breakdown']

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    # === SCORE GLOBAL ===
    if overall >= 80:
        score_color = "#10b981"
    elif overall >= 60:
        score_color = "#FFA500"
    elif overall >= 40:
        score_color = "#FF4B4B"
    else:
        score_color = "#FF4B4B"

    st.markdown(
        f'<div style="text-align:center;padding:40px 0;">'
        f'<div style="font-size:0.6rem;font-weight:800;letter-spacing:0.3em;text-transform:uppercase;'
        f'color:#94a3b8;margin-bottom:16px;">AI AUTHORITY INDEX &mdash; {entity.upper()}</div>'
        f'<div style="font-size:7rem;font-weight:900;color:{score_color};line-height:1;letter-spacing:-0.04em;">'
        f'{round(overall)}</div>'
        f'<div style="font-size:1.2rem;font-weight:700;color:#94a3b8;margin-top:8px;">/100</div>'
        f'<div style="margin-top:16px;">'
        f'<span style="display:inline-block;padding:8px 24px;font-size:0.65rem;font-weight:800;'
        f'letter-spacing:0.2em;text-transform:uppercase;background:{score_color};color:#fff;">'
        f'{result["interpretation"]}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    # === BREAKDOWN DES 5 PILIERS ===
    st.markdown(
        '<p class="section-title">DECOMPOSITION PAR PILIER</p>',
        unsafe_allow_html=True
    )

    pillar_config = [
        ("Knowledge Graph Coverage", 30, 'knowledge_graph'),
        ("Structured Data Footprint", 25, 'structured_data'),
        ("Citation Authority", 20, 'citation_authority'),
        ("Semantic Completeness", 15, 'semantic_completeness'),
        ("Content Freshness", 10, 'content_freshness'),
    ]

    for name, weight, key in pillar_config:
        pillar = breakdown[key]
        _render_pillar_bar(name, pillar['score'], weight, pillar, key)

    st.markdown("<br>", unsafe_allow_html=True)

    # === DETAILS PAR PILIER (expanders) ===
    st.markdown(
        '<p class="section-title">DETAILS PAR PILIER</p>',
        unsafe_allow_html=True
    )

    detail_renderers = {
        'knowledge_graph': ("Knowledge Graph Coverage (30%)", _render_pillar_detail_kg),
        'structured_data': ("Structured Data Footprint (25%)", _render_pillar_detail_sd),
        'citation_authority': ("Citation Authority (20%)", _render_pillar_detail_ca),
        'semantic_completeness': ("Semantic Completeness (15%)", _render_pillar_detail_sc),
        'content_freshness': ("Content Freshness (10%)", _render_pillar_detail_cf),
    }

    for key, (label, renderer) in detail_renderers.items():
        pillar = breakdown[key]
        status_label, status_color = _pillar_status_icon(pillar['score'])
        with st.expander(f"{label}  —  {round(pillar['score'])}/100  [{status_label}]", expanded=False):
            renderer(pillar)

    st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)

    # === RECOMMANDATIONS ===
    st.markdown(
        '<p class="section-title">RECOMMANDATIONS PRIORITAIRES</p>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="padding:24px;border:2px solid #0f172a;background:#fafafa;">',
        unsafe_allow_html=True
    )

    for i, reco in enumerate(result['recommendations'], 1):
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:16px;padding:12px 0;'
            f'border-bottom:1px solid #e2e8f0;">'
            f'<span style="background:#0f172a;color:#fff;padding:2px 10px;font-size:0.65rem;'
            f'font-weight:800;min-width:24px;text-align:center;">{i}</span>'
            f'<span style="font-size:0.85rem;color:#0f172a;line-height:1.5;">{reco}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # === ERREURS ===
    if result.get('errors'):
        st.markdown("<br>", unsafe_allow_html=True)
        for err in result['errors']:
            st.warning(f"Pilier en echec : {err}")
