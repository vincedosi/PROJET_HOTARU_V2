import json
import re

import streamlit as st
from bs4 import BeautifulSoup

from core.scraping import SmartScraper


def _render_log_box(logs):
    """Affiche les logs techniques dans un bloc monospace."""
    if not logs:
        return
    content = "\n".join(logs[-200:])
    st.markdown(
        "<div style='font-family:SFMono-Regular,Menlo,monospace;font-size:0.7rem;"
        "background:#0f172a;color:#e5e7eb;padding:12px;border-radius:4px;"
        "max-height:260px;overflow:auto;white-space:pre-wrap;'>"
        f"{content}</div>",
        unsafe_allow_html=True,
    )


def _detect_frontend_tech(html: str):
    """Heuristiques simples pour détecter la techno front (utile pour JSON-LD)."""
    html_l = html.lower()
    signals = []
    patterns = {
        "react": "React",
        "__next": "Next.js",
        "next.js": "Next.js",
        "nuxt": "Nuxt",
        "_nuxt": "Nuxt",
        "vue": "Vue",
        "angular": "Angular",
        "data-reactroot": "React (data-reactroot)",
    }
    for needle, label in patterns.items():
        if needle in html_l:
            signals.append(label)
    return sorted(set(signals))


def render_scraping_debug_tab():
    """Onglet de debug Scraping/JSON-LD pour une URL unique."""

    st.markdown(
        '<p class="section-title">01 / SCRAPING & JSON-LD DEBUG</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-container">', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        url = st.text_input(
            "URL A DIAGNOSTIQUER",
            placeholder="https://www.example.com/",
            key="scraping_debug_url",
        )
    with col2:
        use_selenium = st.checkbox(
            "FORCER MODE SELENIUM (SPA/React)",
            value=False,
            help="Active le rendu JS complet (Selenium) même si le site n'est pas détecté comme SPA.",
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    log_placeholder = st.empty()

    if st.button(
        "LANCER LE DIAGNOSTIC SCRAPING",
        type="primary",
        use_container_width=True,
        key="scraping_debug_run",
    ):
        if not url:
            st.warning("Veuillez saisir une URL.")
            return

        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        logs: list[str] = []

        def add_log(message: str):
            logs.append(message)
            with log_placeholder:
                _render_log_box(logs)

        try:
            scraper = SmartScraper([target_url], max_urls=1, use_selenium=use_selenium)
            scraper.log_callback = add_log
        except Exception as e:
            st.error(f"Erreur d'initialisation du SmartScraper : {e}")
            return

        add_log(f"🌐 Domaine: {scraper.domain}")
        add_log(f"⚙️ Mode Selenium auto: {'ON' if scraper.use_selenium else 'OFF'}")

        data = None
        try:
            with st.spinner("Scraping de la page et analyse JSON-LD..."):
                data = scraper.get_page_details(target_url)
        except Exception as e:
            st.error(f"Erreur lors du scraping : {e}")
        finally:
            # Nettoyage éventuel de Selenium pour éviter les fuites de drivers
            if getattr(scraper, "driver", None):
                try:
                    scraper.driver.quit()
                except Exception:
                    pass

        if not data:
            st.error(
                "Aucune donnée renvoyée par le scraper (HTTP non-200 ou erreur critique). "
                "Consulte les logs techniques ci-dessus."
            )
            return

        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">02 / DIAGNOSTIC JSON-LD</p>',
            unsafe_allow_html=True,
        )

        has_structured = bool(data.get("has_structured_data"))
        jsonld_blocks = data.get("json_ld") or []

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                "JSON-LD DÉTECTÉ",
                "OUI" if has_structured else "NON",
            )
        with c2:
            st.metric("NOMBRE DE BLOCS JSON-LD", len(jsonld_blocks))
        with c3:
            st.metric("H2 SUR LA PAGE", data.get("h2_count", 0))

        html = data.get("html_content") or ""
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script")

        ld_scripts = []
        type_counts = {}
        for s in scripts:
            t = (s.get("type") or "").strip()
            key = t or "(aucun type)"
            type_counts[key] = type_counts.get(key, 0) + 1
            if "ld+json" in key.lower():
                raw = (s.string or s.get_text(strip=True) or "").strip()
                ld_scripts.append(
                    {
                        "type": key,
                        "length": len(raw),
                        "preview": raw[:800],
                    }
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">03 / SCRIPTS & STRUCTURE</p>',
            unsafe_allow_html=True,
        )

        c4, c5 = st.columns(2)
        with c4:
            st.markdown("**Types de `<script>` détectés (brut)**")
            for t, count in sorted(
                type_counts.items(), key=lambda kv: kv[1], reverse=True
            ):
                st.markdown(
                    f"- `{t}` → **{count}** script(s)",
                    unsafe_allow_html=False,
                )
        with c5:
            tech = _detect_frontend_tech(html)
            st.markdown("**Signaux techno front (heuristiques)**")
            if tech:
                for label in tech:
                    st.markdown(f"- {label}")
            else:
                st.markdown(
                    "_Aucun signal fort de framework SPA (React/Vue/Next/Nuxt) détecté._"
                )

        if ld_scripts:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<p class="section-title">04 / BLOCS JSON-LD BRUTS</p>',
                unsafe_allow_html=True,
            )
            for i, block in enumerate(ld_scripts, 1):
                with st.expander(
                    f"Bloc {i} — type=`{block['type']}` — {block['length']} caractères",
                    expanded=False,
                ):
                    try:
                        parsed = json.loads(block["preview"])
                        st.json(parsed)
                    except Exception:
                        st.code(block["preview"], language="json")

        else:
            st.info(
                "Aucun `<script type=\"application/ld+json\">` détecté dans le HTML brut. "
                "Si le site est une SPA, vérifie que le mode Selenium est activé et que le JSON-LD "
                "est bien injecté côté client."
            )

