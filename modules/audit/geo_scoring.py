"""
Module de scoring GEO (Generative Engine Optimization)
Évalue la qualité d'une page pour être citée par les LLMs (ChatGPT, Claude, Perplexity, etc.)
"""

import re
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup

class GEOScorer:
    """
    Calcule un score GEO sur 100 points basé sur des critères techniques
    optimisés pour la découvrabilité par les moteurs génératifs
    """
    
    def __init__(self):
        self.weights = {
            'meta_description': 15,
            'h1_quality': 10,
            'response_time': 10,
            'structured_data': 15,
            'semantic_structure': 20,
            'content_depth': 15,
            'entity_richness': 10,
            'freshness': 5
        }
    
    def calculate_score(self, page_data):
        """
        Calcule le score GEO global d'une page
        
        Args:
            page_data (dict): Données de la page contenant url, title, description, 
                            html_content, response_time, last_modified, etc.
        
        Returns:
            dict: {
                'total_score': int (0-100),
                'breakdown': dict des scores par critère,
                'recommendations': list des recommandations,
                'grade': str (A+, A, B, C, D, F)
            }
        """
        scores = {}
        recommendations = []
        
        # 1. Meta Description (15 points)
        meta_score, meta_reco = self._score_meta_description(page_data)
        scores['meta_description'] = meta_score
        recommendations.extend(meta_reco)
        
        # 2. Qualité H1 (10 points)
        h1_score, h1_reco = self._score_h1_quality(page_data)
        scores['h1_quality'] = h1_score
        recommendations.extend(h1_reco)
        
        # 3. Performance (10 points)
        perf_score, perf_reco = self._score_response_time(page_data)
        scores['response_time'] = perf_score
        recommendations.extend(perf_reco)
        
        # 4. Données structurées (15 points)
        struct_score, struct_reco = self._score_structured_data(page_data)
        scores['structured_data'] = struct_score
        recommendations.extend(struct_reco)
        
        # 5. Structure sémantique (20 points)
        sem_score, sem_reco = self._score_semantic_structure(page_data)
        scores['semantic_structure'] = sem_score
        recommendations.extend(sem_reco)
        
        # 6. Profondeur du contenu (15 points)
        depth_score, depth_reco = self._score_content_depth(page_data)
        scores['content_depth'] = depth_score
        recommendations.extend(depth_reco)
        
        # 7. Richesse en entités (10 points)
        entity_score, entity_reco = self._score_entity_richness(page_data)
        scores['entity_richness'] = entity_score
        recommendations.extend(entity_reco)
        
        # 8. Fraîcheur (5 points)
        fresh_score, fresh_reco = self._score_freshness(page_data)
        scores['freshness'] = fresh_score
        recommendations.extend(fresh_reco)
        
        # Score total
        total_score = sum(scores.values())
        grade = self._calculate_grade(total_score)
        
        return {
            'total_score': round(total_score),
            'breakdown': scores,
            'recommendations': recommendations,
            'grade': grade
        }
    
    # ========================================================================
    # CRITÈRES INDIVIDUELS
    # ========================================================================
    
    def _score_meta_description(self, page_data):
        """Score la meta description (15 points max)"""
        description = page_data.get('description', '')
        score = 0
        reco = []
        
        if not description:
            reco.append({
                'priority': 'HIGH',
                'category': 'Meta Description',
                'issue': 'Aucune meta description',
                'action': 'Ajouter une description de 120-160 caractères résumant le contenu'
            })
            return score, reco
        
        length = len(description)
        
        # Longueur optimale : 120-160 caractères
        if 120 <= length <= 160:
            score += 10
        elif 100 <= length < 120 or 160 < length <= 200:
            score += 7
            reco.append({
                'priority': 'MEDIUM',
                'category': 'Meta Description',
                'issue': f'Longueur sous-optimale ({length} caractères)',
                'action': 'Viser 120-160 caractères pour un affichage optimal'
            })
        else:
            score += 3
            reco.append({
                'priority': 'HIGH',
                'category': 'Meta Description',
                'issue': f'Longueur inappropriée ({length} caractères)',
                'action': 'Réécrire entre 120-160 caractères'
            })
        
        # Contient des mots-clés d'action
        action_words = ['découvrez', 'apprenez', 'comprenez', 'guide', 'comment', 'pourquoi']
        if any(word in description.lower() for word in action_words):
            score += 3
        
        # Évite le keyword stuffing
        words = description.lower().split()
        unique_ratio = len(set(words)) / len(words) if words else 0
        if unique_ratio > 0.7:
            score += 2
        else:
            reco.append({
                'priority': 'LOW',
                'category': 'Meta Description',
                'issue': 'Trop de répétitions de mots',
                'action': 'Varier le vocabulaire pour paraître plus naturel'
            })
        
        return score, reco
    
    def _score_h1_quality(self, page_data):
        """Score la qualité du H1 (10 points max)"""
        h1 = page_data.get('h1', '')
        score = 0
        reco = []
        
        if not h1:
            reco.append({
                'priority': 'HIGH',
                'category': 'Structure HTML',
                'issue': 'Pas de balise H1',
                'action': 'Ajouter un H1 clair et descriptif (40-70 caractères)'
            })
            return score, reco
        
        # H1 présent
        score += 5
        
        # Longueur optimale
        length = len(h1)
        if 40 <= length <= 70:
            score += 3
        elif length < 40:
            reco.append({
                'priority': 'MEDIUM',
                'category': 'H1',
                'issue': 'H1 trop court',
                'action': 'Allonger le H1 à 40-70 caractères pour plus de contexte'
            })
            score += 1
        else:
            reco.append({
                'priority': 'LOW',
                'category': 'H1',
                'issue': 'H1 trop long',
                'action': 'Raccourcir le H1 pour plus d\'impact'
            })
            score += 2
        
        # Contient une question (très bon pour GEO)
        if '?' in h1:
            score += 2
        
        return score, reco
    
    def _score_response_time(self, page_data):
        """Score le temps de réponse (10 points max)"""
        response_time = page_data.get('response_time', 0)
        score = 0
        reco = []
        
        if response_time < 0.5:
            score = 10
        elif response_time < 1.0:
            score = 7
        elif response_time < 2.0:
            score = 4
            reco.append({
                'priority': 'MEDIUM',
                'category': 'Performance',
                'issue': f'Temps de réponse lent ({response_time:.2f}s)',
                'action': 'Optimiser les images, activer la compression, utiliser un CDN'
            })
        else:
            score = 1
            reco.append({
                'priority': 'HIGH',
                'category': 'Performance',
                'issue': f'Temps de réponse très lent ({response_time:.2f}s)',
                'action': 'Audit technique urgent : serveur, cache, optimisation assets'
            })
        
        return score, reco
    
    def _score_structured_data(self, page_data):
        """Score les données structurées JSON-LD (15 points max)"""
        html_content = page_data.get('html_content', '')
        score = 0
        reco = []
        
        if not html_content:
            # Mode dégradé sans HTML
            reco.append({
                'priority': 'INFO',
                'category': 'Données Structurées',
                'issue': 'HTML non disponible pour analyse',
                'action': 'Activer la capture HTML dans le scraper pour analyse complète'
            })
            return score, reco
        
        soup = BeautifulSoup(html_content, 'html.parser')
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        
        if not json_ld_scripts:
            reco.append({
                'priority': 'HIGH',
                'category': 'Données Structurées',
                'issue': 'Aucune donnée structurée JSON-LD',
                'action': 'Ajouter au minimum Organization, Article ou WebPage schema'
            })
            return score, reco
        
        # Présence de JSON-LD
        score += 8
        
        # Types de schemas détectés
        schemas_found = []
        for script in json_ld_scripts:
            content = script.string
            if content:
                if '@type' in content:
                    if 'Organization' in content: schemas_found.append('Organization')
                    if 'Article' in content: schemas_found.append('Article')
                    if 'FAQPage' in content: schemas_found.append('FAQPage')
                    if 'HowTo' in content: schemas_found.append('HowTo')
                    if 'Product' in content: schemas_found.append('Product')
                    if 'Person' in content: schemas_found.append('Person')
        
        # Bonus pour schemas avancés
        if 'FAQPage' in schemas_found or 'HowTo' in schemas_found:
            score += 5
        elif len(schemas_found) >= 2:
            score += 3
        else:
            score += 2
            reco.append({
                'priority': 'MEDIUM',
                'category': 'Données Structurées',
                'issue': 'Schema basique seulement',
                'action': 'Ajouter FAQPage ou HowTo pour maximiser les citations LLM'
            })
        
        return score, reco
    
    def _score_semantic_structure(self, page_data):
        """Score la structure sémantique (20 points max) - formats préférés des LLMs"""
        html_content = page_data.get('html_content', '')
        score = 0
        reco = []
        
        if not html_content:
            # Mode dégradé : on peut quand même scorer le H1
            if page_data.get('h1'):
                score += 5
            reco.append({
                'priority': 'INFO',
                'category': 'Structure Sémantique',
                'issue': 'HTML non disponible pour analyse détaillée',
                'action': 'Activer la capture HTML dans le scraper pour scoring complet'
            })
            return score, reco
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. Hiérarchie de titres (H2, H3)
        h2_count = len(soup.find_all('h2'))
        h3_count = len(soup.find_all('h3'))
        
        if h2_count >= 3:
            score += 5
        elif h2_count >= 1:
            score += 3
            reco.append({
                'priority': 'MEDIUM',
                'category': 'Structure Sémantique',
                'issue': 'Peu de sous-titres H2',
                'action': 'Ajouter plus de H2 pour structurer le contenu (min 3)'
            })
        else:
            reco.append({
                'priority': 'HIGH',
                'category': 'Structure Sémantique',
                'issue': 'Aucun sous-titre H2',
                'action': 'Structurer le contenu avec des H2 clairs'
            })
        
        # 2. Listes (ul, ol) - adorées par les LLMs
        ul_count = len(soup.find_all('ul'))
        ol_count = len(soup.find_all('ol'))
        total_lists = ul_count + ol_count
        
        if total_lists >= 3:
            score += 5
        elif total_lists >= 1:
            score += 3
            reco.append({
                'priority': 'MEDIUM',
                'category': 'Structure Sémantique',
                'issue': 'Peu de listes',
                'action': 'Convertir des paragraphes en listes pour faciliter l\'extraction'
            })
        else:
            reco.append({
                'priority': 'HIGH',
                'category': 'Structure Sémantique',
                'issue': 'Aucune liste',
                'action': 'Ajouter des listes à puces ou numérotées (très important pour GEO)'
            })
        
        # 3. Tableaux
        tables = len(soup.find_all('table'))
        if tables > 0:
            score += 3
        
        # 4. Strong/Bold pour mettre en avant
        strong_count = len(soup.find_all(['strong', 'b']))
        if strong_count >= 5:
            score += 2
        
        # 5. Définitions (dt, dd) ou blockquotes
        definitions = len(soup.find_all(['dt', 'dd', 'blockquote']))
        if definitions > 0:
            score += 2
        
        # 6. Navigation claire (breadcrumbs)
        if soup.find('nav', {'aria-label': re.compile(r'breadcrumb', re.I)}):
            score += 3
        
        return score, reco
    
    def _score_content_depth(self, page_data):
        """Score la profondeur du contenu (15 points max)"""
        html_content = page_data.get('html_content', '')
        score = 0
        reco = []
        
        if not html_content:
            return score, reco
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extraire le texte visible
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        words = text.split()
        word_count = len(words)
        
        # Longueur du contenu
        if word_count >= 1500:
            score += 8
        elif word_count >= 800:
            score += 6
            reco.append({
                'priority': 'LOW',
                'category': 'Contenu',
                'issue': 'Contenu moyen',
                'action': 'Enrichir le contenu à 1500+ mots pour plus d\'autorité'
            })
        elif word_count >= 300:
            score += 3
            reco.append({
                'priority': 'MEDIUM',
                'category': 'Contenu',
                'issue': 'Contenu léger',
                'action': 'Développer le contenu à 800+ mots minimum'
            })
        else:
            reco.append({
                'priority': 'HIGH',
                'category': 'Contenu',
                'issue': 'Contenu insuffisant',
                'action': 'Créer un contenu substantiel (minimum 500 mots)'
            })
        
        # Paragraphes
        paragraphs = soup.find_all('p')
        if len(paragraphs) >= 5:
            score += 4
        elif len(paragraphs) >= 3:
            score += 2
        
        # Liens externes (citations)
        external_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http') and urlparse(page_data.get('url', '')).netloc not in href:
                external_links.append(href)
        
        if len(external_links) >= 3:
            score += 3
        elif len(external_links) >= 1:
            score += 1
        else:
            reco.append({
                'priority': 'MEDIUM',
                'category': 'Contenu',
                'issue': 'Pas de liens externes',
                'action': 'Citer des sources autoritaires (études, stats, références)'
            })
        
        return score, reco
    
    def _score_entity_richness(self, page_data):
        """Score la richesse en entités nommées (10 points max)"""
        html_content = page_data.get('html_content', '')
        title = page_data.get('title', '')
        description = page_data.get('description', '')
        
        score = 0
        reco = []
        
        full_text = f"{title} {description} {html_content}"
        
        # Détection simple d'entités (majuscules, patterns)
        # Personnes (M., Mme, Dr, etc.)
        persons = len(re.findall(r'\b(?:M\.|Mme|Dr|Professor|CEO)\s+[A-Z][a-z]+', full_text))
        
        # Organisations (SA, SARL, Ltd, Inc, etc.)
        orgs = len(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:SA|SARL|Ltd|Inc|Corp|GmbH)\b', full_text))
        
        # Lieux (ville + pays patterns)
        places = len(re.findall(r'\b(?:Paris|Lyon|Marseille|Londres|New York|Tokyo|Berlin)\b', full_text))
        
        # Dates
        dates = len(re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b', full_text))
        
        # Nombres/Stats (très important pour GEO)
        numbers = len(re.findall(r'\b\d+%|\b\d+\s+(?:millions?|milliards?|personnes?|utilisateurs?|clients?)\b', full_text, re.I))
        
        entity_count = persons + orgs + places + dates + numbers
        
        if entity_count >= 10:
            score = 10
        elif entity_count >= 5:
            score = 7
        elif entity_count >= 2:
            score = 4
            reco.append({
                'priority': 'MEDIUM',
                'category': 'Entités',
                'issue': 'Peu d\'entités détectées',
                'action': 'Ajouter des noms propres, chiffres clés, dates, lieux pour plus de contexte'
            })
        else:
            reco.append({
                'priority': 'HIGH',
                'category': 'Entités',
                'issue': 'Manque d\'entités',
                'action': 'Enrichir avec des données factuelles : stats, noms, dates, lieux'
            })
        
        return score, reco
    
    def _score_freshness(self, page_data):
        """Score la fraîcheur du contenu (5 points max)"""
        last_modified = page_data.get('last_modified', '')
        score = 0
        reco = []
        
        if not last_modified:
            reco.append({
                'priority': 'LOW',
                'category': 'Fraîcheur',
                'issue': 'Date de modification inconnue',
                'action': 'Ajouter balise <meta property="article:modified_time">'
            })
            return score, reco
        
        try:
            # Parser différents formats de date
            if isinstance(last_modified, str):
                # Essayer plusieurs formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%a, %d %b %Y %H:%M:%S GMT']:
                    try:
                        mod_date = datetime.strptime(last_modified.split('+')[0].strip(), fmt)
                        break
                    except:
                        continue
                else:
                    return score, reco
            else:
                mod_date = last_modified
            
            days_old = (datetime.now() - mod_date).days
            
            if days_old <= 90:  # 3 mois
                score = 5
            elif days_old <= 180:  # 6 mois
                score = 3
            elif days_old <= 365:  # 1 an
                score = 2
                reco.append({
                    'priority': 'LOW',
                    'category': 'Fraîcheur',
                    'issue': 'Contenu de plus de 6 mois',
                    'action': 'Mettre à jour le contenu avec des informations récentes'
                })
            else:
                score = 0
                reco.append({
                    'priority': 'MEDIUM',
                    'category': 'Fraîcheur',
                    'issue': f'Contenu ancien ({days_old} jours)',
                    'action': 'Révision complète nécessaire pour rester pertinent'
                })
        except:
            pass
        
        return score, reco
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _calculate_grade(self, score):
        """Convertit le score en note"""
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'
    
    def get_score_explanation(self):
        """Retourne l'explication du scoring"""
        return {
            'criteria': [
                {
                    'name': 'Meta Description',
                    'weight': 15,
                    'description': 'Présence et qualité de la meta description (120-160 caractères optimal)'
                },
                {
                    'name': 'Qualité H1',
                    'weight': 10,
                    'description': 'Présence et pertinence du H1 principal (40-70 caractères)'
                },
                {
                    'name': 'Performance',
                    'weight': 10,
                    'description': 'Temps de réponse du serveur (<1s optimal)'
                },
                {
                    'name': 'Données Structurées',
                    'weight': 15,
                    'description': 'Présence de JSON-LD (Organization, FAQPage, HowTo, etc.)'
                },
                {
                    'name': 'Structure Sémantique',
                    'weight': 20,
                    'description': 'Hiérarchie (H2/H3), listes, tableaux - formats préférés des LLMs'
                },
                {
                    'name': 'Profondeur du Contenu',
                    'weight': 15,
                    'description': 'Longueur (800+ mots), paragraphes, liens externes vers sources'
                },
                {
                    'name': 'Richesse en Entités',
                    'weight': 10,
                    'description': 'Présence d\'entités : noms, lieux, dates, chiffres clés'
                },
                {
                    'name': 'Fraîcheur',
                    'weight': 5,
                    'description': 'Date de dernière modification (<3 mois optimal)'
                }
            ],
            'grades': {
                'A+': {'range': '90-100', 'description': 'Excellente optimisation GEO'},
                'A': {'range': '80-89', 'description': 'Très bonne optimisation GEO'},
                'B': {'range': '70-79', 'description': 'Bonne optimisation GEO'},
                'C': {'range': '60-69', 'description': 'Optimisation GEO moyenne'},
                'D': {'range': '50-59', 'description': 'Optimisation GEO faible'},
                'F': {'range': '0-49', 'description': 'Optimisation GEO insuffisante'}
            }
        }
