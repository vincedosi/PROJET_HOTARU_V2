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
        '<p class="section-title">🔍 DIAGNOSTIC SCRAPING & JSON-LD</p>',
        unsafe_allow_html=True,
    )
    
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
            "FORCER SELENIUM",
            value=False,
            help="Force l'utilisation de Selenium même si la détection automatique ne détecte pas de SPA.",
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    log_placeholder = st.empty()

    if st.button(
        "🚀 LANCER LE DIAGNOSTIC COMPLET",
        type="primary",
        use_container_width=True,
        key="scraping_debug_run",
    ):
        if not url:
            st.warning("⚠️ Veuillez saisir une URL.")
            return

        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        logs: list[str] = []

        def add_log(message: str):
            logs.append(message)
            with log_placeholder:
                _render_log_box(logs)

        # ========== ÉTAPE 1: INITIALISATION ==========
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">01 / INITIALISATION & DÉTECTION SPA</p>',
            unsafe_allow_html=True,
        )

        try:
            scraper = SmartScraper([target_url], max_urls=1, use_selenium=force_selenium)
            scraper.log_callback = add_log
        except Exception as e:
            st.error(f"❌ Erreur d'initialisation : {e}")
            return

        # Affichage des infos d'init
        col_init1, col_init2, col_init3 = st.columns(3)
        with col_init1:
            st.metric("🌐 Domaine", scraper.domain)
        with col_init2:
            selenium_status = "✅ ACTIVÉ" if scraper.use_selenium else "❌ DÉSACTIVÉ"
            st.metric("⚙️ Mode Selenium", selenium_status)
        with col_init3:
            driver_type = "Non initialisé"
            if scraper.driver:
                driver_type = "undetected_chromedriver" if "uc" in str(type(scraper.driver)) else "Selenium standard"
            st.metric("🚗 Driver", driver_type)

        # Analyse SPA AVANT le scraping (HTML brut)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**🔎 Analyse des indicateurs SPA (HTML brut)**")
        
        try:
            import requests
            resp = requests.get(target_url, timeout=5)
            html_brut = resp.text
            soup_brut = BeautifulSoup(html_brut, "html.parser")
            spa_indicators = _detect_spa_indicators(html_brut, soup_brut)
            
            if spa_indicators:
                st.success(f"✅ {len(spa_indicators)} indicateur(s) SPA détecté(s)")
                for ind in spa_indicators[:5]:  # Limite à 5 pour ne pas surcharger
                    st.markdown(f"- **{ind['signal']}** ({ind['type']}) : `{ind['pattern']}`")
                if len(spa_indicators) > 5:
                    st.markdown(f"_... et {len(spa_indicators) - 5} autre(s)_")
            else:
                st.warning("⚠️ Aucun indicateur SPA détecté automatiquement")
                st.markdown(
                    "_Le site ne semble pas utiliser React/Vue/Nuxt/Next. "
                    "Si c'est faux, active 'FORCER SELENIUM'._"
                )
        except Exception as e:
            st.error(f"Erreur analyse préliminaire : {e}")

        # ========== ÉTAPE 2: SCRAPING ==========
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">02 / SCRAPING DE LA PAGE</p>',
            unsafe_allow_html=True,
        )

        data = None
        try:
            with st.spinner("⏳ Scraping en cours..."):
                data = scraper.get_page_details(target_url)
        except Exception as e:
            st.error(f"❌ Erreur lors du scraping : {e}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            if getattr(scraper, "driver", None):
                try:
                    scraper.driver.quit()
                except Exception:
                    pass

        if not data:
            st.error(
                "❌ Aucune donnée renvoyée (HTTP error ou exception critique). "
                "Consulte les logs ci-dessus."
            )
            return

        # Résultats du scraping
        col_scrap1, col_scrap2, col_scrap3, col_scrap4 = st.columns(4)
        with col_scrap1:
            st.metric("📄 Titre", data.get("title", "N/A")[:30] + "...")
        with col_scrap2:
            st.metric("⏱️ Temps réponse", f"{data.get('response_time', 0):.2f}s")
        with col_scrap3:
            st.metric("🔗 Liens trouvés", len(data.get("links", [])))
        with col_scrap4:
            st.metric("📐 Taille HTML", f"{len(data.get('html_content', '')) // 1024}KB")

        # ========== ÉTAPE 3: ANALYSE JSON-LD ==========
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">03 / DIAGNOSTIC JSON-LD</p>',
            unsafe_allow_html=True,
        )

        has_structured = bool(data.get("has_structured_data"))
        jsonld_blocks = data.get("json_ld") or []

        col_ld1, col_ld2, col_ld3 = st.columns(3)
        with col_ld1:
            status_ld = "✅ OUI" if has_structured else "❌ NON"
            st.metric("JSON-LD DÉTECTÉ", status_ld)
        with col_ld2:
            st.metric("BLOCS JSON-LD", len(jsonld_blocks))
        with col_ld3:
            st.metric("H2 sur la page", data.get("h2_count", 0))

        # Affichage des blocs JSON-LD
        if jsonld_blocks:
            st.markdown("<br>", unsafe_allow_html=True)
            st.success(f"✅ {len(jsonld_blocks)} bloc(s) JSON-LD extrait(s) avec succès !")
            
            for i, block in enumerate(jsonld_blocks, 1):
                block_type = "N/A"
                if isinstance(block, dict):
                    block_type = block.get("@type", "Unknown")
                elif isinstance(block, list) and len(block) > 0:
                    block_type = f"Array[{len(block)}]"
                
                with st.expander(
                    f"📦 Bloc {i} — Type: `{block_type}`",
                    expanded=(i == 1),  # Premier bloc ouvert par défaut
                ):
                    st.json(block)
        else:
            st.warning("⚠️ Aucun JSON-LD trouvé sur cette page")

        # ========== ÉTAPE 4: ANALYSE STRUCTURE HTML ==========
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">04 / STRUCTURE HTML & SCRIPTS</p>',
            unsafe_allow_html=True,
        )

        html = data.get("html_content") or ""
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script")

        # Comptage des types de scripts
        type_counts = {}
        ld_scripts_in_html = []
        
        for s in scripts:
            t = (s.get("type") or "").strip()
            key = t or "(aucun type)"
            type_counts[key] = type_counts.get(key, 0) + 1
            
            # Chercher les scripts JSON-LD
            if "ld+json" in key.lower():
                raw = (s.string or s.get_text(strip=True) or "").strip()
                ld_scripts_in_html.append({
                    "type": key,
                    "length": len(raw),
                    "content": raw,
                })

        col_html1, col_html2 = st.columns(2)
        
        with col_html1:
            st.markdown("**📜 Types de `<script>` détectés**")
            for t, count in sorted(type_counts.items(), key=lambda kv: kv[1], reverse=True):
                icon = "🎯" if "ld+json" in t.lower() else "📄"
                st.markdown(f"{icon} `{t}` → **{count}** script(s)")
        
        with col_html2:
            st.markdown("**🎨 Éléments de structure**")
            st.markdown(f"📌 **H1:** {1 if soup.find('h1') else 0}")
            st.markdown(f"📌 **H2:** {data.get('h2_count', 0)}")
            st.markdown(f"📌 **Listes:** {data.get('lists_count', 0)}")
            st.markdown(f"📌 **Images:** {len(soup.find_all('img'))}")

        # Scripts JSON-LD trouvés dans le HTML
        if ld_scripts_in_html:
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"ℹ️ {len(ld_scripts_in_html)} script(s) JSON-LD trouvé(s) dans le HTML")
            
            for i, script_data in enumerate(ld_scripts_in_html, 1):
                with st.expander(
                    f"Script JSON-LD #{i} — {script_data['length']} caractères",
                    expanded=False,
                ):
                    try:
                        parsed = json.loads(script_data["content"])
                        st.json(parsed)
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Erreur de parsing JSON : {e}")
                        st.code(script_data["content"][:500], language="json")

        # ========== ÉTAPE 5: DIAGNOSTIC & RECOMMANDATIONS ==========
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">05 / DIAGNOSTIC & RECOMMANDATIONS</p>',
            unsafe_allow_html=True,
        )

        # Logique de diagnostic
        if has_structured and jsonld_blocks:
            st.success(
                "✅ **Tout fonctionne correctement !**\n\n"
                f"Le scraper a extrait {len(jsonld_blocks)} bloc(s) JSON-LD. "
                "Les données structurées sont bien détectées."
            )
        elif ld_scripts_in_html and not jsonld_blocks:
            st.error(
                "❌ **Problème d'extraction !**\n\n"
                f"Des scripts JSON-LD existent dans le HTML ({len(ld_scripts_in_html)} trouvé(s)) "
                "mais le scraper ne les a pas extraits correctement.\n\n"
                "**Solutions :**\n"
                "- Vérifie que le parsing JSON ne plante pas (erreur de format)\n"
                "- Consulte les logs techniques ci-dessus pour voir l'erreur"
            )
        elif not ld_scripts_in_html and not jsonld_blocks and not scraper.use_selenium:
            st.warning(
                "⚠️ **Site SPA sans Selenium activé**\n\n"
                "Aucun JSON-LD trouvé dans le HTML brut. Si le site est une SPA "
                "(React/Vue/Nuxt/Next), le JSON-LD est probablement injecté par JavaScript.\n\n"
                "**Solutions :**\n"
                "- ✅ Active 'FORCER SELENIUM' et relance le diagnostic\n"
                "- Le JSON-LD devrait apparaître après le rendu JavaScript"
            )
        elif not ld_scripts_in_html and not jsonld_blocks and scraper.use_selenium:
            st.error(
                "❌ **JSON-LD introuvable même avec Selenium**\n\n"
                "Selenium est activé mais aucun JSON-LD n'a été trouvé.\n\n"
                "**Causes possibles :**\n"
                "- Le site n'a tout simplement pas de JSON-LD\n"
                "- Le JSON-LD est chargé par AJAX après un certain délai\n"
                "- Il y a un blocage anti-bot\n\n"
                "**Solutions :**\n"
                "- Vérifie manuellement dans le navigateur (DevTools → Elements → cherche 'ld+json')\n"
                "- Augmente le délai d'attente dans le code (actuellement 2s après détection)\n"
                "- Vérifie les logs Selenium ci-dessus pour des erreurs de timeout"
            )
        
        # ========== LOGS FINAUX ==========
        st.markdown('<div class="zen-divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="section-title">06 / LOGS TECHNIQUES</p>',
            unsafe_allow_html=True,
        )
        
        _render_log_box(logs)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#64748b;font-size:0.85rem;text-align:center;'>"
            "💡 Astuce : Les logs montrent le détail du scraping, "
            "les timeouts, et les erreurs JavaScript éventuelles."
            "</p>",
            unsafe_allow_html=True,
        )