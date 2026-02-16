# =============================================================================
# JSON-LD Analyzer - Interface Streamlit
# Analyse de sites pour regrouper les pages par structure similaire.
# Logique métier dans services/jsonld_service.py (réutilisable par API).
# =============================================================================

import io
import json
import re
import time
import zipfile
from urllib.parse import urlparse

from services.jsonld_service import (
    extract_dom_structure,
    cluster_pages,
    get_cluster_url_pattern,
    name_cluster_with_mistral,
    suggest_cluster_merges_with_mistral,
    generate_optimized_jsonld,
    validate_jsonld_schema,
    build_jsonld_graph_html,
    FLEXIBLE_TAGS,
)


# (Logique extraite dans services/jsonld_service.py)


def _create_jsonld_zip(cluster_labels: list, cluster_urls: list, domain: str, get_optimized) -> bytes:
    """
    Crée un fichier ZIP contenant tous les JSON-LD optimisés.
    get_optimized(i) retourne le JSON-LD du cluster i ou None.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = f"""JSON-LD EXPORT - {domain}
========================================

JSON-LD Schema.org optimisés pour chaque type de page détecté sur {domain}.

Structure : XX_nom_cluster.json (XX = numéro)
Généré le {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        zf.writestr("README.txt", readme)
        for i in range(len(cluster_labels)):
            opt = get_optimized(i)
            if opt:
                name = (cluster_labels[i].get("model_name") or f"Cluster {i+1}").strip()
                safe_name = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
                filename = f"{i+1:02d}_{safe_name}.json"
                zf.writestr(filename, json.dumps(opt, ensure_ascii=False, indent=2))
        manifest = {
            "export_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "domain": domain,
            "total_clusters": len(cluster_labels),
            "exported_count": sum(1 for i in range(len(cluster_labels)) if get_optimized(i)),
            "clusters": [
                {
                    "id": i + 1,
                    "name": (cluster_labels[i].get("model_name") or f"Cluster {i+1}").strip(),
                    "schema_type": cluster_labels[i].get("schema_type", "WebPage"),
                    "page_count": len(cluster_urls[i]) if i < len(cluster_urls) else 0,
                    "has_jsonld": bool(get_optimized(i)),
                }
                for i in range(len(cluster_labels))
            ],
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    zip_buffer.seek(0)
    return zip_buffer.read()


def render_jsonld_analyzer_tab():
    """Onglet Analyse JSON-LD : crawl + clustering, affichage résultats texte."""
    import streamlit as st
    from core.scraping import SmartScraper

    st.markdown(
        "<p class='section-title'>VUE ENSEMBLE</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='home-tagline' style='margin-bottom:1rem; color:#0f172a;'>"
        "Détection des types de pages par structure DOM et pattern d'URL. Clustering intelligent (seuil ajustable).</p>",
        unsafe_allow_html=True,
    )

    st.caption("Chargement / sauvegarde : barre en haut → Choix du workspace, Choix de la sauvegarde → VALIDER ou SAUVEGARDER.")
    st.markdown("---")

    tab_load, tab_new = st.tabs(["Charger (rappel)", "Nouvelle analyse"])
    with tab_load:
        st.info("Utilisez la barre en haut de l'application : **Choix de la sauvegarde** puis **VALIDER** pour charger une sauvegarde. La sauvegarde s'applique à tout le dashboard (Audit GEO + JSON-LD).")

    with tab_new:
        url_input = st.text_input(
            "URL du site à analyser",
            placeholder="https://www.example.com",
            key="jsonld_analyzer_url",
            help="Page d'accueil ou point d'entrée du site.",
        )
        max_pages = st.slider(
            "Nombre de pages à crawler",
            min_value=1,
            max_value=10000,
            value=150,
            step=10,
            key="jsonld_analyzer_max_pages",
            help="~1-2 s/page (mode requests). De 1 à 10 000 pages (palier 10).",
        )
        cluster_threshold = st.slider(
            "Seuil de similarité pour le clustering (%)",
            min_value=70,
            max_value=98,
            value=85,
            step=1,
            key="jsonld_analyzer_threshold",
            help="Plus le seuil est élevé, plus les pages doivent être similaires pour être regroupées. 85 % = par défaut. 70 % = plus de regroupement (moins de clusters). 95 % = plus strict (plus de clusters).",
        ) / 100.0

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
                clusters = cluster_pages(res, threshold=cluster_threshold)

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
        st.markdown("<p class='section-title' style='margin-bottom:1rem;'>Vue d'ensemble</p>", unsafe_allow_html=True)
        col_site, col_pages, col_clusters = st.columns(3)
        with col_site:
            st.markdown(
                f'<div class="zen-metric" style="padding:1rem;"><div class="zen-metric-value" style="font-size:1.1rem; word-break:break-all;">{domain[:40]}{"…" if len(domain) > 40 else ""}</div>'
                '<div class="zen-metric-label">Site analysé</div></div>',
                unsafe_allow_html=True,
            )
        with col_pages:
            st.markdown(
                f'<div class="zen-metric"><div class="zen-metric-value">{total_pages}</div>'
                '<div class="zen-metric-label">Pages analysées</div></div>',
                unsafe_allow_html=True,
            )
        with col_clusters:
            st.markdown(
                f'<div class="zen-metric"><div class="zen-metric-value">{num_clusters}</div>'
                '<div class="zen-metric-label">Modèles détectés</div></div>',
                unsafe_allow_html=True,
            )
        if num_clusters == 0:
            st.warning("Aucun cluster détecté. Le site peut avoir une structure très homogène.")
        elif num_clusters > 25:
            st.caption("Astuce : beaucoup de clusters peuvent indiquer une structure variée ou un seuil ajustable.")

        st.markdown("---")
        if num_clusters == 0:
            st.info("Lancez une nouvelle analyse avec une URL différente ou plus de pages.")
        else:
            tab_names = ["VUE ENSEMBLE", "TABLEAU", "EXPORT", "FUSION"] + (["Logs"] if logs else [])
            tabs = st.tabs(tab_names)
            tab_graphe, tab_tableau, tab_export, tab_fusion = tabs[0], tabs[1], tabs[2], tabs[3]
            tab_logs = tabs[4] if logs else None

        if num_clusters > 0:
            with tab_graphe:
                st.markdown("<p style='color:#0f172a; font-weight:700; font-size:1rem; margin:0 0 0.5rem 0;'>Vue d'ensemble</p>", unsafe_allow_html=True)
                st.caption("Cliquez sur un nœud (modèle/cluster) dans le graphe pour le sélectionner, ou utilisez le menu « Détails du cluster ». Vous verrez le JSON-LD actuel et le JSON-LD optimisé (si généré). Clic sur une URL = ouverture dans un nouvel onglet.")

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
                # Synchroniser le selectbox avec le cluster sélectionné (ex. clic sur le graphe) pour que "Détails du cluster" se mette à jour
                if default_idx < len(options):
                    st.session_state["jsonld_cluster_select"] = options[default_idx]

                # Layout : graphe à gauche, panneau latéral à droite
                col_graph, col_panel = st.columns([2, 1])

                with col_graph:
                    html_graph = build_jsonld_graph_html(domain, cluster_labels, cluster_urls)
                    components.html(html_graph, height=620)

                with col_panel:
                    st.markdown(
                        "<div style='background:#0f172a; color:#fff; padding:10px 14px; font-weight:700; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.08em;'>Détails du cluster</div>",
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

                        st.markdown(
                            f'<p style="margin:0.25rem 0; font-size:0.9rem;"><strong>Modèle</strong> {name}</p>'
                            f'<p style="margin:0.25rem 0; font-size:0.85rem; color:#64748b;"><strong>Schema.org</strong> <code>{schema_type}</code></p>'
                            f'<p style="margin:0.25rem 0; font-size:0.85rem; color:#64748b;"><strong>Pattern</strong> <code>{pattern}</code></p>'
                            f'<p style="margin:0.25rem 0; font-size:0.85rem;"><strong>Pages</strong> {len(urls_in_cluster)}</p>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("---")

                        # JSON-LD actuel (modèle/template) et JSON-LD optimisé — visibles au clic sur le nœud
                        st.markdown("**JSON-LD actuel (modèle / template)**")
                        jld = cluster_jsonld[idx] if idx < len(cluster_jsonld) else None
                        if jld:
                            st.json(jld)
                        else:
                            st.caption("Aucun JSON-LD détecté sur ces pages.")
                        st.markdown("---")
                        st.markdown("**JSON-LD optimisé** (si généré)")
                        optimized_data = st.session_state.get(f"optimized_jsonld_{idx}")
                        if optimized_data:
                            st.json(optimized_data)
                            validation_result = validate_jsonld_schema(optimized_data)
                            if validation_result["valid"]:
                                if validation_result["warnings"]:
                                    st.caption(validation_result["message"])
                                else:
                                    st.success(validation_result["message"])
                            else:
                                st.error(validation_result["message"])
                            st.download_button(
                                "Télécharger JSON-LD",
                                data=json.dumps(optimized_data, ensure_ascii=False, indent=2),
                                file_name=f"jsonld_optimized_{name.lower().replace(' ', '_')[:30]}.json",
                                mime="application/json",
                                use_container_width=True,
                                key=f"download_jsonld_{idx}",
                            )
                        else:
                            st.caption("Cliquez sur GÉNÉRER ci-dessous pour créer le JSON-LD optimisé.")
                        st.markdown("---")

                        col_btn1, col_btn2 = st.columns([3, 1])
                        with col_btn1:
                            st.markdown("**Génération automatique du JSON-LD optimisé :**")
                            st.caption("Mistral AI analyse la structure et génère un JSON-LD Schema.org complet.")
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
                                        st.success(" JSON-LD optimisé généré !")
                                        st.rerun()
                                    else:
                                        st.error(f" Échec de la génération. {err_msg or 'Erreur inconnue.'}")
                                elif not sample_pages:
                                    st.warning("Résultats du crawl non disponibles (analyse chargée depuis Sheets). Lancez une nouvelle analyse.")

                        st.markdown("---")
                        tab_dom, tab_jsonld, tab_urls = st.tabs(["DOM", "JSON-LD", "URLs"])
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
                                            st.caption(f"**Variabilité détectée** : {' • '.join(variability_info)}")
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

            with tab_fusion:
                st.markdown(
                    '<div style="background:#f8fafc; border:1px solid #e2e8f0; padding:1rem 1.25rem; margin-bottom:1rem;">'
                    "<p style='font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; color:#0f172a; margin:0 0 0.5rem 0;'>"
                    "Fusion manuelle des clusters</p>"
                    "<p style='font-size:0.85rem; color:#64748b; margin:0;'>"
                    "Sélectionnez deux clusters ou plus dans la liste (choix multiples), puis cliquez sur FUSIONNER. "
                    "Les pages seront regroupées et Mistral générera un nouveau nom.</p></div>",
                    unsafe_allow_html=True,
                )
                if num_clusters < 2:
                    st.info("Au moins 2 clusters requis pour fusionner.")
                else:
                    merge_options = [
                        f"{i + 1}. {(cluster_labels[i].get('model_name') or f'Cluster {i + 1}').strip()} ({len(cluster_urls[i])} p.)"
                        for i in range(num_clusters)
                    ]
                    selected_labels = st.multiselect(
                        "Clusters à fusionner (sélectionnez 2 ou plus)",
                        merge_options,
                        default=[],
                        key="fusion_multiselect",
                        help="Maintenez Ctrl/Cmd pour sélectionner plusieurs clusters.",
                    )
                    selected_indices = sorted([merge_options.index(lbl) for lbl in selected_labels]) if selected_labels else []

                    if len(selected_indices) >= 2:
                        total_pages = sum(len(cluster_urls[i]) for i in selected_indices)
                        names_preview = " + ".join(
                            (cluster_labels[i].get("model_name") or f"Cluster {i + 1}").strip()
                            for i in selected_indices
                        )
                        st.markdown("**Aperçu :**")
                        st.markdown(f"- {names_preview} → **{total_pages}** pages fusionnées")

                        if st.button("FUSIONNER", type="primary", key="fusion_manual_btn"):
                            keep_idx = selected_indices[0]
                            merged_urls = []
                            for i in selected_indices:
                                merged_urls.extend(cluster_urls[i] if i < len(cluster_urls) else [])
                            merged_urls = list(dict.fromkeys(merged_urls))
                            best_idx = max(selected_indices, key=lambda i: len(cluster_urls[i]) if i < len(cluster_urls) else 0)
                            merged_dom = cluster_dom[best_idx] if best_idx < len(cluster_dom) else {}
                            merged_jsonld = cluster_jsonld[best_idx] if best_idx < len(cluster_jsonld) else None
                            new_label = (cluster_labels[best_idx] if best_idx < len(cluster_labels) else {}).copy()
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
                                    with st.spinner("Mistral génère un nouveau nom..."):
                                        renamed = name_cluster_with_mistral(
                                            mistral_key, merged_sample_pages, list(range(len(merged_sample_pages)))
                                        )
                                        if renamed:
                                            new_label = renamed
                            new_cluster_urls = []
                            new_cluster_dom = []
                            new_cluster_jsonld = []
                            new_cluster_labels = []
                            new_optimized = []
                            for i in range(num_clusters):
                                if i in selected_indices and i != keep_idx:
                                    continue
                                if i == keep_idx:
                                    new_cluster_urls.append(merged_urls)
                                    new_cluster_dom.append(merged_dom)
                                    new_cluster_jsonld.append(merged_jsonld)
                                    new_cluster_labels.append(new_label)
                                    new_optimized.append(None)
                                else:
                                    new_cluster_urls.append(cluster_urls[i])
                                    new_cluster_dom.append(cluster_dom[i] if i < len(cluster_dom) else {})
                                    new_cluster_jsonld.append(cluster_jsonld[i] if i < len(cluster_jsonld) else None)
                                    new_cluster_labels.append(cluster_labels[i] if i < len(cluster_labels) else {"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"})
                                    new_optimized.append(st.session_state.get(f"optimized_jsonld_{i}"))
                            for k in list(st.session_state.keys()):
                                if k.startswith("optimized_jsonld_"):
                                    del st.session_state[k]
                            for j, opt in enumerate(new_optimized):
                                if opt is not None:
                                    st.session_state[f"optimized_jsonld_{j}"] = opt
                            results_data = st.session_state.get("jsonld_analyzer_results", {})
                            results_data["cluster_urls"] = new_cluster_urls
                            results_data["cluster_dom_structures"] = new_cluster_dom
                            results_data["cluster_jsonld"] = new_cluster_jsonld
                            results_data["cluster_labels"] = new_cluster_labels
                            st.session_state["jsonld_analyzer_results"] = results_data
                            new_keep_pos = new_cluster_urls.index(merged_urls)
                            st.session_state["jsonld_selected_cluster"] = new_keep_pos
                            st.success(f" Fusionné ! Nouveau nom : {new_label.get('model_name', 'Cluster fusionné')}")
                            st.balloons()
                            st.rerun()
                    elif selected_indices:
                        st.warning("Sélectionnez au moins 2 clusters pour fusionner.")

            with tab_tableau:
                tab_labels = []
                for i in range(num_clusters):
                    label = cluster_labels[i] if i < len(cluster_labels) else {"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"}
                    name = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
                    n = len(cluster_urls[i]) if i < len(cluster_urls) else 0
                    has_jld = "Oui" if st.session_state.get(f"optimized_jsonld_{i}") else "Non"
                    tab_labels.append(f"{i + 1}. {name} ({n} p.) {has_jld}")

                cluster_tabs = st.tabs(tab_labels)

                for i, tab in enumerate(cluster_tabs):
                    with tab:
                        label = cluster_labels[i] if i < len(cluster_labels) else {"model_name": f"Cluster {i + 1}", "schema_type": "WebPage"}
                        urls_in_cluster = cluster_urls[i] if i < len(cluster_urls) else []
                        pattern = get_cluster_url_pattern(urls_in_cluster)
                        sample = urls_in_cluster[:5]
                        name = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
                        schema_type = (label.get("schema_type") or "").strip() or "—"
                        has_opt = st.session_state.get(f"optimized_jsonld_{i}")

                        if has_opt:
                            st.markdown(
                                '<span style="display:inline-block; background:#dcfce7; color:#166534; padding:4px 10px; font-size:0.75rem; font-weight:700; text-transform:uppercase;">JSON-LD généré</span>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                '<span style="display:inline-block; background:#fef3c7; color:#92400e; padding:4px 10px; font-size:0.75rem; font-weight:700; text-transform:uppercase;">En attente</span>',
                                unsafe_allow_html=True,
                            )
                        st.markdown("")
                        st.markdown(f"**Modèle :** {name}")
                        st.markdown(f"**Schema.org :** `{schema_type}`")
                        st.markdown(f"**Pattern d'URL :** `{pattern}`")
                        st.markdown("**URLs exemples :**")
                        for u in sample:
                            st.code(u, language=None)
                        if len(urls_in_cluster) > 5:
                            st.caption(f"... et {len(urls_in_cluster) - 5} de plus.")

            with tab_export:
                from core.database import AuditDatabase
                from core.session_keys import get_current_user_email

                # Bandeau de stats
                generated_count = sum(1 for i in range(num_clusters) if st.session_state.get(f"optimized_jsonld_{i}"))
                valid_count = sum(
                    1 for i in range(num_clusters)
                    if st.session_state.get(f"optimized_jsonld_{i}")
                    and validate_jsonld_schema(st.session_state[f"optimized_jsonld_{i}"])["valid"]
                )
                total_pages_export = sum(len(cluster_urls[i]) for i in range(len(cluster_urls)))
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(
                        f'<div class="zen-metric"><div class="zen-metric-value">{num_clusters}</div>'
                        '<div class="zen-metric-label">Clusters</div></div>',
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.markdown(
                        f'<div class="zen-metric"><div class="zen-metric-value">{generated_count}<span style="font-size:0.75rem; font-weight:500; color:rgba(0,0,0,0.4);">/{num_clusters}</span></div>'
                        '<div class="zen-metric-label">JSON-LD générés</div></div>',
                        unsafe_allow_html=True,
                    )
                with col3:
                    st.markdown(
                        f'<div class="zen-metric"><div class="zen-metric-value">{valid_count}<span style="font-size:0.75rem; font-weight:500; color:rgba(0,0,0,0.4);">/{generated_count}</span></div>'
                        '<div class="zen-metric-label">JSON-LD valides</div></div>',
                        unsafe_allow_html=True,
                    )
                with col4:
                    st.markdown(
                        f'<div class="zen-metric"><div class="zen-metric-value">{total_pages_export}</div>'
                        '<div class="zen-metric-label">Pages analysées</div></div>',
                        unsafe_allow_html=True,
                    )
                st.markdown("---")

                st.caption("Chargement : utilisez la barre en haut → Choix de la sauvegarde → VALIDER.")
                st.markdown("---")

                # 02 — Génération en masse
                st.markdown(
                    '<p style="font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">02 — Génération en masse</p>'
                    '<p style="font-size:0.85rem; color:#64748b; margin:0 0 1rem 0;">Générez automatiquement les JSON-LD optimisés pour tous les clusters.</p>',
                    unsafe_allow_html=True,
                )
                pending_count = sum(1 for i in range(num_clusters) if not st.session_state.get(f"optimized_jsonld_{i}"))
                col_batch_info, col_batch_btn = st.columns([3, 1])
                with col_batch_info:
                    if pending_count == 0:
                        st.success(f" Tous les {num_clusters} clusters ont déjà un JSON-LD optimisé généré.")
                    else:
                        st.info(f" {pending_count} cluster(s) sur {num_clusters} en attente de génération.")
                with col_batch_btn:
                    batch_btn = st.button(
                        "GÉNÉRER TOUS",
                        type="primary",
                        disabled=(pending_count == 0),
                        use_container_width=True,
                        key="batch_generate_all",
                    )
                if batch_btn and pending_count > 0:
                    try:
                        mistral_key = st.secrets["mistral"]["api_key"]
                    except Exception:
                        mistral_key = None
                    if not mistral_key:
                        st.error("Clé API Mistral manquante. Configurez st.secrets['mistral']['api_key'].")
                    else:
                        progress_bar = st.progress(0.0, "Initialisation...")
                        success_count = 0
                        fail_count = 0
                        done = 0
                        for i in range(num_clusters):
                            if st.session_state.get(f"optimized_jsonld_{i}"):
                                continue
                            done += 1
                            progress = done / pending_count
                            cluster_name = (cluster_labels[i].get("model_name") or f"Cluster {i+1}").strip()
                            progress_bar.progress(progress, f"Génération {done}/{pending_count} : {cluster_name}...")
                            label = cluster_labels[i]
                            schema_type = label.get("schema_type", "WebPage")
                            dom = cluster_dom[i] if i < len(cluster_dom) else {}
                            jld = cluster_jsonld[i] if i < len(cluster_jsonld) else None
                            urls_in_cluster = cluster_urls[i] if i < len(cluster_urls) else []
                            pattern = get_cluster_url_pattern(urls_in_cluster)
                            sample_pages = []
                            if "jsonld_analyzer_crawl_results" in st.session_state:
                                for url in urls_in_cluster[:3]:
                                    for p in st.session_state["jsonld_analyzer_crawl_results"]:
                                        if p.get("url") == url:
                                            sample_pages.append({
                                                "url": url,
                                                "title": p.get("title", ""),
                                                "h1": p.get("h1", ""),
                                                "description": p.get("description", ""),
                                                "html_snippet": (p.get("html_content") or "")[:5000],
                                            })
                                            break
                            optimized, _ = generate_optimized_jsonld(
                                api_key=mistral_key,
                                schema_type=schema_type,
                                dom_structure=dom,
                                sample_pages=sample_pages,
                                existing_jsonld=jld,
                                url_pattern=pattern,
                                timeout=30,
                            )
                            if optimized:
                                st.session_state[f"optimized_jsonld_{i}"] = optimized
                                success_count += 1
                            else:
                                fail_count += 1
                            time.sleep(0.5)
                        progress_bar.empty()
                        if fail_count == 0:
                            st.success(f"{success_count} JSON-LD générés avec succès !")
                            st.balloons()
                        else:
                            st.warning(f" {success_count} réussis, {fail_count} échecs. Réessayez les échecs individuellement.")
                        st.rerun()

                st.markdown("---")
                st.markdown(
                    '<p style="font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">03 — Export complet</p>'
                    '<p style="font-size:0.85rem; color:#64748b; margin:0 0 1rem 0;">Téléchargez un ZIP contenant tous les JSON-LD générés, organisés par cluster avec README et manifest.</p>',
                    unsafe_allow_html=True,
                )
                available_count = sum(1 for i in range(num_clusters) if st.session_state.get(f"optimized_jsonld_{i}"))
                if available_count == 0:
                    st.info("Aucun JSON-LD généré. Utilisez « GÉNÉRER TOUS » ou générez-les individuellement dans l'onglet Graphe.")
                else:
                    col_zip_info, col_zip_btn = st.columns([3, 1])
                    with col_zip_info:
                        st.markdown(f"**{available_count} JSON-LD** disponible(s) pour export.")
                    with col_zip_btn:
                        get_opt = lambda i: st.session_state.get(f"optimized_jsonld_{i}")
                        zip_data = _create_jsonld_zip(cluster_labels, cluster_urls, domain, get_opt)
                        st.download_button(
                            "TÉLÉCHARGER ZIP",
                            data=zip_data,
                            file_name=f"jsonld_export_{domain.replace('.', '_')}.zip",
                            mime="application/zip",
                            use_container_width=True,
                            key="export_zip_all",
                        )

                st.markdown("---")
                st.caption("Sauvegarde : utilisez le bouton **SAUVEGARDER** en haut de la page.")
                site_url = data.get("site_url") or f"https://{domain}"
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

                st.markdown(
                    '<p style="font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">05 — Télécharger JSON</p>',
                    unsafe_allow_html=True,
                )
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


def render_jsonld_fusion_intelligente():
    """Onglet LEAF : Fusion intelligente par Mistral (suggestions + Accepter/Refuser)."""
    import streamlit as st

    st.markdown(
        "<p class='section-title'>LEAF — Fusion intelligente</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='home-tagline' style='margin-bottom:1rem; color:#0f172a;'>"
        "Mistral analyse les noms des clusters et propose des fusions (même type de page). "
        "Validez une à une. La fusion manuelle reste dans l'onglet FUSION de la Vue d'ensemble.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if "jsonld_analyzer_results" not in st.session_state:
        st.info("Lancez d'abord une analyse dans **Vue d'ensemble** (onglet Nouvelle analyse) pour afficher les suggestions de fusion.")
        return

    data = st.session_state["jsonld_analyzer_results"]
    cluster_labels = data["cluster_labels"]
    cluster_urls = data["cluster_urls"]
    cluster_dom = data.get("cluster_dom_structures", [])
    cluster_jsonld = data.get("cluster_jsonld", [])
    num_clusters = len(cluster_labels)

    if num_clusters < 2:
        st.info("Au moins 2 clusters requis pour la fusion intelligente. Lancez une analyse avec plusieurs types de pages.")
        return

    st.markdown(
        '<div style="background:#f8fafc; border:1px solid #e2e8f0; padding:1rem 1.25rem; margin-bottom:1rem;">'
        "<p style='font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; color:#0f172a; margin:0 0 0.5rem 0;'>"
        "Fusion intelligente par Mistral</p>"
        "<p style='font-size:0.85rem; color:#64748b; margin:0;'>"
        "Mistral analyse les noms des clusters et propose des fusions (même type de page). "
        "Validez une à une. La fusion manuelle reste dans l'onglet FUSION.</p></div>",
        unsafe_allow_html=True,
    )
    merge_suggestions = st.session_state.get("jsonld_merge_suggestions") or []
    suggestion_idx = st.session_state.get("jsonld_merge_suggestion_idx", 0)

    col_launch, _ = st.columns([1, 2])
    with col_launch:
        if st.button("Lancer les suggestions Mistral", key="jsonld_merge_suggest_btn"):
            try:
                mistral_key = st.secrets["mistral"]["api_key"]
            except Exception:
                mistral_key = None
            if not mistral_key:
                st.error("Clé API Mistral manquante. Configurez st.secrets['mistral']['api_key'].")
            else:
                with st.spinner("Mistral analyse les clusters..."):
                    merge_suggestions = suggest_cluster_merges_with_mistral(
                        mistral_key, cluster_labels, cluster_urls
                    )
                st.session_state["jsonld_merge_suggestions"] = merge_suggestions
                st.session_state["jsonld_merge_suggestion_idx"] = 0
                st.session_state["jsonld_merge_suggestions_asked"] = True
                st.rerun()

    if merge_suggestions and suggestion_idx < len(merge_suggestions):
        sugg = merge_suggestions[suggestion_idx]
        idx_a, idx_b = sugg["source"], sugg["target"]
        reason = sugg.get("reason", "Noms similaires")
        name_a = (cluster_labels[idx_a].get("model_name") or f"Cluster {idx_a + 1}").strip()
        name_b = (cluster_labels[idx_b].get("model_name") or f"Cluster {idx_b + 1}").strip()
        count_a = len(cluster_urls[idx_a]) if idx_a < len(cluster_urls) else 0
        count_b = len(cluster_urls[idx_b]) if idx_b < len(cluster_urls) else 0

        st.markdown(
            f'<div style="background:#fffbeb; border:1px solid #fcd34d; padding:1rem 1.25rem; margin:0.5rem 0;">'
            f'<p style="font-weight:700; font-size:0.9rem; margin:0 0 0.5rem 0;">Suggestion {suggestion_idx + 1}/{len(merge_suggestions)}</p>'
            f'<p style="margin:0.25rem 0; font-size:0.95rem;">Fusionner « <strong>{name_a}</strong> » avec « <strong>{name_b}</strong> » ?</p>'
            f'<p style="font-size:0.8rem; color:#64748b; margin:0.25rem 0;">Raison : {reason}</p>'
            f'<p style="font-size:0.85rem; margin:0.5rem 0 0 0;">{name_a} ({count_a} p.) + {name_b} ({count_b} p.) → {count_a + count_b} pages</p></div>',
            unsafe_allow_html=True,
        )
        col_accept, col_refuse, _ = st.columns([1, 1, 2])
        with col_accept:
            if st.button("Accepter", type="primary", key="jsonld_merge_accept"):
                if idx_a >= len(cluster_labels) or idx_b >= len(cluster_labels):
                    st.session_state["jsonld_merge_suggestions"] = []
                    st.session_state["jsonld_merge_suggestion_idx"] = 0
                    st.rerun()
                else:
                    idx, target_idx = (idx_a, idx_b) if idx_a < idx_b else (idx_b, idx_a)
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
                            with st.spinner("Mistral génère un nouveau nom..."):
                                renamed = name_cluster_with_mistral(
                                    mistral_key, merged_sample_pages, list(range(len(merged_sample_pages)))
                                )
                                if renamed:
                                    new_label = renamed
                    cluster_urls = list(cluster_urls)
                    cluster_dom = list(cluster_dom)
                    cluster_jsonld = list(cluster_jsonld)
                    cluster_labels = list(cluster_labels)
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
                    merged_suggestions = []
                    for s in merge_suggestions:
                        if s["source"] == idx or s["target"] == idx or s["source"] == target_idx or s["target"] == target_idx:
                            continue
                        new_s = {"source": s["source"], "target": s["target"], "reason": s.get("reason", "")}
                        if s["source"] > idx:
                            new_s["source"] -= 1
                        if s["target"] > idx:
                            new_s["target"] -= 1
                        if new_s["source"] > target_idx:
                            new_s["source"] -= 1
                        if new_s["target"] > target_idx:
                            new_s["target"] -= 1
                        merged_suggestions.append(new_s)
                    st.session_state["jsonld_merge_suggestions"] = merged_suggestions
                    st.session_state["jsonld_merge_suggestion_idx"] = min(suggestion_idx, len(merged_suggestions) - 1) if merged_suggestions else 0
                    new_merged_idx = target_idx - 1 if idx < target_idx else target_idx
                    st.session_state["jsonld_selected_cluster"] = new_merged_idx
                    st.success(f" Fusionné ! Nouveau nom : {new_label.get('model_name', 'Cluster fusionné')}")
                    st.rerun()
        with col_refuse:
            if st.button("Refuser", key="jsonld_merge_refuse"):
                st.session_state["jsonld_merge_suggestion_idx"] = suggestion_idx + 1
                if suggestion_idx + 1 >= len(merge_suggestions):
                    st.session_state["jsonld_merge_suggestions"] = []
                    st.session_state["jsonld_merge_suggestion_idx"] = 0
                st.rerun()
    elif merge_suggestions and suggestion_idx >= len(merge_suggestions):
        st.info("Toutes les suggestions ont été traitées.")
        st.session_state["jsonld_merge_suggestions"] = []
        st.session_state["jsonld_merge_suggestion_idx"] = 0
    elif st.session_state.get("jsonld_merge_suggestions_asked") and (not merge_suggestions or len(merge_suggestions) == 0):
        st.info("Mistral n'a trouvé aucune fusion pertinente.")
