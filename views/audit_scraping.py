import json
import re

import streamlit as st
from bs4 import BeautifulSoup

def _render_log_box(logs):
    """Affiche les logs techniques dans un bloc monospace."""
    if not logs:
        st.info("Aucun log disponible")
        return
    content = "\n".join(logs[-200:])
    st.markdown(
        "<div style='font-family:SFMono-Regular,Menlo,monospace;font-size:0.75rem;"
        "background:#0f172a;color:#e5e7eb;padding:14px;border-radius:6px;"
        "max-height:300px;overflow:auto;white-space:pre-wrap;line-height:1.5;'>"
        f"{content}</div>",
        unsafe_allow_html=True,
    )


def _detect_spa_indicators(html: str, soup: BeautifulSoup):
    """Détecte tous les indicateurs SPA possibles."""
    html_l = html.lower()
    indicators = []
    
    # Patterns dans le texte
    text_patterns = {
        "react": "React (texte)",
        "__next": "Next.js (texte)",
        "nuxt": "Nuxt (texte)",
        "_nuxt": "Nuxt (texte)",
        "vue": "Vue (texte)",
        "angular": "Angular (texte)",
        "data-reactroot": "React (data-reactroot)",
        '<div id="root">': "React (div#root)",
        '<div id="app">': "Vue (div#app)",
    }
    
    for pattern, label in text_patterns.items():
        if pattern in html_l:
            indicators.append({"type": "texte", "signal": label, "pattern": pattern})
    
    # Scripts avec src
    for script in soup.find_all("script", src=True):
        src = script["src"].lower()
        if "_nuxt" in src:
            indicators.append({"type": "script", "signal": "Nuxt", "pattern": f"src={script['src'][:60]}..."})
        elif "__next" in src:
            indicators.append({"type": "script", "signal": "Next.js", "pattern": f"src={script['src'][:60]}..."})
        elif any(p in src for p in ["react", "vue", "angular"]):
            indicators.append({"type": "script", "signal": "Framework JS", "pattern": f"src={script['src'][:60]}..."})
    
    # Links modulepreload
    for link in soup.find_all("link", rel=True):
        rel = " ".join(link["rel"]).lower() if isinstance(link["rel"], list) else link["rel"].lower()
        href = link.get("href", "").lower()
        
        if "modulepreload" in rel and (".js" in href or "_nuxt" in href):
            indicators.append({"type": "link", "signal": "ES Module", "pattern": f"modulepreload {href[:50]}..."})
    
    # Scripts type=module
    module_scripts = soup.find_all("script", type="module")
    if module_scripts:
        indicators.append({"type": "module", "signal": f"{len(module_scripts)} script(s) ES module", "pattern": "type=module"})
    
    return indicators


def render_scraping_debug_tab():
    """Onglet de debug Scraping/JSON-LD ultra-complet."""

    st.markdown(
        '<p class="section-title">DIAGNOSTIC SCRAPING & JSON-LD</p>',
        unsafe_allow_html=True,
    )

    # ── Choix moteur (V1 / V2) ─────────────────────────────────────────
    if "scraping_engine" not in st.session_state:
        st.session_state["scraping_engine"] = "v2"
    _engine_label = st.radio(
        "⚙️ Moteur de scraping",
        options=[
            "🚀 V2 — Crawl4AI (rapide, Markdown LLM-ready)",
            "🔧 V1 — Selenium (robuste, sites protégés)",
        ],
        index=0 if st.session_state.get("scraping_engine") == "v2" else 1,
        horizontal=True,
        key="scraping_engine_radio_audit_scraping",
        help=(
            "V2 = Playwright async, x5 plus rapide, génère du Markdown propre pour l'IA. "
            "V1 = cascade requests→Selenium, pour les sites qui bloquent (Cloudflare, anti-bot)."
        ),
    )
    use_v2 = str(_engine_label).startswith("🚀")
    st.session_state["scraping_engine"] = "v2" if use_v2 else "v1"
    st.caption(f"Moteur actif : {'🚀 Crawl4AI V2' if use_v2 else '🔧 Selenium V1'}")
    
    st.markdown(
        "<p style='color:#64748b;margin-bottom:20px;'>Analyse complète du scraping, "
        "détection SPA, et extraction JSON-LD avec logs détaillés.</p>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-container">', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        url = st.text_input(
            "URL À DIAGNOSTIQUER",
            placeholder="https://lamarinerecrute.gouv.fr/",
            key="scraping_debug_url",
        )
    with col2:
        force_selenium = st.checkbox(
            "Utiliser Selenium",
            value=False,
            help="Activer Selenium pour les sites SPA ou protégés (plus lent).",
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ===== CONTENEUR POUR LES LOGS EN TEMPS RÉEL =====
    log_placeholder = st.empty()

    if st.button(
        "LANCER LE DIAGNOSTIC COMPLET",
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

        # ===== LISTE POUR ACCUMULER LES LOGS =====
        logs: list[str] = []

        def add_log(message: str):
            """Callback appelé par SmartScraper pour chaque log."""
            logs.append(message)
            # Mise à jour en temps réel
            with log_placeholder:
                _render_log_box(logs)

        # ===== INITIALISATION AVEC CALLBACK =====
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">01 / INITIALISATION & DÉTECTION SPA</p>',
            unsafe_allow_html=True,
        )

        scraper = None
        try:
            # CRITIQUE : On crée une classe temporaire pour passer le callback AVANT __init__
            add_log("Initialisation du scraper...")

            engine = st.session_state.get("scraping_engine", "v2")
            if engine == "v2":
                from core.scraping_v2 import HotaruScraperV2 as Scraper
                scraper = Scraper(
                    start_urls=[target_url],
                    max_urls=1,
                    log_callback=add_log,
                )
                add_log(f"Domaine : {scraper.domain}")
                add_log("Selenium : N/A (Playwright natif en V2)")
                add_log("Driver : N/A (Playwright)")
            else:
                from core.scraping import SmartScraper as Scraper
                scraper = Scraper(
                    start_urls=[target_url],
                    max_urls=1,
                    use_selenium=force_selenium,
                    log_callback=add_log,
                )
                add_log(f"Domaine : {scraper.domain}")
                add_log(f"Selenium forcé : {'OUI' if force_selenium else 'NON'}")
                add_log(f"Selenium activé : {'OUI' if getattr(scraper, 'use_selenium', False) else 'NON'}")
                add_log(f"Driver : {'Initialisé' if getattr(scraper, 'driver', None) else 'Non initialisé'}")
            
        except Exception as e:
            st.error(f"Erreur d'initialisation : {e}")
            import traceback
            st.code(traceback.format_exc())
            return

        # Affichage des métriques d'init
        col_init1, col_init2, col_init3 = st.columns(3)
        with col_init1:
            st.metric("Domaine", scraper.domain)
        with col_init2:
            selenium_status = "N/A (V2)" if st.session_state.get("scraping_engine") == "v2" else ("ACTIVÉ" if getattr(scraper, "use_selenium", False) else "DÉSACTIVÉ")
            st.metric("Mode Selenium", selenium_status)
        with col_init3:
            driver_type = "Non initialisé"
            if getattr(scraper, "driver", None):
                driver_type = "Opérationnel"
            st.metric("Driver", driver_type)

        # Analyse SPA AVANT le scraping
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Analyse des indicateurs SPA (HTML brut)**")
        
        try:
            import requests
            resp = requests.get(target_url, timeout=5)
            html_brut = resp.text
            soup_brut = BeautifulSoup(html_brut, "html.parser")
            spa_indicators = _detect_spa_indicators(html_brut, soup_brut)
            
            if spa_indicators:
                st.success(f"{len(spa_indicators)} indicateur(s) SPA détecté(s)")
                for ind in spa_indicators[:5]:
                    st.markdown(f"- **{ind['signal']}** ({ind['type']}) : `{ind['pattern']}`")
                if len(spa_indicators) > 5:
                    st.markdown(f"_... et {len(spa_indicators) - 5} autre(s)_")
            else:
                st.warning("Aucun indicateur SPA détecté")
        except Exception as e:
            st.error(f"Erreur analyse préliminaire : {e}")

        # ===== SCRAPING =====
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">02 / SCRAPING DE LA PAGE</p>',
            unsafe_allow_html=True,
        )

        data = None
        try:
            with st.spinner("⏳ Scraping en cours..."):
                if st.session_state.get("scraping_engine") == "v2":
                    results, _summary = scraper.run_analysis()
                    data = results[0] if results else None
                else:
                    data = scraper.get_page_details(target_url)
        except Exception as e:
            st.error(f"Erreur scraping : {e}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            if getattr(scraper, "driver", None):
                try:
                    scraper.driver.quit()
                except Exception:
                    pass

        if not data:
            st.error("Aucune donnée renvoyée")
            return

        # Résultats scraping
        col_scrap1, col_scrap2, col_scrap3, col_scrap4 = st.columns(4)
        with col_scrap1:
            st.metric("Titre", data.get("title", "N/A")[:30] + "...")
        with col_scrap2:
            st.metric("Temps", f"{data.get('response_time', 0):.2f}s")
        with col_scrap3:
            st.metric("Liens", len(data.get("links", [])))
        with col_scrap4:
            st.metric("HTML", f"{len(data.get('html_content', '')) // 1024}KB")

        # ===== JSON-LD =====
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">03 / DIAGNOSTIC JSON-LD</p>',
            unsafe_allow_html=True,
        )

        has_structured = bool(data.get("has_structured_data"))
        jsonld_blocks = data.get("json_ld") or []

        col_ld1, col_ld2, col_ld3 = st.columns(3)
        with col_ld1:
            status_ld = "OUI" if has_structured else "NON"
            st.metric("JSON-LD DÉTECTÉ", status_ld)
        with col_ld2:
            st.metric("BLOCS JSON-LD", len(jsonld_blocks))
        with col_ld3:
            st.metric("H2", data.get("h2_count", 0))

        if jsonld_blocks:
            st.markdown("<br>", unsafe_allow_html=True)
            st.success(f"{len(jsonld_blocks)} bloc(s) JSON-LD extrait(s) !")
            
            block_tab_labels = []
            for i, block in enumerate(jsonld_blocks, 1):
                block_type = "N/A"
                if isinstance(block, dict):
                    block_type = block.get("@type", "Unknown")
                elif isinstance(block, list):
                    block_type = f"Array[{len(block)}]"
                block_tab_labels.append(f"Bloc {i} — {block_type}")
            block_tabs = st.tabs(block_tab_labels) if block_tab_labels else []
            for i, block in enumerate(jsonld_blocks):
                if i < len(block_tabs):
                    with block_tabs[i]:
                        st.json(block)
        else:
            st.warning("Aucun JSON-LD trouvé")

        # ===== STRUCTURE HTML =====
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">04 / STRUCTURE HTML & SCRIPTS</p>',
            unsafe_allow_html=True,
        )

        html = data.get("html_content") or ""
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script")

        type_counts = {}
        ld_scripts_in_html = []
        
        for s in scripts:
            t = (s.get("type") or "").strip()
            key = t or "(aucun type)"
            type_counts[key] = type_counts.get(key, 0) + 1
            
            if "ld+json" in key.lower():
                raw = (s.string or s.get_text(strip=True) or "").strip()
                ld_scripts_in_html.append({
                    "type": key,
                    "length": len(raw),
                    "content": raw,
                })

        col_html1, col_html2 = st.columns(2)
        
        with col_html1:
            st.markdown("**Types de `<script>`**")
            for t, count in sorted(type_counts.items(), key=lambda kv: kv[1], reverse=True):
                icon = "JSON-LD" if "ld+json" in t.lower() else "Script"
                st.markdown(f"{icon} `{t}` → **{count}**")
        
        with col_html2:
            st.markdown("**Structure**")
            st.markdown(f"H1: {1 if soup.find('h1') else 0}")
            st.markdown(f"H2: {data.get('h2_count', 0)}")
            st.markdown(f"Listes: {data.get('lists_count', 0)}")
            st.markdown(f"Images: {len(soup.find_all('img'))}")

        if ld_scripts_in_html:
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"{len(ld_scripts_in_html)} script(s) JSON-LD dans HTML")
            
            script_tab_labels = [f"Script #{i} — {s['length']} chars" for i, s in enumerate(ld_scripts_in_html, 1)]
            script_tabs = st.tabs(script_tab_labels) if script_tab_labels else []
            for i, script_data in enumerate(ld_scripts_in_html):
                if i < len(script_tabs):
                    with script_tabs[i]:
                        try:
                            parsed = json.loads(script_data["content"])
                            st.json(parsed)
                        except json.JSONDecodeError as e:
                            st.error(f"Erreur JSON : {e}")
                            st.code(script_data["content"][:500])

        # ===== DIAGNOSTIC =====
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">05 / DIAGNOSTIC & RECOMMANDATIONS</p>',
            unsafe_allow_html=True,
        )

        if has_structured and jsonld_blocks:
            st.success(
                f"**Parfait !** {len(jsonld_blocks)} bloc(s) JSON-LD extrait(s)."
            )
        elif ld_scripts_in_html and not jsonld_blocks:
            st.error(
                "**Problème d'extraction !** Scripts JSON-LD présents mais non extraits."
            )
        elif not ld_scripts_in_html and not jsonld_blocks and not scraper.use_selenium:
            st.warning(
                "**Active 'FORCER SELENIUM'** pour les sites SPA."
            )
        elif not ld_scripts_in_html and not jsonld_blocks and scraper.use_selenium:
            st.error(
                "**Aucun JSON-LD trouvé** même avec Selenium. Le site n'en a peut-être pas."
            )
        
        # ===== LOGS =====
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">06 / LOGS TECHNIQUES</p>',
            unsafe_allow_html=True,
        )
        
        _render_log_box(logs)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#64748b;font-size:0.85rem;text-align:center;'>"
            f"Total : {len(logs)} ligne(s) de log"
            "</p>",
            unsafe_allow_html=True,
        )