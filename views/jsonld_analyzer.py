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
        "<p class='section-title'>ANALYSE JSON-LD</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='home-tagline' style='margin-bottom:1rem; color:#0f172a;'>"
        "Détection des types de pages par structure DOM et pattern d'URL. Clustering intelligent (seuil ajustable).</p>",
        unsafe_allow_html=True,
    )

    tab_new, tab_load = st.tabs(["Nouvelle analyse", "Charger depuis Sheets"])
    with tab_load:
        from core.database import AuditDatabase
        from core.session_keys import get_current_user_email

        user_email = get_current_user_email() or ""
        db = AuditDatabase()

        # --- Sauvegardes unifiées (onglet unified_saves) ---
        unified_saves = []
        if user_email and getattr(db, "sheet_file", None):
            unified_saves = [u for u in db.list_unified_saves(user_email, workspace=None) if u.get("has_jsonld")]

        if unified_saves:
            st.markdown(
                '<p style="font-weight:700; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">Sauvegardes unifiées</p>',
                unsafe_allow_html=True,
            )
            unified_labels = {f"{u.get('nom_site') or 'Site'} ({u.get('created_at')}) — {u.get('workspace')}": u for u in unified_saves}
            sel_unified = st.selectbox(
                "Choisir une sauvegarde unifiée",
                list(unified_labels.keys()),
                key="jsonld_load_unified_select",
                label_visibility="collapsed",
            )
            if st.button("CHARGER (sauvegardes unifiées)", type="primary", use_container_width=True, key="jsonld_load_unified_btn"):
                u = unified_labels[sel_unified]
                loaded = db.load_unified(u["save_id"], user_email)
                if not loaded:
                    st.error("Sauvegarde introuvable ou accès refusé.")
                else:
                    jsonld_data = loaded.get("jsonld_data") or []
                    site_url = loaded.get("site_url", "")
                    domain = urlparse(site_url).netloc or "site"
                    cluster_labels = []
                    cluster_urls = []
                    cluster_dom = []
                    cluster_jsonld = []
                    total_pages = 0
                    for i, m in enumerate(jsonld_data):
                        cluster_labels.append({"model_name": m.get("model_name") or "Cluster", "schema_type": m.get("schema_type") or m.get("recommended_schema") or "WebPage"})
                        urls = m.get("sample_urls")
                        if not isinstance(urls, list):
                            urls = urls if isinstance(urls, list) else []
                        cluster_urls.append(urls)
                        cluster_dom.append(m.get("dom_structure") or {})
                        cluster_jsonld.append(m.get("existing_jsonld"))
                        total_pages += m.get("page_count", 0)
                    st.session_state["jsonld_analyzer_results"] = {
                        "site_url": site_url,
                        "domain": domain,
                        "total_pages": total_pages,
                        "cluster_labels": cluster_labels,
                        "cluster_urls": cluster_urls,
                        "cluster_dom_structures": cluster_dom,
                        "cluster_jsonld": cluster_jsonld,
                        "logs": [],
                        "loaded_from_sheet": True,
                    }
                    for k in list(st.session_state.keys()):
                        if k.startswith("optimized_jsonld_"):
                            del st.session_state[k]
                    for i, m in enumerate(jsonld_data):
                        opt = m.get("optimized_jsonld")
                        if opt is not None and isinstance(opt, dict):
                            st.session_state[f"optimized_jsonld_{i}"] = opt
                    crawl_data = loaded.get("crawl_data")
                    if crawl_data:
                        st.session_state["jsonld_analyzer_crawl_results"] = crawl_data
                    st.success("Données chargées depuis les sauvegardes unifiées.")
                    st.rerun()
            st.markdown("---")

        # --- Anciennes (onglet jsonld) ---
        sites = db.list_jsonld_sites(user_email) if user_email and db.client else []

        if not sites and not unified_saves:
            st.caption("Aucune donnée enregistrée pour votre compte. Lancez une analyse puis enregistrez dans Google Sheets.")
        elif sites:
            st.markdown(
                '<p style="font-weight:700; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">Anciennes (onglet jsonld)</p>',
                unsafe_allow_html=True,
            )
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

        # Fusion suggérée par Mistral
        if num_clusters >= 2:
            with st.container():
                st.markdown(
                    '<div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:0; padding:1rem 1.25rem; margin-bottom:1rem;">'
                    "<p style='font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; color:#0f172a; margin:0 0 0.5rem 0;'>"
                    "Fusion intelligente par Mistral</p>"
                    "<p style='font-size:0.85rem; color:#64748b; margin:0;'>"
                    "Mistral analyse les noms des clusters et propose des fusions (même type de page). "
                    "Validez une à une. La fusion manuelle reste dans l'onglet FUSION.</p></div>",
                    unsafe_allow_html=True,
                )
            merge_suggestions = st.session_state.get("jsonld_merge_suggestions") or []
            suggestion_idx = st.session_state.get("jsonld_merge_suggestion_idx", 0)

            col_launch, col_status = st.columns([1, 2])
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

        st.markdown("---")
        if num_clusters == 0:
            st.info("Lancez une nouvelle analyse avec une URL différente ou plus de pages.")
        else:
            tab_names = ["GRAPHE", "TABLEAU", "EXPORT", "FUSION"] + (["Logs"] if logs else [])
            tabs = st.tabs(tab_names)
            tab_graphe, tab_tableau, tab_export, tab_fusion = tabs[0], tabs[1], tabs[2], tabs[3]
            tab_logs = tabs[4] if logs else None

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
                                        st.success(" JSON-LD optimisé généré !")
                                        st.rerun()
                                    else:
                                        st.error(f" Échec de la génération. {err_msg or 'Erreur inconnue.'}")
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
                                st.warning(" Aucun JSON-LD détecté sur ces pages.")

                        with col_optimized:
                            st.markdown("**JSON-LD optimisé**")
                            optimized_data = st.session_state.get(f"optimized_jsonld_{idx}")
                            if optimized_data:
                                st.json(optimized_data)
                                validation_result = validate_jsonld_schema(optimized_data)
                                if validation_result["valid"]:
                                    if validation_result["warnings"]:
                                        st.warning(validation_result["message"])
                                        with st.expander("Voir les warnings"):
                                            for w in validation_result["warnings"]:
                                                st.markdown(f"- {w}")
                                    else:
                                        st.success(validation_result["message"])
                                else:
                                    st.error(validation_result["message"])
                                    with st.expander("Voir les erreurs"):
                                        for e in validation_result["errors"]:
                                            st.markdown(f"- {e}")
                                st.download_button(
                                    "Télécharger JSON-LD",
                                    data=json.dumps(optimized_data, ensure_ascii=False, indent=2),
                                    file_name=f"jsonld_optimized_{name.lower().replace(' ', '_')[:30]}.json",
                                    mime="application/json",
                                    use_container_width=True,
                                    key=f"download_jsonld_{idx}",
                                )
                            else:
                                st.info("Cliquez sur 'GÉNÉRER' pour créer le JSON-LD optimisé.")

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
                    "Si deux clusters représentent le même type de page (ex: « Fiches métiers » et « Pages emploi »), "
                    "fusionnez-les ici. Les pages seront regroupées et Mistral générera un nouveau nom.</p></div>",
                    unsafe_allow_html=True,
                )
                if num_clusters < 2:
                    st.info("Au moins 2 clusters requis pour fusionner.")
                else:
                    merge_options = [
                        f"{i + 1}. {(cluster_labels[i].get('model_name') or f'Cluster {i + 1}').strip()} ({len(cluster_urls[i])} p.)"
                        for i in range(num_clusters)
                    ]
                    col_src, col_tgt = st.columns(2)
                    with col_src:
                        idx = st.selectbox(
                            "Cluster source (à fusionner)",
                            range(num_clusters),
                            format_func=lambda i: merge_options[i],
                            key="fusion_source",
                        )
                    with col_tgt:
                        other_options = [(i, merge_options[i]) for i in range(num_clusters) if i != idx]
                        target_sel = st.selectbox(
                            "Fusionner avec",
                            [name for _, name in other_options],
                            key="fusion_target",
                        )
                        target_idx = next(i for i, name in other_options if name == target_sel)

                    urls_in_cluster = cluster_urls[idx] if idx < len(cluster_urls) else []
                    current_name = (cluster_labels[idx].get("model_name") or f"Cluster {idx + 1}").strip()
                    target_name = (cluster_labels[target_idx].get("model_name") or f"Cluster {target_idx + 1}").strip()

                    st.markdown("**Aperçu :**")
                    st.markdown(f"- **{current_name}** ({len(urls_in_cluster)} p.) + **{target_name}** ({len(cluster_urls[target_idx])} p.) → {len(urls_in_cluster) + len(cluster_urls[target_idx])} pages fusionnées")

                    if st.button("FUSIONNER", type="primary", key="fusion_manual_btn"):
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
                        st.session_state["jsonld_selected_cluster"] = target_idx - 1 if idx < target_idx else target_idx
                        st.success(f" Fusionné ! Nouveau nom : {new_label.get('model_name', 'Cluster fusionné')}")
                        st.balloons()
                        st.rerun()

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

                # Génération en masse
                st.markdown(
                    '<p style="font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">01 — Génération en masse</p>'
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
                    '<p style="font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">02 — Export complet</p>'
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
                st.markdown(
                    '<p style="font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">03 — Charger depuis Google Sheets</p>',
                    unsafe_allow_html=True,
                )
                _user_email = get_current_user_email() or ""
                _db = AuditDatabase()
                _unified = [u for u in (_db.list_unified_saves(_user_email, workspace=None) or []) if u.get("has_jsonld")] if getattr(_db, "sheet_file", None) else []
                if _unified:
                    _unified_labels = {f"{u.get('nom_site') or 'Site'} ({u.get('created_at')})": u for u in _unified}
                    _sel_u = st.selectbox("Sauvegardes unifiées", list(_unified_labels.keys()), key="jsonld_load_export_unified")
                    if st.button("CHARGER (unifié)", use_container_width=True, key="jsonld_load_export_unified_btn"):
                        _u = _unified_labels[_sel_u]
                        _loaded = _db.load_unified(_u["save_id"], _user_email)
                        if _loaded and _loaded.get("jsonld_data"):
                            _jd = _loaded["jsonld_data"]
                            _site_url = _loaded.get("site_url", "")
                            _domain = urlparse(_site_url).netloc or "site"
                            _labels = [{"model_name": m.get("model_name") or "Cluster", "schema_type": m.get("schema_type") or "WebPage"} for m in _jd]
                            _urls = [m.get("sample_urls") if isinstance(m.get("sample_urls"), list) else [] for m in _jd]
                            _doms = [m.get("dom_structure") or {} for m in _jd]
                            _jlds = [m.get("existing_jsonld") for m in _jd]
                            for k in list(st.session_state.keys()):
                                if k.startswith("optimized_jsonld_"):
                                    del st.session_state[k]
                            for i, m in enumerate(_jd):
                                opt = m.get("optimized_jsonld")
                                if opt is not None and isinstance(opt, dict):
                                    st.session_state[f"optimized_jsonld_{i}"] = opt
                            st.session_state["jsonld_analyzer_results"] = {"site_url": _site_url, "domain": _domain, "total_pages": sum(m.get("page_count", 0) for m in _jd), "cluster_labels": _labels, "cluster_urls": _urls, "cluster_dom_structures": _doms, "cluster_jsonld": _jlds, "logs": [], "loaded_from_sheet": True}
                            if _loaded.get("crawl_data"):
                                st.session_state["jsonld_analyzer_crawl_results"] = _loaded["crawl_data"]
                            st.success("Données chargées (sauvegardes unifiées).")
                            st.rerun()
                        else:
                            st.warning("Sauvegarde introuvable ou sans données JSON-LD.")
                _sites = _db.list_jsonld_sites(_user_email) if _user_email and _db.client else []
                if _sites:
                    if _unified:
                        st.caption("Anciennes (onglet jsonld) :")
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
                st.markdown("---")
                st.markdown(
                    '<p style="font-weight:700; font-size:0.9rem; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 0.5rem 0;">04 — Enregistrer dans Google Sheets</p>',
                    unsafe_allow_html=True,
                )
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
                    ok_legacy = db.save_jsonld_models(user_email, site_url, workspace, models_data)
                    nom_site = (data.get("domain") or domain or "Site")[:200]
                    crawl_for_unified = st.session_state.get("jsonld_analyzer_crawl_results") or []
                    ok_unified = False
                    if getattr(db, "sheet_file", None):
                        try:
                            db.save_unified(user_email, workspace, site_url, nom_site, crawl_data=crawl_for_unified, geo_data=None, jsonld_data=models_data)
                            ok_unified = True
                        except Exception as e:
                            if ok_legacy:
                                st.warning("Enregistré dans l'onglet 'jsonld'. Sauvegarde unifiée en échec: " + str(e)[:80])
                            else:
                                st.error("Sauvegarde unifiée en échec: " + str(e)[:200])
                    if ok_legacy or ok_unified:
                        st.success("Enregistré dans Google Sheets" + (" (sauvegardes unifiées)" if ok_unified else " (onglet jsonld)."))
                        try:
                            st.toast("Enregistrement réussi")
                        except Exception:
                            pass
                    elif not ok_legacy:
                        st.error("Échec de l'enregistrement. Vérifiez la config GCP (secrets) et l'URL du Sheet.")

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
