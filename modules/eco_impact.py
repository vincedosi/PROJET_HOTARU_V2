# =============================================================================
# ECO-SCORE - HOTARU
# Calculatrice d'impact carbone : réduction des tokens = sobriété numérique
# =============================================================================

import re
import json

from bs4 import BeautifulSoup

from core.scraping import fetch_page

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

    def __init__(self, timeout=15):
        self.timeout = timeout
        self._enc = None

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
            html = fetch_page(url, timeout=self.timeout)
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
            html = fetch_page(url, timeout=self.timeout)
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


# =============================================================================
# UI STREAMLIT (Calculatrice + Méthodologie)
# =============================================================================

def render_eco_tab():
    """Onglet principal Eco-Score : Calculatrice + Méthodologie."""
    import streamlit as st

    st.markdown(
        "<p class='section-title'>Eco-Score</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='home-tagline' style='margin-bottom:1.5rem;'>"
        "Sobriété numérique — Prouver que l'optimisation des données (JSON-LD, llms.txt) réduit la consommation d'énergie des IA.</p>",
        unsafe_allow_html=True,
    )

    tab_calc, tab_methodo = st.tabs(["Calculatrice d'Impact", "Méthodologie Scientifique"])

    with tab_calc:
        _render_calculatrice()
    with tab_methodo:
        _render_methodologie()


# Jours cumulés en fin de mois (année non bissextile)
_DAYS_CUMUL_MOIS = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]


def _render_calculatrice():
    import streamlit as st
    import plotly.graph_objects as go

    with st.sidebar:
        st.markdown("### Paramètres du Site")
        total_pages = st.slider(
            "Nombre de pages du catalogue",
            min_value=1,
            max_value=100_000,
            value=1_000,
            step=100,
            key="eco_total_pages",
        )
        daily_views = st.slider(
            "Vues IA/Crawls par jour par page",
            min_value=1,
            max_value=1_000,
            value=100,
            step=10,
            key="eco_daily_views",
        )

    st.markdown("#### AIO Efficiency : Levier de Sobriété Numérique")
    url = st.text_input(
        "URL du site web",
        placeholder="https://www.example.com",
        key="eco_impact_url",
    )
    if st.button("Simuler l'économie Carbone", type="primary", use_container_width=True, key="eco_btn"):
        if not url or not url.strip():
            st.warning("Veuillez saisir une URL.")
            return
        with st.spinner("Analyse du poids cognitif en cours..."):
            calc = AIOImpactCalculator()
            result = calc.calculate(url.strip(), total_pages=total_pages, daily_views_per_page=daily_views)

        if result.get("error"):
            st.error(result["error"])
            return

        # Conversion pour les Big Numbers (formule fournie)
        co2_total_grammes = result["co2_saved"] * total_pages * daily_views * 365
        co2_total_tonnes = co2_total_grammes / 1_000_000
        vols_pny = round(co2_total_tonnes, 1)
        annual_kwh = result["kwh_saved"] * total_pages * daily_views * 365
        annual_mwh = annual_kwh / 1_000

        st.markdown("---")
        st.markdown("##### Impact Global (annuel)")

        col1, col2, col3 = st.columns(3)
        with col1:
            if co2_total_tonnes >= 1:
                st.metric("CO₂ économisé / an", f"{co2_total_tonnes:.2f} t", delta="Économie annuelle")
            else:
                st.metric("CO₂ économisé / an", f"{co2_total_grammes:,.0f} g", delta="Économie annuelle")
        with col2:
            st.metric("Énergie économisée", f"{annual_mwh:.2f} MWh", delta="Économie annuelle")
        with col3:
            st.metric("Équivalent Vols Paris-NY", f"✈️ {vols_pny}", delta="Économie annuelle")

        st.markdown("##### Métriques par page (une vue)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tokens économisés", f"{result['tokens_saved']:,}")
        with col2:
            st.metric("Énergie épargnée (kWh)", f"{result['kwh_saved']:.6f}")
        with col3:
            st.metric("gCO₂ évité", f"{result['co2_saved']:.2f}")

        # Projection sur l'année : cumul mois par mois
        tokens_per_day = result["tokens_saved"] * total_pages * daily_views
        kwh_per_day = result["kwh_saved"] * total_pages * daily_views
        co2_per_day = result["co2_saved"] * total_pages * daily_views

        mois = list(range(1, 13))
        cumul_tokens = [tokens_per_day * d for d in _DAYS_CUMUL_MOIS]
        cumul_kwh = [kwh_per_day * d for d in _DAYS_CUMUL_MOIS]
        cumul_gco2 = [co2_per_day * d for d in _DAYS_CUMUL_MOIS]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=mois,
                y=cumul_tokens,
                name="Tokens économisés (cumul)",
                line=dict(color="#3498db", width=2),
                yaxis="y",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=mois,
                y=cumul_kwh,
                name="kWh économisés (cumul)",
                line=dict(color="#27ae60", width=2),
                yaxis="y2",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=mois,
                y=cumul_gco2,
                name="gCO₂ évité (cumul)",
                line=dict(color="#e74c3c", width=2),
                yaxis="y3",
            )
        )
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=60, r=80, t=50, b=50),
            height=400,
            font=dict(size=11),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis=dict(title="Mois", dtick=1),
            yaxis=dict(
                title=dict(text="Tokens (cumul)", font=dict(color="#3498db")),
                side="left",
                anchor="x",
                tickfont=dict(color="#3498db"),
            ),
            yaxis2=dict(
                title=dict(text="kWh (cumul)", font=dict(color="#27ae60")),
                side="right",
                anchor="x",
                overlaying="y",
                tickfont=dict(color="#27ae60"),
            ),
            yaxis3=dict(
                title=dict(text="gCO₂ (cumul)", font=dict(color="#e74c3c")),
                side="right",
                overlaying="y2",
                tickfont=dict(color="#e74c3c"),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Comparatif : Poids cognitif (par page)")
        fig_bar = go.Figure(
            data=[
                go.Bar(name="Poids cognitif actuel (brut)", x=["Tokens"], y=[result["tokens_dirty"]], marker_color="#e74c3c"),
                go.Bar(name="Poids cognitif HOTARU (optimisé)", x=["Tokens"], y=[result["tokens_clean"]], marker_color="#27ae60"),
            ]
        )
        fig_bar.update_layout(
            barmode="group",
            template="plotly_white",
            margin=dict(l=40, r=40, t=40, b=40),
            height=320,
            font=dict(size=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis_title="",
            yaxis_title="Nombre de tokens",
        )
        st.plotly_chart(fig_bar, use_container_width=True)


def _render_methodologie():
    import streamlit as st

    st.markdown("#### Méthodologie Scientifique")
    st.markdown("---")

    st.markdown("""
## La Physique de la Donnée : Pourquoi structurer, c'est optimiser

### 1. Le Problème : L'Obésité Numérique des LLMs

Les modèles de langage (GPT-4, Claude, Gemini) ne « lisent » pas comme des humains. Ils **tokenisent** le code HTML brut avant de l'analyser.

**Un site web classique non optimisé contient :**
- Des balises HTML complexes (nav, footer, aside)
- Des scripts JavaScript inline
- Du CSS embarqué
- Des menus, breadcrumbs, widgets

**Conséquence :** Pour extraire une information simple (prix, horaires, localisation), un LLM doit traiter **des milliers de tokens parasites**.

**Impact direct :**

*Plus de tokens = Plus de cycles GPU = Plus d'électricité = Plus de CO₂*

---

### 2. La Solution HOTARU : Signal vs. Bruit

HOTARU structure l'information via :
- **JSON-LD** (données sémantiques au format Schema.org)
- **Extraction du contenu principal** (titre, H1, paragraphes clés)
- **Suppression du bruit** (scripts, CSS, navigation)

**Résultat :** L'IA accède directement au "signal pur" sans traiter le superflu.

---

### 3. La Formule d'Impact Carbone

Notre calculatrice mesure la **réduction de charge cognitive** des serveurs d'inférence.

$$
\\Delta_{CO_2} = (Tokens_{Bruts} - Tokens_{Optimisés}) \\times E_{Token} \\times I_{Carbone}
$$

**Avec :**
- **Tokens** : Unité de lecture des LLMs (~0,75 mot)
- **E_Token** : Énergie pour traiter 1000 tokens en inférence (NVIDIA H100)
- **I_Carbone** : Intensité carbone du mix électrique mondial

---

### 4. Ordres de Grandeur & Honnêteté Scientifique

#### **Impact par requête (estimation) :**
- Site non optimisé : ~5000 tokens
- Site HOTARU : ~500 tokens
- **Économie : 4500 tokens**

**En CO₂ :**
- 4500 tokens ≈ 0,0001 kWh (H100)
- × 475g CO₂/kWh (mix mondial)
- = **~0,05g CO₂ économisé par requête**

#### **Pour économiser 1 kg de CO₂ :**
- Il faut **20 000 requêtes optimisées**
- Équivalent à **~250 emails** (4g CO₂/email)

#### **Donc oui, l'impact individuel est faible.**

**MAIS :**
- Si 10 000 entreprises optimisent leurs sites
- Et que chacune reçoit 1000 requêtes IA/jour
- **Économie annuelle : ~180 tonnes de CO₂**
- Équivalent à **~30 vols Paris-New York**

---

### 5. Méthodologie & Limites

#### **Sources des coefficients :**
- **E_Token (0,0004 kWh/1000 tokens)** : Basé sur les benchmarks NVIDIA H100 pour l'inférence GPT-4 (2023)
- **I_Carbone (475g CO₂/kWh)** : Mix électrique mondial moyen (IEA 2024)

#### **Ce que nous NE mesurons PAS :**
- L'empreinte carbone de **l'entraînement** des modèles (90% de l'impact total de l'IA)
- Les variations selon le **data center** (France = 60g CO₂/kWh, Pologne = 700g)
- Les variations selon le **modèle** (GPT-4 ≠ Claude ≠ Gemini)

#### **Mise à jour :**
Nous révisons nos coefficients **trimestriellement** selon les nouvelles publications scientifiques.

---

### Conclusion : Sobriété Numérique à l'Échelle

HOTARU ne va pas "sauver la planète" à lui seul.

**Mais :**
- Multiplié par des milliers d'organisations
- Cet effet marginal devient un **standard de sobriété**
- Une infrastructure AI plus efficiente = Moins de serveurs nécessaires

**En structurant vos données, vous :**
1. Gagnez en visibilité IA (GEO)
2. Réduisez la charge des data centers
3. Participez à un écosystème numérique plus sobre

---

#### 📊 Méthodologie complète & sources
Documentation technique disponible sur demande.

#### 💬 Questions ou corrections ?
Feedback scientifique bienvenu.
""")
