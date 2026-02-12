# =============================================================================
# JSON-LD Analyzer - Interface Streamlit
# Analyse de sites pour regrouper les pages par structure similaire.
# Logique métier dans services/jsonld_service.py (réutilisable par API).
# =============================================================================

import json
import time
from urllib.parse import urlparse

from services.jsonld_service import (
    extract_dom_structure,
    cluster_pages,
    get_cluster_url_pattern,
    name_cluster_with_mistral,
    generate_optimized_jsonld,
    build_jsonld_graph_html,
    FLEXIBLE_TAGS,
)


# (Logique extraite dans services/jsonld_service.py)


def render_jsonld_analyzer_tab():
    """Onglet Analyse JSON-LD : crawl + clustering, affichage résultats texte."""
    import streamlit as st
    from core.scraping import SmartScraper

    st.markdown(
        "<p class='section-title'>ANALYSE JSON-LD</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='home-tagline' style='margin-bottom:1.5rem; color:#0f172a;'>"
        "Détection des types de pages par structure DOM et pattern d'URL. Clustering intelligent (seuil 85%).</p>",
        unsafe_allow_html=True,
    )

    tab_new, tab_load = st.tabs(["Nouvelle analyse", "Charger depuis Sheets"])
    with tab_load:
        from core.database import AuditDatabase
        from core.session_keys import get_current_user_email

        user_email = get_current_user_email() or ""
        db = AuditDatabase()
        sites = db.list_jsonld_sites(user_email) if user_email and db.client else []

        if not sites:
            st.caption("Aucune donnée enregistrée pour votre compte. Lancez une analyse puis enregistrez dans Google Sheets.")
        else:
            opt_labels = [f"{s['site_url']} — {s['workspace']}" for s in sites]
            sel_idx = st.selectbox("Sélectionner un site enregistré", range(len(opt_labels)), format_func=lambda i: opt_labels[i], key="jsonld_load_site")
            if st.button("CHARGER DEPUIS GOOGLE SHEETS", type="secondary", use_container_width=True, key="jsonld_load_btn"):
                s = sites[sel_idx]
                models = db.load_jsonld_models(user_email, site_url=s["site_url"])
                models = [m for m in models if (m.get("workspace") or "").strip() == (s.get("workspace") or "").strip()]
                if not models:
                    st.warning("Aucun modèle trouvé pour ce site et workspace.")
                else:
                    domain = urlparse(s["site_url"]).netloc or "site"
                    cluster_labels = []
                    cluster_urls = []
                    cluster_dom = []
                    cluster_jsonld = []
                    total_pages = 0
                    for m in models:
                        cluster_labels.append({"model_name": m.get("model_name") or "Cluster", "schema_type": m.get("recommended_schema") or "WebPage"})
                        urls_str = m.get("sample_urls") or "[]"
                        try:
                            urls = json.loads(urls_str) if isinstance(urls_str, str) else urls_str
                        except json.JSONDecodeError:
                            try:
                                raw = __import__("base64").b64decode(urls_str)
                                urls = json.loads(__import__("zlib").decompress(raw).decode())
                            except Exception:
                                urls = []
                        cluster_urls.append(urls if isinstance(urls, list) else [])
                        cluster_dom.append(db._decompress_from_sheet(m.get("dom_structure") or "") or {})
                        cluster_jsonld.append(db._decompress_from_sheet(m.get("existing_jsonld") or ""))
                        total_pages += m.get("page_count", 0)
                    st.session_state["jsonld_analyzer_results"] = {
                        "site_url": s["site_url"],
                        "domain": domain,
                        "total_pages": total_pages,
                        "cluster_labels": cluster_labels,
                        "cluster_urls": cluster_urls,
                        "cluster_dom_structures": cluster_dom,
                        "cluster_jsonld": cluster_jsonld,
                        "logs": [],
                        "loaded_from_sheet": True,
                    }
                    st.success("Données chargées.")
                    st.rerun()

    with tab_new:
        url_input = st.text_input(
            "URL du site à analyser",
            placeholder="https://www.example.com",
            key="jsonld_analyzer_url",
            help="Page d'accueil ou point d'entrée du site.",
        )
        max_pages = st.slider(
            "Nombre de pages à crawler",
            min_value=50,
            max_value=500,
            value=150,
            step=10,
            key="jsonld_analyzer_max_pages",
            help="~1-2 s/page (mode requests). Clustering < 30 s pour 500 pages.",
        )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            launch = st.button("LANCER L'ANALYSE", type="primary", use_container_width=True, key="jsonld_analyzer_btn")
        with col_btn2:
            if "jsonld_analyzer_results" in st.session_state and st.button("EFFACER LES RÉSULTATS", use_container_width=True, key="jsonld_clear_btn"):
                del st.session_state["jsonld_analyzer_results"]
                if "jsonld_analyzer_crawl_results" in st.session_state:
                    del st.session_state["jsonld_analyzer_crawl_results"]
                for k in list(st.session_state.keys()):
                    if k.startswith("optimized_jsonld_"):
                        del st.session_state[k]
                st.rerun()

        if launch:
            if not url_input or not url_input.strip():
                st.warning("Veuillez entrer une URL.")
                return

            url = url_input.strip()
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            logs = []
            def add_log(msg):
                logs.append(msg)

            progress_placeholder = st.empty()
            log_placeholder = st.container()

            with progress_placeholder:
                bar = st.progress(0.0, "Initialisation...")

            try:
                scr = SmartScraper(
                    [url],
                    max_urls=max_pages,
                    use_selenium=False,
                    log_callback=add_log,
                )
                res, crawl_meta = scr.run_analysis(
                    progress_callback=lambda msg, val: bar.progress(min(val, 1.0), msg),
                )
            except Exception as e:
                progress_placeholder.empty()
                err_msg = str(e)[:300] if e else "Erreur inconnue"
                st.error(f"Erreur crawl : {err_msg}")
                st.caption("Vérifiez l'URL, la connexion réseau et l'accessibilité du site.")
                return

            progress_placeholder.empty()

            if not res:
                st.warning("Aucune page récupérée. Vérifiez l'URL et réessayez.")
                if logs:
                    st.markdown("**Logs du crawl**")
                    st.text("\n".join(logs[-100:]))
                return

            # Clustering
            with st.spinner("Clustering des pages..."):
                clusters = cluster_pages(res)

            # Nommage Mistral (étape 3)
            cluster_labels = []
            try:
                mistral_key = st.secrets["mistral"]["api_key"]
            except Exception:
                mistral_key = None

            if mistral_key:
                mistral_fail_count = 0
                for i, cluster_indices in enumerate(clusters):
                    with st.spinner(f"Nommage Mistral — cluster {i + 1}/{len(clusters)}..."):
                        out = name_cluster_with_mistral(mistral_key, res, cluster_indices)
                    if out:
                        cluster_labels.append(out)
                    else:
                        cluster_labels.append({"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"})
                        mistral_fail_count += 1
                if mistral_fail_count > 0:
                    st.warning(f"Mistral : {mistral_fail_count} cluster(s) sans nom (timeout ou API occupée). Réessayez.")
            else:
                cluster_labels = [
                    {"model_name": f"Cluster {i + 1}", "schema_type": "—"}
                    for i in range(len(clusters))
                ]
                st.info("Clé API Mistral manquante. Configurez st.secrets['mistral']['api_key'] pour activer.")

            domain = urlparse(url).netloc or "site"
            site_url = url
            cluster_urls = [[res[idx]["url"] for idx in indices] for indices in clusters]
            # DOM + JSON-LD par cluster (première page) pour le graphe et le panneau
            cluster_dom_structures = []
            cluster_jsonld = []
            for indices in clusters:
                page = res[indices[0]]
                dom = page.get("dom_structure") or extract_dom_structure(page.get("html_content") or "")
                cluster_dom_structures.append(dom)
                jld = page.get("json_ld") or []
                cluster_jsonld.append(jld[0] if jld else None)
            st.session_state["jsonld_analyzer_results"] = {
                "site_url": site_url,
                "domain": domain,
                "total_pages": len(res),
                "cluster_labels": cluster_labels,
                "cluster_urls": cluster_urls,
                "cluster_dom_structures": cluster_dom_structures,
                "cluster_jsonld": cluster_jsonld,
                "logs": logs,
            }
            st.session_state["jsonld_analyzer_crawl_results"] = res
            st.rerun()

    # Affichage des résultats (depuis session_state, persistant après rerun)
    if "jsonld_analyzer_results" in st.session_state:
        import streamlit.components.v1 as components

        data = st.session_state["jsonld_analyzer_results"]
        domain = data["domain"]
        total_pages = data["total_pages"]
        cluster_labels = data["cluster_labels"]
        cluster_urls = data["cluster_urls"]
        cluster_dom = data.get("cluster_dom_structures", [])
        cluster_jsonld = data.get("cluster_jsonld", [])
        logs = data.get("logs", [])
        num_clusters = len(cluster_labels)

        st.markdown("---")
        st.markdown("<p style='color:#0f172a; font-weight:700; font-size:1rem; margin:0 0 0.5rem 0;'>Vue d'ensemble</p>", unsafe_allow_html=True)
        st.markdown(f"- **Site :** {domain}")
        st.markdown(f"- **Pages analysées :** {total_pages}")
        st.markdown(f"- **Modèles détectés :** {num_clusters}")
        if num_clusters == 0:
            st.warning("Aucun cluster détecté. Le site peut avoir une structure très homogène.")
        elif num_clusters > 25:
            st.caption("Astuce : beaucoup de clusters peuvent indiquer une structure variée ou un seuil ajustable.")

        st.markdown("---")
        if num_clusters == 0:
            st.info("Lancez une nouvelle analyse avec une URL différente ou plus de pages.")
        else:
            tab_names = ["GRAPHE", "TABLEAU", "EXPORT"] + (["Logs"] if logs else [])
            tabs = st.tabs(tab_names)
            tab_graphe, tab_tableau, tab_export = tabs[0], tabs[1], tabs[2]
            tab_logs = tabs[3] if logs else None

        if num_clusters > 0:
            with tab_graphe:
                st.markdown("<p style='color:#0f172a; font-weight:700; font-size:1rem; margin:0 0 0.5rem 0;'>Graphe interactif des clusters</p>", unsafe_allow_html=True)
                st.caption("Cliquez sur un cluster (nœud coloré) pour afficher les détails dans le panneau. Cliquez sur une URL pour l'ouvrir. Sinon, utilisez le menu déroulant.")

                # Déterminer le cluster à afficher : query param (clic graphe) > session_state > 0
                selected_cluster_idx = None
                try:
                    qp = getattr(st, "query_params", None)
                    if qp is not None and "jsonld_cluster" in qp:
                        selected_cluster_idx = int(qp["jsonld_cluster"])
                        if selected_cluster_idx >= num_clusters:
                            selected_cluster_idx = 0
                        st.session_state["jsonld_selected_cluster"] = selected_cluster_idx
                except (ValueError, TypeError, KeyError):
                    pass
                if selected_cluster_idx is None:
                    if "jsonld_selected_cluster" in st.session_state:
                        selected_cluster_idx = st.session_state["jsonld_selected_cluster"]
                    else:
                        selected_cluster_idx = 0

                options = [
                    f"{i + 1}. {(cluster_labels[i].get('model_name') or '').strip() or f'Cluster {i + 1}'} ({len(cluster_urls[i])} p.)"
                    for i in range(num_clusters)
                ]
                default_idx = selected_cluster_idx if selected_cluster_idx is not None and selected_cluster_idx < len(options) else 0

                # Layout : graphe à gauche, panneau latéral à droite
                col_graph, col_panel = st.columns([2, 1])

                with col_graph:
                    html_graph = build_jsonld_graph_html(domain, cluster_labels, cluster_urls)
                    components.html(html_graph, height=620)

                with col_panel:
                    st.markdown(
                        "<div style='background:#0f172a; color:#fff; padding:8px 12px; font-weight:700; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em;'>Détails du cluster</div>",
                        unsafe_allow_html=True,
                    )
                    sel = st.selectbox(
                        "Sélectionner un cluster", options, index=default_idx, key="jsonld_cluster_select"
                    )
                    if sel:
                        idx = options.index(sel)
                        st.session_state["jsonld_selected_cluster"] = idx
                        label = cluster_labels[idx] if idx < len(cluster_labels) else {}
                        name = (label.get("model_name") or "").strip() or f"Cluster {idx + 1}"
                        schema_type = (label.get("schema_type") or "").strip() or "—"
                        urls_in_cluster = cluster_urls[idx] if idx < len(cluster_urls) else []
                        pattern = get_cluster_url_pattern(urls_in_cluster)

                        st.markdown(f"**Modèle :** {name}")
                        st.markdown(f"**Schema.org :** `{schema_type}`")
                        st.markdown(f"**Pattern :** `{pattern}`")
                        st.markdown(f"**Pages :** {len(urls_in_cluster)}")

                        st.markdown("---")
                        col_btn1, col_btn2 = st.columns([3, 1])
                        with col_btn1:
                            st.markdown("**Génération automatique du JSON-LD optimisé :**")
                            st.caption("Mistral AI analyse la structure et génère un JSON-LD Schema.org complet avec tous les champs recommandés.")
                        with col_btn2:
                            generate_btn = st.button(
                                "GÉNÉRER",
                                type="primary",
                                use_container_width=True,
                                key=f"jsonld_generate_{idx}",
                                help="Génère le JSON-LD optimisé pour ce cluster via Mistral AI",
                            )

                        if f"optimized_jsonld_{idx}" not in st.session_state:
                            st.session_state[f"optimized_jsonld_{idx}"] = None

                        if generate_btn:
                            sample_pages = []
                            crawl_res = st.session_state.get("jsonld_analyzer_crawl_results", [])
                            for url in urls_in_cluster[:3]:
                                page_data = None
                                for p in crawl_res:
                                    if p.get("url") == url:
                                        page_data = p
                                        break
                                if page_data:
                                    sample_pages.append({
                                        "url": url,
                                        "title": page_data.get("title", ""),
                                        "h1": page_data.get("h1", ""),
                                        "description": page_data.get("description", ""),
                                        "html_snippet": (page_data.get("html_content") or "")[:5000],
                                    })

                            with st.spinner("Mistral génère le JSON-LD optimisé..."):
                                try:
                                    mistral_key = st.secrets["mistral"]["api_key"]
                                except Exception:
                                    st.error("Clé API Mistral manquante. Configurez st.secrets['mistral']['api_key'].")
                                    mistral_key = None

                                if mistral_key:
                                    dom = cluster_dom[idx] if idx < len(cluster_dom) else {}
                                    jld = cluster_jsonld[idx] if idx < len(cluster_jsonld) else None
                                    optimized, err_msg = generate_optimized_jsonld(
                                        api_key=mistral_key,
                                        schema_type=schema_type if schema_type != "—" else "WebPage",
                                        dom_structure=dom,
                                        sample_pages=sample_pages,
                                        existing_jsonld=jld,
                                        url_pattern=pattern,
                                    )
                                    if optimized:
                                        st.session_state[f"optimized_jsonld_{idx}"] = optimized
                                        st.success("✅ JSON-LD optimisé généré !")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Échec de la génération. {err_msg or 'Erreur inconnue.'}")
                                elif not sample_pages:
                                    st.warning("Résultats du crawl non disponibles (analyse chargée depuis Sheets). Lancez une nouvelle analyse.")

                        st.markdown("---")
                        col_current, col_optimized = st.columns(2)
                        with col_current:
                            st.markdown("**JSON-LD actuel**")
                            jld = cluster_jsonld[idx] if idx < len(cluster_jsonld) else None
                            if jld:
                                st.json(jld)
                            else:
                                st.warning("⚠️ Aucun JSON-LD détecté sur ces pages.")

                        with col_optimized:
                            st.markdown("**JSON-LD optimisé** ✨")
                            optimized_data = st.session_state.get(f"optimized_jsonld_{idx}")
                            if optimized_data:
                                st.json(optimized_data)
                                st.download_button(
                                    "📋 Télécharger JSON-LD",
                                    data=json.dumps(optimized_data, ensure_ascii=False, indent=2),
                                    file_name=f"jsonld_optimized_{name.lower().replace(' ', '_')[:30]}.json",
                                    mime="application/json",
                                    use_container_width=True,
                                    key=f"download_jsonld_{idx}",
                                )
                            else:
                                st.info("Cliquez sur 'GÉNÉRER' pour créer le JSON-LD optimisé.")

                        tab_dom, tab_jsonld, tab_urls, tab_actions = st.tabs(["DOM", "JSON-LD", "URLs", "Actions avancées"])
                        with tab_dom:
                            st.markdown("**Structure DOM**")
                            dom = cluster_dom[idx] if idx < len(cluster_dom) else {}
                            if dom:
                                st.json(dom)
                                # Indicateur de variabilité des balises flexibles (h2, h3)
                                if len(urls_in_cluster) > 1:
                                    cluster_doms = []
                                    if "jsonld_analyzer_crawl_results" in st.session_state:
                                        for url in urls_in_cluster:
                                            for page in st.session_state["jsonld_analyzer_crawl_results"]:
                                                if page.get("url") == url:
                                                    page_dom = page.get("dom_structure") or extract_dom_structure(page.get("html_content") or "")
                                                    cluster_doms.append(page_dom)
                                                    break
                                    if cluster_doms:
                                        variability_info = []
                                        for tag in FLEXIBLE_TAGS:
                                            counts = [d.get(tag, 0) for d in cluster_doms]
                                            if counts and max(counts) != min(counts):
                                                variability_info.append(f"{tag.upper()}: {min(counts)}-{max(counts)}")
                                        if variability_info:
                                            st.caption(f"ℹ️ **Variabilité détectée** : {' • '.join(variability_info)}")
                                            st.caption("(Normal : le contenu varie entre pages du même type)")
                            else:
                                st.caption("Non disponible.")

                        with tab_jsonld:
                            st.markdown("**JSON-LD existant**")
                            jld = cluster_jsonld[idx] if idx < len(cluster_jsonld) else None
                            if jld:
                                st.json(jld)
                            else:
                                st.caption("Aucun JSON-LD détecté.")

                        with tab_urls:
                            st.markdown("**URLs exemples**")
                            for u in urls_in_cluster[:5]:
                                st.markdown(f"- [{u}]({u})")
                            if len(urls_in_cluster) > 5:
                                st.caption(f"... et {len(urls_in_cluster) - 5} de plus.")

                        with tab_actions:
                            st.markdown("##### Fusionner avec un autre cluster")
                            st.caption(
                                "Si deux clusters représentent le même type de page (ex: 'Fiches métiers' et 'Pages emploi'), "
                                "vous pouvez les fusionner manuellement. Les pages seront regroupées et un nouveau nom pourra être généré."
                            )

                            other_clusters = [
                                (i, (cluster_labels[i].get("model_name") or f"Cluster {i + 1}").strip())
                                for i in range(num_clusters)
                                if i != idx
                            ]

                            if not other_clusters:
                                st.info("Aucun autre cluster disponible pour fusion.")
                            else:
                                merge_options = ["--- Sélectionner un cluster ---"] + [
                                    f"{i + 1}. {name} ({len(cluster_urls[i])} p.)"
                                    for i, name in other_clusters
                                ]

                                selected_merge = st.selectbox(
                                    "Fusionner le cluster actuel avec :",
                                    merge_options,
                                    key=f"merge_select_{idx}",
                                )

                                if selected_merge != merge_options[0]:
                                    target_idx = int(selected_merge.split(".")[0]) - 1

                                    col_preview, col_action = st.columns([3, 1])

                                    with col_preview:
                                        st.markdown("**Aperçu de la fusion :**")
                                        current_name = (cluster_labels[idx].get("model_name") or f"Cluster {idx + 1}").strip()
                                        target_name = (cluster_labels[target_idx].get("model_name") or f"Cluster {target_idx + 1}").strip()
                                        st.markdown(f"- **Cluster source** : {current_name} ({len(urls_in_cluster)} p.)")
                                        st.markdown(f"- **Cluster cible** : {target_name} ({len(cluster_urls[target_idx])} p.)")
                                        st.markdown(f"- **Résultat** : {len(urls_in_cluster) + len(cluster_urls[target_idx])} p. fusionnées")

                                    with col_action:
                                        if st.button(
                                            "FUSIONNER",
                                            type="primary",
                                            use_container_width=True,
                                            key=f"merge_btn_{idx}_{target_idx}",
                                        ):
                                            # ========== LOGIQUE DE FUSION ==========
                                            merged_urls = list(set(cluster_urls[idx] + cluster_urls[target_idx]))

                                            if len(cluster_urls[idx]) >= len(cluster_urls[target_idx]):
                                                merged_dom = cluster_dom[idx]
                                                merged_jsonld = cluster_jsonld[idx]
                                                base_label = cluster_labels[idx]
                                            else:
                                                merged_dom = cluster_dom[target_idx]
                                                merged_jsonld = cluster_jsonld[target_idx]
                                                base_label = cluster_labels[target_idx]

                                            new_label = base_label
                                            try:
                                                mistral_key = st.secrets["mistral"]["api_key"]
                                            except Exception:
                                                mistral_key = None

                                            if mistral_key:
                                                merged_sample_pages = []
                                                crawl_results = st.session_state.get("jsonld_analyzer_crawl_results", [])
                                                for url in merged_urls[:5]:
                                                    for page in crawl_results:
                                                        if page.get("url") == url:
                                                            merged_sample_pages.append(page)
                                                            break

                                                if merged_sample_pages:
                                                    with st.spinner("Mistral génère un nouveau nom pour le cluster fusionné..."):
                                                        renamed = name_cluster_with_mistral(
                                                            mistral_key,
                                                            merged_sample_pages,
                                                            list(range(len(merged_sample_pages))),
                                                        )
                                                        if renamed:
                                                            new_label = renamed

                                            cluster_urls[target_idx] = merged_urls
                                            cluster_dom[target_idx] = merged_dom
                                            cluster_jsonld[target_idx] = merged_jsonld
                                            cluster_labels[target_idx] = new_label

                                            del cluster_urls[idx]
                                            del cluster_dom[idx]
                                            del cluster_jsonld[idx]
                                            del cluster_labels[idx]

                                            results_data = st.session_state.get("jsonld_analyzer_results", {})
                                            results_data["cluster_urls"] = cluster_urls
                                            results_data["cluster_dom_structures"] = cluster_dom
                                            results_data["cluster_jsonld"] = cluster_jsonld
                                            results_data["cluster_labels"] = cluster_labels
                                            st.session_state["jsonld_analyzer_results"] = results_data

                                            for k in list(st.session_state.keys()):
                                                if k.startswith("optimized_jsonld_"):
                                                    del st.session_state[k]
                                            new_merged_idx = target_idx - 1 if idx < target_idx else target_idx
                                            st.session_state["jsonld_selected_cluster"] = new_merged_idx

                                            st.success(f"✅ Clusters fusionnés ! Nouveau nom : {new_label.get('model_name', 'Cluster fusionné')}")
                                            st.balloons()
                                            time.sleep(1)
                                            st.rerun()

            with tab_tableau:
                tab_labels = []
                for i in range(num_clusters):
                    label = cluster_labels[i] if i < len(cluster_labels) else {"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"}
                    name = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
                    n = len(cluster_urls[i]) if i < len(cluster_urls) else 0
                    tab_labels.append(f"{i + 1}. {name} ({n} p.)")

                cluster_tabs = st.tabs(tab_labels)

                for i, tab in enumerate(cluster_tabs):
                    with tab:
                        label = cluster_labels[i] if i < len(cluster_labels) else {"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"}
                        urls_in_cluster = cluster_urls[i] if i < len(cluster_urls) else []
                        pattern = get_cluster_url_pattern(urls_in_cluster)
                        sample = urls_in_cluster[:5]
                        name = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
                        schema_type = (label.get("schema_type") or "").strip() or "—"

                        if st.session_state.get(f"optimized_jsonld_{i}"):
                            st.markdown("✨ **JSON-LD optimisé généré**")
                        else:
                            st.markdown("⚠️ *JSON-LD optimisé non généré*")
                        st.markdown(f"**Modèle :** {name}")
                        st.markdown(f"**Schema.org type :** `{schema_type}`")
                        st.markdown(f"**Pattern d'URL :** `{pattern}`")
                        st.markdown("**URLs exemples :**")
                        for u in sample:
                            st.code(u, language=None)
                        if len(urls_in_cluster) > 5:
                            st.caption(f"... et {len(urls_in_cluster) - 5} de plus.")

            with tab_export:
                from core.database import AuditDatabase
                from core.session_keys import get_current_user_email

                st.markdown("<p style='color:#0f172a; font-weight:700; font-size:1rem; margin:0 0 0.5rem 0;'>Charger depuis Google Sheets</p>", unsafe_allow_html=True)
                _user_email = get_current_user_email() or ""
                _db = AuditDatabase()
                _sites = _db.list_jsonld_sites(_user_email) if _user_email and _db.client else []
                if _sites:
                    _opt_labels = [f"{s['site_url']} — {s['workspace']}" for s in _sites]
                    _sel_idx = st.selectbox("Site enregistré", range(len(_opt_labels)), format_func=lambda i: _opt_labels[i], key="jsonld_load_export")
                    if st.button("CHARGER DEPUIS GOOGLE SHEETS", use_container_width=True, key="jsonld_load_export_btn"):
                        _s = _sites[_sel_idx]
                        _models = _db.load_jsonld_models(_user_email, site_url=_s["site_url"])
                        _models = [m for m in _models if (m.get("workspace") or "").strip() == (_s.get("workspace") or "").strip()]
                        if _models:
                            _domain = urlparse(_s["site_url"]).netloc or "site"
                            _labels = []
                            _urls = []
                            _doms = []
                            _jlds = []
                            for i, m in enumerate(_models):
                                _labels.append({"model_name": m.get("model_name") or "Cluster", "schema_type": m.get("recommended_schema") or "WebPage"})
                                _us = m.get("sample_urls") or "[]"
                                try:
                                    _u = json.loads(_us) if isinstance(_us, str) else _us
                                except json.JSONDecodeError:
                                    try:
                                        _u = json.loads(__import__("zlib").decompress(__import__("base64").b64decode(_us)).decode())
                                    except Exception:
                                        _u = []
                                _urls.append(_u if isinstance(_u, list) else [])
                                _doms.append(_db._decompress_from_sheet(m.get("dom_structure") or "") or {})
                                _jlds.append(_db._decompress_from_sheet(m.get("existing_jsonld") or ""))
                                _opt = _db._decompress_from_sheet(m.get("optimized_jsonld") or "")
                                st.session_state[f"optimized_jsonld_{i}"] = _opt if isinstance(_opt, dict) else None
                            st.session_state["jsonld_analyzer_results"] = {
                                "site_url": _s["site_url"], "domain": _domain,
                                "total_pages": sum(m.get("page_count", 0) for m in _models),
                                "cluster_labels": _labels, "cluster_urls": _urls,
                                "cluster_dom_structures": _doms, "cluster_jsonld": _jlds,
                                "logs": [], "loaded_from_sheet": True,
                            }
                            st.success("Données chargées.")
                            st.rerun()
                        else:
                            st.warning("Aucun modèle trouvé pour ce site et workspace.")
                else:
                    st.caption("Aucune donnée enregistrée.")
                st.markdown("<p style='color:#0f172a; font-weight:700; font-size:1rem; margin:0 0 0.5rem 0;'>Enregistrer dans Google Sheets</p>", unsafe_allow_html=True)
                site_url = data.get("site_url") or f"https://{domain}"
                workspace = st.session_state.get("audit_workspace_select", "Non classé") or "Non classé"
                if workspace in ("+ Creer Nouveau", "+ Créer Nouveau", "+ Create New"):
                    workspace = "Non classé"

                models_data = []
                for i in range(num_clusters):
                    label = cluster_labels[i] if i < len(cluster_labels) else {}
                    urls_in_cluster = cluster_urls[i] if i < len(cluster_urls) else []
                    pattern = get_cluster_url_pattern(urls_in_cluster)
                    optimized = st.session_state.get(f"optimized_jsonld_{i}")
                    models_data.append({
                        "model_name": (label.get("model_name") or "").strip() or f"Cluster {i + 1}",
                        "schema_type": (label.get("schema_type") or "").strip() or "WebPage",
                        "page_count": len(urls_in_cluster),
                        "url_pattern": pattern,
                        "sample_urls": urls_in_cluster[:5],
                        "dom_structure": cluster_dom[i] if i < len(cluster_dom) else None,
                        "existing_jsonld": cluster_jsonld[i] if i < len(cluster_jsonld) else None,
                        "optimized_jsonld": optimized,
                    })

                if st.button("ENREGISTRER DANS GOOGLE SHEETS", type="primary", use_container_width=True, key="jsonld_save_btn"):
                    user_email = get_current_user_email() or ""
                    db = AuditDatabase()
                    if db.save_jsonld_models(user_email, site_url, workspace, models_data):
                        st.success("Modèles JSON-LD enregistrés dans l'onglet 'jsonld' du Google Sheet.")
                        try:
                            st.toast("Enregistrement réussi", icon="✅")
                        except Exception:
                            pass
                    else:
                        st.error("Échec de l'enregistrement. Vérifiez la config GCP (secrets) et l'URL du Sheet.")

                st.markdown("<p style='color:#0f172a; font-weight:700; font-size:1rem; margin:0 0 0.5rem 0;'>Télécharger JSON</p>", unsafe_allow_html=True)
                payload = {
                    "site_url": site_url,
                    "analyzed_at": __import__("datetime").datetime.now().isoformat() + "Z",
                    "total_pages": total_pages,
                    "models": models_data,
                }
                json_str = json.dumps(payload, ensure_ascii=False, indent=2)
                st.download_button(
                    "Télécharger le JSON complet",
                    data=json_str,
                    file_name=f"jsonld_models_{domain.replace('.', '_')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="jsonld_download_btn",
                )

        if logs and tab_logs is not None:
            with tab_logs:
                st.text("\n".join(logs[-150:]))
