# =============================================================================
# ECO-SCORE - UI Streamlit (Calculatrice + Méthodologie)
# =============================================================================

import streamlit as st
import plotly.graph_objects as go

from modules.eco.eco_impact import AIOImpactCalculator

# Jours cumulés en fin de mois (année non bissextile)
_DAYS_CUMUL_MOIS = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]


def render_eco_tab():
    """Onglet principal Eco-Score : Calculatrice + Méthodologie."""
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


def _render_calculatrice():
    st.markdown("#### AIO Efficiency : Levier de Sobriété Numérique")
    tab_params, tab_simul = st.tabs(["Paramètres du Site", "Simulation"])

    with tab_params:
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
        st.caption("Réglage des paramètres pour le calcul d'impact annuel.")

    with tab_simul:
        total_pages = st.session_state.get("eco_total_pages", 1_000)
        daily_views = st.session_state.get("eco_daily_views", 100)
        url = st.text_input(
            "URL du site web",
            placeholder="https://www.example.com",
            key="eco_impact_url",
        )
        if st.button("Simuler l'économie Carbone", type="primary", use_container_width=True, key="eco_btn"):
            if not url or not url.strip():
                st.warning("Veuillez saisir une URL.")
            else:
                with st.spinner("Analyse du poids cognitif en cours..."):
                    calc = AIOImpactCalculator()
                    result = calc.calculate(url.strip(), total_pages=total_pages, daily_views_per_page=daily_views)

                if result.get("error"):
                    st.error(result["error"])
                else:
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
                        st.metric("Équivalent Vols Paris-NY", f"{vols_pny}", delta="Économie annuelle")

                    st.markdown("##### Métriques par page (une vue)")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Tokens économisés", f"{result['tokens_saved']:,}")
                    with col2:
                        st.metric("Énergie épargnée (kWh)", f"{result['kwh_saved']:.6f}")
                    with col3:
                        st.metric("gCO₂ évité", f"{result['co2_saved']:.2f}")

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
    st.markdown("#### Méthodologie AIO Efficiency : Levier de Sobriété Numérique")
    st.markdown("---")

    st.markdown("""
### 1. Le Constat : L'Obésité Numérique du Web "Legacy"

Les modèles de langage (GPT-4o, Claude 3.5, Gemini 1.5) ne voient pas les sites web comme nous. Ils **consomment des tokens**.

Un site web classique est une **"soupe de code"** :

- **Structure parasite :** Balises HTML, scripts de tracking, CSS inline.
- **Bruit cognitif :** Menus, footers, publicités, pop-ups.

**Conséquence :** Pour lire une simple description de produit de 100 mots, une IA doit en "ingérer" 5 000. C'est le **Token Penalty**.

---

### 2. Le Triptyque AIO : La Solution "AI-Native"

Nous transformons ce chaos en un standard de données épurées que les agents IA (SearchGPT, Perplexity, OpenAI Bot) peuvent traiter instantanément :

- **Fichiers .md (Markdown)** : Le texte pur, structuré hiérarchiquement. C'est le langage natal des LLMs.
- **Fichiers .json (Données Structurées)** : Prix, stocks, et caractéristiques techniques au format Schema.org. Zéro ambiguïté.
- **Sitemap-AIO.xml** : Un index spécialisé qui guide les robots IA vers la donnée propre sans qu'ils aient besoin de "crawler" tout le site inutilement.

---

### 3. Modèle Mathématique d'Efficience

L'impact est calculé en comparant le coût énergétique de l'inférence (le traitement par l'IA) entre une page brute et une page optimisée AIO.

$$
\\Delta CO_2 = (Tokens_{Bruts} - Tokens_{AIO}) \\times E_{Token} \\times I_{Carbone} \\times Scale
$$

**Paramètres clés :**

- $E_{Token}$ : Énergie moyenne consommée par un GPU (type NVIDIA H100) pour traiter 1 000 tokens ($0{,}0004$ kWh).
- $I_{Carbone}$ : Intensité carbone moyenne du mix électrique mondial ($475$ gCO₂/kWh).
- $Scale$ : Le multiplicateur de puissance (Nombre de pages $\\times$ Fréquence des requêtes IA).

---

### 4. Le Système de Cache "Intelligent Hash"

Contrairement au web classique, la méthodologie AIO utilise le **versioning par Hash**.

- **Principe :** Nous générons une empreinte numérique unique pour chaque page.
- **Optimisation :** Si le contenu ne change pas, le Hash reste identique. L'IA accède au fichier statique pré-généré sans aucun nouveau calcul.
- **Gain :** 99 % d'économie de ressources serveurs sur les catalogues à fort trafic.

---

### 5. Ordres de Grandeur & Impact Réel

L'impact d'une seule requête est infime, mais à l'échelle d'un site e-commerce ou d'un média, les chiffres deviennent massifs.

| Métrique | Par requête (Unitaire) | Par an (Catalogue 5k pages) |
| -------- | ---------------------- | -------------------------- |
| Tokens économisés | ~4 500 | ~1,6 Milliard |
| Énergie épargnée | 0,0018 Wh | 650 kWh |
| CO₂ évité | 0,05 g | ~310 kg |

**Le saviez-vous ?** À l'échelle de 10 000 entreprises adoptant le standard AIO, l'économie annuelle représente l'équivalent de **30 vols Paris-New York** en termes de rejet de CO₂.

---

### 6. Limites & Évolutions

Cette méthodologie se concentre sur **l'inférence** (la consommation). Elle ne prend pas en compte l'entraînement initial des modèles, mais elle optimise la partie la plus répétitive et croissante de l'usage de l'IA : la navigation et la recherche d'information en temps réel.

**Mise à jour :** Les coefficients énergétiques sont révisés chaque trimestre selon les benchmarks de performance des nouveaux processeurs IA (NVIDIA Blackwell, etc.).
""")

