# =============================================================================
# JSON-LD Analyzer — Interface Streamlit (SaaS-ready)
# Analyse de sites, clustering, comparaison visuelle, batch processing.
# Logique métier : services/jsonld_service.py + services/jsonld_diff.py
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
from services.jsonld_diff import (
    compute_jsonld_diff,
    extract_modified_fields,
    render_comparison_html,
    diff_summary,
)


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

def _create_jsonld_zip(cluster_labels, cluster_urls, domain, get_optimized):
    """ZIP contenant tous les JSON-LD optimisés + README + manifest."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = (
            f"JSON-LD EXPORT - {domain}\n{'=' * 40}\n\n"
            f"JSON-LD Schema.org optimisés pour chaque type de page.\n"
            f"Généré le {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        zf.writestr("README.txt", readme)
        for i in range(len(cluster_labels)):
            opt = get_optimized(i)
            if opt:
                name = (cluster_labels[i].get("model_name") or f"Cluster {i+1}").strip()
                safe = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
                zf.writestr(f"{i+1:02d}_{safe}.json", json.dumps(opt, ensure_ascii=False, indent=2))
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


def _get_sample_pages(urls_in_cluster, session_state, max_pages=3):
    """Extract sample page data from crawl results for a cluster."""
    pages = []
    crawl_res = session_state.get("jsonld_analyzer_crawl_results", [])
    for url in urls_in_cluster[:max_pages]:
        for p in crawl_res:
            if p.get("url") == url:
                pages.append({
                    "url": url,
                    "title": p.get("title", ""),
                    "h1": p.get("h1", ""),
                    "description": p.get("description", ""),
                    "html_snippet": (p.get("html_content") or "")[:5000],
                })
                break
    return pages


def _get_mistral_key():
    from core.mistral_utils import get_mistral_key
    return get_mistral_key() or None


# ═════════════════════════════════════════════════════════════════════════════
# Main entry point
# ═════════════════════════════════════════════════════════════════════════════

def render_jsonld_analyzer_tab():
    """Onglet Vue d'ensemble : crawl + clustering + comparaison JSON-LD."""
    import streamlit as st
    from views.audit_geo import run_unified_site_analysis, _format_crawl_error

    st.markdown("<p class='section-title'>VUE ENSEMBLE</p>", unsafe_allow_html=True)
    st.markdown(
        "<p class='home-tagline' style='margin-bottom:1rem;color:#0f172a;'>"
        "Détection des types de pages par structure DOM et pattern d'URL. Clustering intelligent.</p>",
        unsafe_allow_html=True,
    )
    st.caption("Chargement / sauvegarde : barre en haut → Choix du workspace → VALIDER ou SAUVEGARDER.")
    st.markdown("---")

    # ─── Charger / Nouvelle analyse ──────────────────────────────────────────
    tab_load, tab_new = st.tabs(["Charger (rappel)", "Nouvelle analyse"])
    with tab_load:
        st.info("Utilisez la barre en haut : **Choix de la sauvegarde** puis **VALIDER**.")

    with tab_new:
        st.caption("Un seul scrape remplit l'Audit GEO et la Vue d'ensemble JSON-LD.")

        if "scraping_engine" not in st.session_state:
            st.session_state["scraping_engine"] = "v2"
        _engine_label = st.radio(
            "Moteur de scraping",
            ["V2 — Crawl4AI (rapide)", "V1 — Selenium (robuste)"],
            index=0 if st.session_state.get("scraping_engine") == "v2" else 1,
            horizontal=True,
            key="scraping_engine_radio_jsonld",
        )
        use_v2 = "V2" in str(_engine_label)
        st.session_state["scraping_engine"] = "v2" if use_v2 else "v1"

        url_input = st.text_input("URL du site", placeholder="https://www.example.com", key="jsonld_analyzer_url")
        max_pages = st.slider("Pages à crawler", 1, 10000, 150, 10, key="jsonld_analyzer_max_pages")
        cluster_threshold = st.slider("Seuil de similarité (%)", 70, 98, 85, 1, key="jsonld_analyzer_threshold") / 100.0
        use_selenium_jsonld = st.checkbox("Selenium (sites protégés)", value=False, key="jsonld_use_selenium")

        def _on_launch():
            st.session_state["_jsonld_launch"] = True

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.button("LANCER L'ANALYSE", type="primary", use_container_width=True, key="jsonld_analyzer_btn", on_click=_on_launch)
        with col_btn2:
            if "jsonld_analyzer_results" in st.session_state and st.button("EFFACER", use_container_width=True, key="jsonld_clear_btn"):
                for k in list(st.session_state.keys()):
                    if k.startswith(("optimized_jsonld_", "jsonld_prompt_", "jsonld_validated_")):
                        del st.session_state[k]
                del st.session_state["jsonld_analyzer_results"]
                st.session_state.pop("jsonld_analyzer_crawl_results", None)
                st.rerun()

        if st.session_state.pop("_jsonld_launch", False):
            if not url_input or not url_input.strip():
                st.warning("Veuillez entrer une URL.")
                return
            url = url_input.strip()
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            progress_ph = st.empty()
            with progress_ph:
                bar = st.progress(0.0, "Crawl et analyse unifiés...")
            try:
                run_unified_site_analysis(
                    st.session_state,
                    urls=[url],
                    max_pages=max_pages,
                    use_selenium=use_selenium_jsonld,
                    selenium_mode="light" if use_selenium_jsonld else None,
                    workspace_name=st.session_state.get("audit_workspace_select") or "Non classé",
                    engine=st.session_state.get("scraping_engine", "v2"),
                    cluster_threshold=cluster_threshold,
                    progress_callback=lambda msg, val: bar.progress(min(val, 1.0), msg),
                    log_callback=lambda msg: None,
                )
            except Exception as e:
                progress_ph.empty()
                st.error(_format_crawl_error(e))
                return
            progress_ph.empty()
            st.rerun()

    # ═════════════════════════════════════════════════════════════════════════
    # RESULTS
    # ═════════════════════════════════════════════════════════════════════════
    if "jsonld_analyzer_results" not in st.session_state:
        return

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
    st.markdown("<p class='section-title'>Vue d'ensemble</p>", unsafe_allow_html=True)

    col_s, col_p, col_c = st.columns(3)
    with col_s:
        st.markdown(
            f'<div class="zen-metric"><div class="zen-metric-value" style="font-size:1.1rem;word-break:break-all;">'
            f'{domain[:40]}{"…" if len(domain) > 40 else ""}</div><div class="zen-metric-label">Site</div></div>',
            unsafe_allow_html=True,
        )
    with col_p:
        st.markdown(
            f'<div class="zen-metric"><div class="zen-metric-value">{total_pages}</div>'
            '<div class="zen-metric-label">Pages</div></div>',
            unsafe_allow_html=True,
        )
    with col_c:
        st.markdown(
            f'<div class="zen-metric"><div class="zen-metric-value">{num_clusters}</div>'
            '<div class="zen-metric-label">Modèles</div></div>',
            unsafe_allow_html=True,
        )

    if num_clusters == 0:
        st.warning("Aucun cluster détecté.")
        return

    st.markdown("---")
    tab_names = ["VUE ENSEMBLE", "TRAITEMENT UNITAIRE", "TRAITEMENT EN MASSE", "TABLEAU", "EXPORT", "FUSION"]
    if logs:
        tab_names.append("Logs")
    tabs = st.tabs(tab_names)

    with tabs[0]:
        _render_vue_ensemble(data, cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters, domain)
    with tabs[1]:
        _render_unit_processing(cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters)
    with tabs[2]:
        _render_batch_processing(cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters)
    with tabs[3]:
        _render_tableau(cluster_labels, cluster_urls, num_clusters)
    with tabs[4]:
        _render_export(data, cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters, domain, total_pages)
    with tabs[5]:
        _render_fusion(cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters)
    if logs and len(tabs) > 6:
        with tabs[6]:
            st.text("\n".join(logs[-150:]))


# ═════════════════════════════════════════════════════════════════════════════
# VUE ENSEMBLE — Graphe + Détails cluster (pleine largeur, sous le graphe)
# ═════════════════════════════════════════════════════════════════════════════

def _render_vue_ensemble(data, cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters, domain):
    import streamlit as st
    import streamlit.components.v1 as components

    html_graph = build_jsonld_graph_html(domain, cluster_labels, cluster_urls)
    components.html(html_graph, height=620)
    st.caption("Cliquez sur un **cluster** (bleu) pour voir les détails ci-dessous.")
    st.markdown("---")

    selected = _get_selected_cluster(num_clusters)
    site_url = data.get("site_url") or f"https://{domain}"

    options = ["Nœud central (URL du site)"] + [
        f"{i+1}. {(cluster_labels[i].get('model_name') or '').strip() or f'Cluster {i+1}'} ({len(cluster_urls[i])} p.)"
        for i in range(num_clusters)
    ]
    default_idx = max(0, min(selected + 1, len(options) - 1))

    sel = st.selectbox("Sélectionner un nœud", options, index=default_idx, key="jsonld_cluster_select")
    if sel:
        menu_idx = options.index(sel)
        selected = -1 if menu_idx == 0 else menu_idx - 1
        st.session_state["jsonld_selected_cluster"] = selected

    st.markdown("---")

    if selected == -1:
        _render_master_node(site_url)
    else:
        _render_cluster_detail(selected, cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters)


def _get_selected_cluster(num_clusters):
    import streamlit as st
    selected = None
    try:
        qp = getattr(st, "query_params", None)
        if qp and "jsonld_cluster" in qp:
            selected = int(qp["jsonld_cluster"])
            if selected < -1 or selected >= num_clusters:
                selected = -1
            st.session_state["jsonld_selected_cluster"] = selected
    except (ValueError, TypeError, KeyError):
        pass
    if selected is None:
        selected = st.session_state.get("jsonld_selected_cluster", -1)
        if selected < -1 or selected >= num_clusters:
            selected = -1
    return selected


def _render_master_node(site_url):
    import streamlit as st
    st.markdown("**Nœud central** (pas un cluster)")
    st.caption("Page du site utilisée pour le scrape — porte le Master.")
    st.markdown(f"**URL** : {site_url}")
    st.markdown("---")

    master_data = st.session_state.get("master_data")
    jsonld_master = st.session_state.get("jsonld_master") or ""

    if master_data:
        name = getattr(master_data, "brand_name", "") or getattr(master_data, "legal_name", "") or "—"
        st.markdown(f"**Entité** : {name}")
        st.success("Master renseigné. Modifiez-le dans l'onglet **MASTER**.")
    else:
        st.warning("Aucun Master renseigné. Onglet **MASTER** pour configurer.")

    if jsonld_master.strip():
        st.markdown("**JSON-LD Master**")
        st.code(jsonld_master, language="json")
    else:
        st.caption("Aucun JSON-LD Master généré.")


# ═════════════════════════════════════════════════════════════════════════════
# Détail d'un cluster (sous le graphe, pleine largeur)
# ═════════════════════════════════════════════════════════════════════════════

def _render_cluster_detail(idx, cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters):
    import streamlit as st

    label = cluster_labels[idx] if idx < len(cluster_labels) else {}
    name = (label.get("model_name") or "").strip() or f"Cluster {idx + 1}"
    schema_type = (label.get("schema_type") or "").strip() or "—"
    urls_in_cluster = cluster_urls[idx] if idx < len(cluster_urls) else []
    pattern = get_cluster_url_pattern(urls_in_cluster)
    dom = cluster_dom[idx] if idx < len(cluster_dom) else {}
    existing_jld = cluster_jsonld[idx] if idx < len(cluster_jsonld) else None
    optimized = st.session_state.get(f"optimized_jsonld_{idx}")
    prompt_data = st.session_state.get(f"jsonld_prompt_{idx}")

    # ── Info banner ──────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;padding:12px 16px;border-radius:6px;margin-bottom:1rem;">'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;">'
        f'<div><span style="color:#64748b;font-size:0.75rem;text-transform:uppercase;">Modèle</span><br/><strong>{name}</strong></div>'
        f'<div><span style="color:#64748b;font-size:0.75rem;text-transform:uppercase;">Schema.org</span><br/><code>{schema_type}</code></div>'
        f'<div><span style="color:#64748b;font-size:0.75rem;text-transform:uppercase;">Pattern</span><br/><code>{pattern}</code></div>'
        f'<div><span style="color:#64748b;font-size:0.75rem;text-transform:uppercase;">Pages</span><br/><strong>{len(urls_in_cluster)}</strong></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Sub-tabs: DOM, JSON-LD brut, URLs (sous le schéma des nœuds) ────────
    tab_dom, tab_jld_raw, tab_urls = st.tabs(["Structure DOM", "JSON-LD brut", "URLs"])

    with tab_dom:
        if dom:
            st.json(dom)
            if len(urls_in_cluster) > 1 and "jsonld_analyzer_crawl_results" in st.session_state:
                cluster_doms = []
                for url in urls_in_cluster:
                    for page in st.session_state["jsonld_analyzer_crawl_results"]:
                        if page.get("url") == url:
                            page_dom = page.get("dom_structure") or extract_dom_structure(page.get("html_content") or "")
                            cluster_doms.append(page_dom)
                            break
                if cluster_doms:
                    variability = []
                    for tag in FLEXIBLE_TAGS:
                        counts = [d.get(tag, 0) for d in cluster_doms]
                        if counts and max(counts) != min(counts):
                            variability.append(f"{tag.upper()}: {min(counts)}-{max(counts)}")
                    if variability:
                        st.caption(f"**Variabilité** : {' • '.join(variability)}")
        else:
            st.caption("Non disponible.")

    with tab_jld_raw:
        if existing_jld:
            st.json(existing_jld)
        else:
            st.caption("Aucun JSON-LD détecté sur ces pages.")

    with tab_urls:
        for u in urls_in_cluster[:5]:
            st.markdown(f"- [{u}]({u})")
        if len(urls_in_cluster) > 5:
            st.caption(f"... et {len(urls_in_cluster) - 5} de plus.")

    st.markdown("---")

    # ── JSON-LD : Comparaison visuelle ───────────────────────────────────────
    st.markdown("#### JSON-LD : Actuel vs Optimisé")

    display_mode = st.radio(
        "Mode d'affichage",
        ["Comparaison visuelle", "JSON-LD optimisé complet", "JSON-LD actuel + champs vides"],
        horizontal=True,
        key=f"jsonld_display_{idx}",
    )

    if display_mode == "Comparaison visuelle":
        if optimized:
            html = render_comparison_html(existing_jld, optimized)
            st.markdown(html, unsafe_allow_html=True)
            _show_validation_badge(optimized)
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**JSON-LD actuel**")
                if existing_jld:
                    st.json(existing_jld)
                else:
                    st.caption("Aucun JSON-LD détecté.")
            with col_b:
                st.markdown("**JSON-LD optimisé**")
                st.caption("Cliquez sur GÉNÉRER ci-dessous.")

    elif display_mode == "JSON-LD optimisé complet":
        if optimized:
            st.json(optimized)
            _show_validation_badge(optimized)
        else:
            st.caption("Aucun JSON-LD optimisé. Générez-le ci-dessous.")

    elif display_mode == "JSON-LD actuel + champs vides":
        if existing_jld:
            if optimized:
                merged = {}
                for key in list(dict.fromkeys(list(optimized.keys()) + list(existing_jld.keys()))):
                    if key in existing_jld:
                        merged[key] = existing_jld[key]
                    else:
                        merged[key] = f"⟵ {key} (absent)"
                st.json(merged)
                st.caption("Les champs ⟵ sont absents dans l'actuel mais présents dans l'optimisé.")
            else:
                st.json(existing_jld)
        else:
            st.caption("Aucun JSON-LD détecté.")

    # Download
    if optimized:
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.download_button(
                "JSON-LD optimisé",
                data=json.dumps(optimized, ensure_ascii=False, indent=2),
                file_name=f"jsonld_opt_{re.sub(r'[^a-z0-9]+', '_', name.lower())[:30]}.json",
                mime="application/json",
                use_container_width=True,
                key=f"dl_opt_{idx}",
            )
        with col_d2:
            delta = extract_modified_fields(existing_jld, optimized)
            if delta:
                st.download_button(
                    "Delta uniquement",
                    data=json.dumps(delta, ensure_ascii=False, indent=2),
                    file_name=f"jsonld_delta_{re.sub(r'[^a-z0-9]+', '_', name.lower())[:30]}.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"dl_delta_{idx}",
                )
        with col_d3:
            if st.session_state.get(f"jsonld_validated_{idx}"):
                st.success("Validé")
            elif st.button("Valider ce JSON-LD", key=f"validate_{idx}", type="primary", use_container_width=True):
                st.session_state[f"jsonld_validated_{idx}"] = True
                st.rerun()

    st.markdown("---")

    # ── Génération Mistral ───────────────────────────────────────────────────
    col_g1, col_g2 = st.columns([3, 1])
    with col_g1:
        st.markdown("**Génération automatique du JSON-LD optimisé**")
        st.caption("Mistral AI analyse la structure et génère un JSON-LD Schema.org complet.")
    with col_g2:
        gen_btn = st.button(
            "GÉNÉRER" if not optimized else "REGÉNÉRER",
            type="primary",
            use_container_width=True,
            key=f"gen_{idx}",
        )

    if gen_btn:
        mistral_key = _get_mistral_key()
        if not mistral_key:
            st.error("Clé API Mistral manquante. Configurez st.secrets['mistral']['api_key'].")
        else:
            sample_pages = _get_sample_pages(urls_in_cluster, st.session_state)
            prompt_out = {}
            with st.spinner("Mistral génère le JSON-LD optimisé..."):
                result, err = generate_optimized_jsonld(
                    api_key=mistral_key,
                    schema_type=schema_type if schema_type != "—" else "WebPage",
                    dom_structure=dom,
                    sample_pages=sample_pages,
                    existing_jsonld=existing_jld,
                    url_pattern=pattern,
                    prompt_output=prompt_out,
                )
            if result:
                st.session_state[f"optimized_jsonld_{idx}"] = result
                if prompt_out:
                    st.session_state[f"jsonld_prompt_{idx}"] = prompt_out
                st.success("JSON-LD optimisé généré !")
                st.rerun()
            else:
                st.error(f"Échec. {err or ''}")

    # ── Prompt display ───────────────────────────────────────────────────────
    if prompt_data:
        with st.expander("Voir le prompt envoyé à Mistral"):
            st.markdown("**System prompt :**")
            st.code(prompt_data.get("system_prompt", ""), language=None)
            st.markdown("**User prompt :**")
            st.code(prompt_data.get("user_prompt", ""), language=None)


def _show_validation_badge(optimized):
    import streamlit as st
    result = validate_jsonld_schema(optimized)
    if result["valid"]:
        if result.get("warnings"):
            st.caption(result["message"])
        else:
            st.success(result["message"])
    else:
        st.error(result["message"])


# ═════════════════════════════════════════════════════════════════════════════
# TRAITEMENT UNITAIRE — Sélection d'un nœud, optimisation Mistral, comparaison
# ═════════════════════════════════════════════════════════════════════════════

def _render_unit_processing(cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters):
    import streamlit as st

    st.markdown("### Traitement unitaire")
    st.caption("Sélectionnez un nœud, lancez l'optimisation Mistral et comparez le JSON-LD actuel avec l'optimisé.")

    options = [
        f"{i+1}. {(cluster_labels[i].get('model_name') or '').strip() or f'Cluster {i+1}'} ({len(cluster_urls[i])} p.)"
        for i in range(num_clusters)
    ]
    sel = st.selectbox("Sélectionner un nœud à optimiser", options, key="unit_node_select")
    if not sel:
        return
    idx = options.index(sel)

    label = cluster_labels[idx] if idx < len(cluster_labels) else {}
    name = (label.get("model_name") or "").strip() or f"Cluster {idx + 1}"
    schema_type = (label.get("schema_type") or "").strip() or "—"
    urls_in_cluster = cluster_urls[idx] if idx < len(cluster_urls) else []
    pattern = get_cluster_url_pattern(urls_in_cluster)
    dom = cluster_dom[idx] if idx < len(cluster_dom) else {}
    existing_jld = cluster_jsonld[idx] if idx < len(cluster_jsonld) else None
    optimized = st.session_state.get(f"optimized_jsonld_{idx}")
    prompt_data = st.session_state.get(f"jsonld_prompt_{idx}")
    is_validated = st.session_state.get(f"jsonld_validated_{idx}", False)

    # ── Info banner ──────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;padding:12px 16px;border-radius:6px;margin-bottom:1rem;">'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;">'
        f'<div><span style="color:#64748b;font-size:0.75rem;text-transform:uppercase;">Modèle</span><br/><strong>{name}</strong></div>'
        f'<div><span style="color:#64748b;font-size:0.75rem;text-transform:uppercase;">Schema.org</span><br/><code>{schema_type}</code></div>'
        f'<div><span style="color:#64748b;font-size:0.75rem;text-transform:uppercase;">Pattern</span><br/><code>{pattern}</code></div>'
        f'<div><span style="color:#64748b;font-size:0.75rem;text-transform:uppercase;">Pages</span><br/><strong>{len(urls_in_cluster)}</strong></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Bouton Générer / Regénérer ───────────────────────────────────────────
    col_g1, col_g2 = st.columns([3, 1])
    with col_g1:
        st.markdown("**Optimisation Mistral**")
        st.caption("Mistral AI analyse la structure DOM et les pages du cluster pour générer un JSON-LD Schema.org complet.")
    with col_g2:
        gen_btn = st.button(
            "GÉNÉRER" if not optimized else "REGÉNÉRER",
            type="primary",
            use_container_width=True,
            key=f"unit_gen_{idx}",
        )

    if gen_btn:
        mistral_key = _get_mistral_key()
        if not mistral_key:
            st.error("Clé API Mistral manquante. Configurez `st.secrets['mistral']['api_key']`.")
        else:
            sample_pages = _get_sample_pages(urls_in_cluster, st.session_state)
            prompt_out = {}
            with st.spinner("Mistral génère le JSON-LD optimisé..."):
                result, err = generate_optimized_jsonld(
                    api_key=mistral_key,
                    schema_type=schema_type if schema_type != "—" else "WebPage",
                    dom_structure=dom,
                    sample_pages=sample_pages,
                    existing_jsonld=existing_jld,
                    url_pattern=pattern,
                    prompt_output=prompt_out,
                )
            if result:
                st.session_state[f"optimized_jsonld_{idx}"] = result
                if prompt_out:
                    st.session_state[f"jsonld_prompt_{idx}"] = prompt_out
                st.success("JSON-LD optimisé généré !")
                st.rerun()
            else:
                st.error(f"Échec de la génération. {err or ''}")

    # ── Prompt Mistral ───────────────────────────────────────────────────────
    if prompt_data:
        with st.expander("Voir le prompt envoyé à Mistral"):
            st.markdown("**System prompt :**")
            st.code(prompt_data.get("system_prompt", ""), language=None)
            st.markdown("**User prompt :**")
            st.code(prompt_data.get("user_prompt", ""), language=None)

    st.markdown("---")

    # ── Comparaison JSON-LD actuel vs optimisé ───────────────────────────────
    st.markdown("#### Comparaison : JSON-LD actuel vs optimisé")

    display_mode = st.radio(
        "Mode d'affichage",
        ["Comparaison visuelle", "JSON-LD optimisé complet", "JSON-LD actuel + champs vides"],
        horizontal=True,
        key=f"unit_display_{idx}",
    )

    if display_mode == "Comparaison visuelle":
        if optimized:
            html = render_comparison_html(existing_jld, optimized)
            st.markdown(html, unsafe_allow_html=True)
            _show_validation_badge(optimized)
            ds = diff_summary(existing_jld, optimized)
            st.caption(f"Champs : {ds['same']} identiques, {ds['added']} ajoutés, {ds['enriched']} enrichis, {ds['removed']} supprimés")
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**JSON-LD actuel**")
                if existing_jld:
                    st.json(existing_jld)
                else:
                    st.caption("Aucun JSON-LD détecté sur ces pages.")
            with col_b:
                st.markdown("**JSON-LD optimisé**")
                st.caption("Cliquez sur GÉNÉRER ci-dessus.")

    elif display_mode == "JSON-LD optimisé complet":
        if optimized:
            st.json(optimized)
            _show_validation_badge(optimized)
        else:
            st.caption("Aucun JSON-LD optimisé. Générez-le ci-dessus.")

    elif display_mode == "JSON-LD actuel + champs vides":
        if existing_jld:
            if optimized:
                merged = {}
                for key in list(dict.fromkeys(list(optimized.keys()) + list(existing_jld.keys()))):
                    if key in existing_jld:
                        merged[key] = existing_jld[key]
                    else:
                        merged[key] = f"⟵ {key} (absent)"
                st.json(merged)
                st.caption("Les champs ⟵ sont absents dans l'actuel mais présents dans l'optimisé.")
            else:
                st.json(existing_jld)
        else:
            st.caption("Aucun JSON-LD détecté.")

    # ── Actions : Download / Valider / Annuler ───────────────────────────────
    if optimized:
        st.markdown("---")
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        with col_d1:
            st.download_button(
                "JSON-LD optimisé",
                data=json.dumps(optimized, ensure_ascii=False, indent=2),
                file_name=f"jsonld_opt_{re.sub(r'[^a-z0-9]+', '_', name.lower())[:30]}.json",
                mime="application/json",
                use_container_width=True,
                key=f"unit_dl_opt_{idx}",
            )
        with col_d2:
            delta = extract_modified_fields(existing_jld, optimized)
            if delta:
                st.download_button(
                    "Delta uniquement",
                    data=json.dumps(delta, ensure_ascii=False, indent=2),
                    file_name=f"jsonld_delta_{re.sub(r'[^a-z0-9]+', '_', name.lower())[:30]}.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"unit_dl_delta_{idx}",
                )
        with col_d3:
            if is_validated:
                st.success("Validé")
            elif st.button("Valider", key=f"unit_validate_{idx}", type="primary", use_container_width=True):
                st.session_state[f"jsonld_validated_{idx}"] = True
                st.rerun()
        with col_d4:
            if st.button("Annuler (rollback)", key=f"unit_rollback_{idx}", use_container_width=True):
                for prefix in ("optimized_jsonld_", "jsonld_validated_", "jsonld_prompt_"):
                    st.session_state.pop(f"{prefix}{idx}", None)
                st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# TRAITEMENT EN MASSE — Batch generation + node-by-node validation
# ═════════════════════════════════════════════════════════════════════════════

def _render_batch_processing(cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters):
    import streamlit as st

    st.markdown("### Traitement en masse")
    st.caption("Générez les JSON-LD optimisés pour tous les clusters, puis validez nœud par nœud.")

    generated = sum(1 for i in range(num_clusters) if st.session_state.get(f"optimized_jsonld_{i}"))
    validated = sum(1 for i in range(num_clusters) if st.session_state.get(f"jsonld_validated_{i}"))
    pending = num_clusters - generated

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clusters", num_clusters)
    c2.metric("Générés", f"{generated}/{num_clusters}")
    c3.metric("Validés", f"{validated}/{num_clusters}")
    c4.metric("En attente", pending)

    st.markdown("---")

    # ── 1. Batch generate ────────────────────────────────────────────────────
    st.markdown("#### 1. Génération en masse")
    col_i, col_b = st.columns([3, 1])
    with col_i:
        if pending == 0:
            st.success(f"Tous les {num_clusters} clusters ont un JSON-LD optimisé.")
        else:
            st.info(f"{pending} cluster(s) en attente.")
    with col_b:
        batch_btn = st.button("GÉNÉRER TOUS", type="primary", disabled=(pending == 0), use_container_width=True, key="batch_gen_all")

    if batch_btn and pending > 0:
        mistral_key = _get_mistral_key()
        if not mistral_key:
            st.error("Clé API Mistral manquante.")
        else:
            bar = st.progress(0.0, "Initialisation...")
            ok, fail, done = 0, 0, 0
            for i in range(num_clusters):
                if st.session_state.get(f"optimized_jsonld_{i}"):
                    continue
                done += 1
                cname = (cluster_labels[i].get("model_name") or f"Cluster {i+1}").strip()
                bar.progress(done / pending, f"Génération {done}/{pending} : {cname}...")

                schema = cluster_labels[i].get("schema_type", "WebPage")
                dom = cluster_dom[i] if i < len(cluster_dom) else {}
                jld = cluster_jsonld[i] if i < len(cluster_jsonld) else None
                urls_c = cluster_urls[i] if i < len(cluster_urls) else []
                pat = get_cluster_url_pattern(urls_c)
                pages = _get_sample_pages(urls_c, st.session_state)

                prompt_out = {}
                result, _ = generate_optimized_jsonld(
                    api_key=mistral_key, schema_type=schema, dom_structure=dom,
                    sample_pages=pages, existing_jsonld=jld, url_pattern=pat,
                    timeout=90, prompt_output=prompt_out,
                )
                if result:
                    st.session_state[f"optimized_jsonld_{i}"] = result
                    if prompt_out:
                        st.session_state[f"jsonld_prompt_{i}"] = prompt_out
                    ok += 1
                else:
                    fail += 1
                time.sleep(0.5)

            bar.empty()
            if fail == 0:
                st.success(f"{ok} JSON-LD générés !")
                st.balloons()
            else:
                st.warning(f"{ok} réussis, {fail} échecs.")
            st.rerun()

    st.markdown("---")

    # ── 2. Validation nœud par nœud (onglets) ──────────────────────────────
    st.markdown("#### 2. Validation nœud par nœud")
    st.caption("Comparez avant/après et validez ou annulez chaque JSON-LD optimisé.")

    validation_tab_labels = []
    for i in range(num_clusters):
        label = cluster_labels[i] if i < len(cluster_labels) else {}
        cname = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
        is_validated = st.session_state.get(f"jsonld_validated_{i}", False)
        has_opt = st.session_state.get(f"optimized_jsonld_{i}")
        if is_validated:
            icon = "✓"
        elif has_opt:
            icon = "⏳"
        else:
            icon = "—"
        validation_tab_labels.append(f"{icon} {i+1}. {cname}")

    validation_tabs = st.tabs(validation_tab_labels)
    for i, vtab in enumerate(validation_tabs):
        with vtab:
            label = cluster_labels[i] if i < len(cluster_labels) else {}
            cname = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
            schema = (label.get("schema_type") or "").strip() or "WebPage"
            opt = st.session_state.get(f"optimized_jsonld_{i}")
            existing = cluster_jsonld[i] if i < len(cluster_jsonld) else None
            is_validated = st.session_state.get(f"jsonld_validated_{i}", False)

            if opt:
                html = render_comparison_html(existing, opt)
                st.markdown(html, unsafe_allow_html=True)

                ds = diff_summary(existing, opt)
                st.caption(f"**{cname}** ({schema}) — {ds['same']} identiques, {ds['added']} ajoutés, {ds['enriched']} enrichis, {ds['removed']} supprimés")

                c_v, c_r = st.columns(2)
                with c_v:
                    if not is_validated:
                        if st.button("Valider", key=f"bv_{i}", type="primary", use_container_width=True):
                            st.session_state[f"jsonld_validated_{i}"] = True
                            st.rerun()
                    else:
                        st.success("Validé")
                with c_r:
                    if st.button("Annuler (rollback)", key=f"br_{i}", use_container_width=True):
                        for prefix in ("optimized_jsonld_", "jsonld_validated_", "jsonld_prompt_"):
                            st.session_state.pop(f"{prefix}{i}", None)
                        st.rerun()
            else:
                st.caption("Non encore généré. Utilisez « GÉNÉRER TOUS » ci-dessus ou l'onglet **Traitement unitaire**.")

    if generated > 0:
        st.markdown("---")
        c_va, c_ra = st.columns(2)
        with c_va:
            if st.button("VALIDER TOUS", type="primary", use_container_width=True, key="bv_all"):
                for i in range(num_clusters):
                    if st.session_state.get(f"optimized_jsonld_{i}"):
                        st.session_state[f"jsonld_validated_{i}"] = True
                st.rerun()
        with c_ra:
            if st.button("ANNULER TOUS", use_container_width=True, key="br_all"):
                for i in range(num_clusters):
                    for prefix in ("optimized_jsonld_", "jsonld_validated_", "jsonld_prompt_"):
                        st.session_state.pop(f"{prefix}{i}", None)
                st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# TABLEAU
# ═════════════════════════════════════════════════════════════════════════════

def _render_tableau(cluster_labels, cluster_urls, num_clusters):
    import streamlit as st

    tab_labels = []
    for i in range(num_clusters):
        label = cluster_labels[i] if i < len(cluster_labels) else {}
        cname = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
        n = len(cluster_urls[i]) if i < len(cluster_urls) else 0
        has_jld = "Oui" if st.session_state.get(f"optimized_jsonld_{i}") else "Non"
        tab_labels.append(f"{i+1}. {cname} ({n} p.) {has_jld}")

    cluster_tabs = st.tabs(tab_labels)
    for i, tab in enumerate(cluster_tabs):
        with tab:
            label = cluster_labels[i] if i < len(cluster_labels) else {}
            urls_c = cluster_urls[i] if i < len(cluster_urls) else []
            pat = get_cluster_url_pattern(urls_c)
            cname = (label.get("model_name") or "").strip() or f"Cluster {i + 1}"
            schema = (label.get("schema_type") or "").strip() or "—"
            has_opt = st.session_state.get(f"optimized_jsonld_{i}")

            if has_opt:
                st.markdown(
                    '<span style="display:inline-block;background:#dcfce7;color:#166534;padding:4px 10px;font-size:0.75rem;font-weight:700;text-transform:uppercase;">JSON-LD généré</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span style="display:inline-block;background:#fef3c7;color:#92400e;padding:4px 10px;font-size:0.75rem;font-weight:700;text-transform:uppercase;">En attente</span>',
                    unsafe_allow_html=True,
                )
            st.markdown(f"**Modèle :** {cname}")
            st.markdown(f"**Schema.org :** `{schema}`")
            st.markdown(f"**Pattern :** `{pat}`")
            st.markdown("**URLs :**")
            for u in urls_c[:5]:
                st.code(u, language=None)
            if len(urls_c) > 5:
                st.caption(f"... et {len(urls_c) - 5} de plus.")


# ═════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═════════════════════════════════════════════════════════════════════════════

def _render_export(data, cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters, domain, total_pages):
    import streamlit as st

    generated_count = sum(1 for i in range(num_clusters) if st.session_state.get(f"optimized_jsonld_{i}"))
    valid_count = sum(
        1 for i in range(num_clusters)
        if st.session_state.get(f"optimized_jsonld_{i}") and validate_jsonld_schema(st.session_state[f"optimized_jsonld_{i}"])["valid"]
    )
    total_p = sum(len(cluster_urls[i]) for i in range(len(cluster_urls)))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="zen-metric"><div class="zen-metric-value">{num_clusters}</div>'
            '<div class="zen-metric-label">Clusters</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="zen-metric"><div class="zen-metric-value">{generated_count}'
            f'<span style="font-size:0.75rem;font-weight:500;color:rgba(0,0,0,0.4);">/{num_clusters}</span></div>'
            '<div class="zen-metric-label">JSON-LD générés</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="zen-metric"><div class="zen-metric-value">{valid_count}'
            f'<span style="font-size:0.75rem;font-weight:500;color:rgba(0,0,0,0.4);">/{generated_count}</span></div>'
            '<div class="zen-metric-label">Valides</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="zen-metric"><div class="zen-metric-value">{total_p}</div>'
            '<div class="zen-metric-label">Pages</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ZIP export
    st.markdown("#### Export ZIP")
    available = sum(1 for i in range(num_clusters) if st.session_state.get(f"optimized_jsonld_{i}"))
    if available == 0:
        st.info("Aucun JSON-LD généré. Utilisez l'onglet **Traitement en masse**.")
    else:
        ci, cb = st.columns([3, 1])
        with ci:
            st.markdown(f"**{available} JSON-LD** disponible(s).")
        with cb:
            get_opt = lambda i: st.session_state.get(f"optimized_jsonld_{i}")
            zip_data = _create_jsonld_zip(cluster_labels, cluster_urls, domain, get_opt)
            st.download_button(
                "TÉLÉCHARGER ZIP", data=zip_data,
                file_name=f"jsonld_{domain.replace('.', '_')}.zip",
                mime="application/zip", use_container_width=True, key="zip_all",
            )

    st.markdown("---")

    # JSON export
    st.markdown("#### Export JSON complet")
    site_url = data.get("site_url") or f"https://{domain}"
    models_data = []
    for i in range(num_clusters):
        label = cluster_labels[i] if i < len(cluster_labels) else {}
        urls_c = cluster_urls[i] if i < len(cluster_urls) else []
        pat = get_cluster_url_pattern(urls_c)
        opt = st.session_state.get(f"optimized_jsonld_{i}")
        existing = cluster_jsonld[i] if i < len(cluster_jsonld) else None
        delta = extract_modified_fields(existing, opt) if opt else None
        models_data.append({
            "model_name": (label.get("model_name") or "").strip() or f"Cluster {i+1}",
            "schema_type": (label.get("schema_type") or "").strip() or "WebPage",
            "page_count": len(urls_c),
            "url_pattern": pat,
            "sample_urls": urls_c[:5],
            "dom_structure": cluster_dom[i] if i < len(cluster_dom) else None,
            "existing_jsonld": existing,
            "optimized_jsonld": opt,
            "optimized_jsonld_delta": delta,
        })

    payload = {
        "site_url": site_url,
        "analyzed_at": __import__("datetime").datetime.now().isoformat() + "Z",
        "total_pages": total_pages,
        "models": models_data,
    }
    st.download_button(
        "Télécharger JSON complet",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name=f"jsonld_{domain.replace('.', '_')}.json",
        mime="application/json", use_container_width=True, key="json_dl",
    )

    st.markdown("---")
    st.caption("Sauvegarde Supabase : le bouton **SAUVEGARDER** en haut enregistre automatiquement. "
               "Seuls les champs modifiés (delta) sont stockés en plus du JSON-LD complet.")


# ═════════════════════════════════════════════════════════════════════════════
# FUSION MANUELLE
# ═════════════════════════════════════════════════════════════════════════════

def _render_fusion(cluster_labels, cluster_urls, cluster_dom, cluster_jsonld, num_clusters):
    import streamlit as st

    st.markdown(
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;padding:1rem 1.25rem;margin-bottom:1rem;">'
        '<p style="font-weight:700;font-size:0.9rem;text-transform:uppercase;letter-spacing:.05em;color:#0f172a;margin:0 0 .5rem 0;">Fusion manuelle</p>'
        '<p style="font-size:0.85rem;color:#64748b;margin:0;">Sélectionnez 2+ clusters, puis FUSIONNER. Mistral génère un nouveau nom.</p></div>',
        unsafe_allow_html=True,
    )

    if num_clusters < 2:
        st.info("Au moins 2 clusters requis.")
        return

    merge_options = [
        f"{i+1}. {(cluster_labels[i].get('model_name') or f'Cluster {i+1}').strip()} ({len(cluster_urls[i])} p.)"
        for i in range(num_clusters)
    ]
    selected_labels = st.multiselect("Clusters à fusionner (2+)", merge_options, default=[], key="fusion_ms")
    selected_indices = sorted([merge_options.index(lbl) for lbl in selected_labels]) if selected_labels else []

    if len(selected_indices) >= 2:
        total_p = sum(len(cluster_urls[i]) for i in selected_indices)
        names_preview = " + ".join((cluster_labels[i].get("model_name") or f"Cluster {i+1}").strip() for i in selected_indices)
        st.markdown(f"**Aperçu :** {names_preview} → **{total_p}** pages")

        if st.button("FUSIONNER", type="primary", key="fusion_btn"):
            keep_idx = selected_indices[0]
            merged_urls = []
            for i in selected_indices:
                merged_urls.extend(cluster_urls[i] if i < len(cluster_urls) else [])
            merged_urls = list(dict.fromkeys(merged_urls))

            best = max(selected_indices, key=lambda i: len(cluster_urls[i]) if i < len(cluster_urls) else 0)
            merged_dom = cluster_dom[best] if best < len(cluster_dom) else {}
            merged_jld = cluster_jsonld[best] if best < len(cluster_jsonld) else None
            new_label = (cluster_labels[best] if best < len(cluster_labels) else {}).copy()

            mistral_key = _get_mistral_key()
            if mistral_key:
                crawl_res = st.session_state.get("jsonld_analyzer_crawl_results", [])
                merged_sample = [p for u in merged_urls[:5] for p in crawl_res if p.get("url") == u][:5]
                if merged_sample:
                    with st.spinner("Mistral nomme le cluster fusionné..."):
                        renamed = name_cluster_with_mistral(mistral_key, merged_sample, list(range(len(merged_sample))))
                        if renamed:
                            new_label = renamed

            new_urls, new_dom, new_jld, new_labels, new_opt = [], [], [], [], []
            for i in range(num_clusters):
                if i in selected_indices and i != keep_idx:
                    continue
                if i == keep_idx:
                    new_urls.append(merged_urls)
                    new_dom.append(merged_dom)
                    new_jld.append(merged_jld)
                    new_labels.append(new_label)
                    new_opt.append(None)
                else:
                    new_urls.append(cluster_urls[i])
                    new_dom.append(cluster_dom[i] if i < len(cluster_dom) else {})
                    new_jld.append(cluster_jsonld[i] if i < len(cluster_jsonld) else None)
                    new_labels.append(cluster_labels[i] if i < len(cluster_labels) else {"model_name": f"Cluster {i+1}", "schema_type": "WebPage"})
                    new_opt.append(st.session_state.get(f"optimized_jsonld_{i}"))

            for k in list(st.session_state.keys()):
                if k.startswith(("optimized_jsonld_", "jsonld_prompt_", "jsonld_validated_")):
                    del st.session_state[k]
            for j, opt in enumerate(new_opt):
                if opt is not None:
                    st.session_state[f"optimized_jsonld_{j}"] = opt

            results_data = st.session_state.get("jsonld_analyzer_results", {})
            results_data["cluster_urls"] = new_urls
            results_data["cluster_dom_structures"] = new_dom
            results_data["cluster_jsonld"] = new_jld
            results_data["cluster_labels"] = new_labels
            st.session_state["jsonld_analyzer_results"] = results_data
            st.session_state["jsonld_selected_cluster"] = new_urls.index(merged_urls)
            st.success(f"Fusionné ! Nouveau nom : {new_label.get('model_name', 'Cluster fusionné')}")
            st.balloons()
            st.rerun()
    elif selected_indices:
        st.warning("Sélectionnez au moins 2 clusters.")


# ═════════════════════════════════════════════════════════════════════════════
# LEAF — Fusion intelligente (Mistral suggestions)
# ═════════════════════════════════════════════════════════════════════════════

def render_jsonld_fusion_intelligente():
    """Onglet LEAF : Fusion intelligente par Mistral (suggestions + Accepter/Refuser)."""
    import streamlit as st

    st.markdown("<p class='section-title'>LEAF — Fusion intelligente</p>", unsafe_allow_html=True)
    st.markdown(
        "<p class='home-tagline' style='margin-bottom:1rem;color:#0f172a;'>"
        "Mistral analyse les noms des clusters et propose des fusions. Validez une à une.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if "jsonld_analyzer_results" not in st.session_state:
        st.info("Lancez d'abord une analyse dans **Vue d'ensemble**.")
        return

    data = st.session_state["jsonld_analyzer_results"]
    cluster_labels = data["cluster_labels"]
    cluster_urls = data["cluster_urls"]
    cluster_dom = data.get("cluster_dom_structures", [])
    cluster_jsonld = data.get("cluster_jsonld", [])
    num_clusters = len(cluster_labels)

    if num_clusters < 2:
        st.info("Au moins 2 clusters requis pour la fusion intelligente.")
        return

    merge_suggestions = st.session_state.get("jsonld_merge_suggestions") or []
    suggestion_idx = st.session_state.get("jsonld_merge_suggestion_idx", 0)

    col_launch, _ = st.columns([1, 2])
    with col_launch:
        if st.button("Lancer les suggestions Mistral", key="merge_suggest_btn"):
            mistral_key = _get_mistral_key()
            if not mistral_key:
                st.error("Clé API Mistral manquante.")
            else:
                with st.spinner("Mistral analyse les clusters..."):
                    merge_suggestions = suggest_cluster_merges_with_mistral(mistral_key, cluster_labels, cluster_urls)
                st.session_state["jsonld_merge_suggestions"] = merge_suggestions
                st.session_state["jsonld_merge_suggestion_idx"] = 0
                st.session_state["jsonld_merge_suggestions_asked"] = True
                st.rerun()

    if merge_suggestions and suggestion_idx < len(merge_suggestions):
        sugg = merge_suggestions[suggestion_idx]
        idx_a, idx_b = sugg["source"], sugg["target"]
        reason = sugg.get("reason", "Noms similaires")
        name_a = (cluster_labels[idx_a].get("model_name") or f"Cluster {idx_a+1}").strip()
        name_b = (cluster_labels[idx_b].get("model_name") or f"Cluster {idx_b+1}").strip()
        count_a = len(cluster_urls[idx_a]) if idx_a < len(cluster_urls) else 0
        count_b = len(cluster_urls[idx_b]) if idx_b < len(cluster_urls) else 0

        st.markdown(
            f'<div style="background:#fffbeb;border:1px solid #fcd34d;padding:1rem;margin:.5rem 0;">'
            f'<p style="font-weight:700;font-size:0.9rem;margin:0 0 .5rem 0;">Suggestion {suggestion_idx+1}/{len(merge_suggestions)}</p>'
            f'<p style="margin:.25rem 0;">Fusionner « <strong>{name_a}</strong> » avec « <strong>{name_b}</strong> » ?</p>'
            f'<p style="font-size:0.8rem;color:#64748b;margin:.25rem 0;">Raison : {reason}</p>'
            f'<p style="font-size:0.85rem;margin:.5rem 0 0 0;">{count_a} + {count_b} = {count_a + count_b} pages</p></div>',
            unsafe_allow_html=True,
        )

        col_a, col_r, _ = st.columns([1, 1, 2])
        with col_a:
            if st.button("Accepter", type="primary", key="merge_accept"):
                if idx_a >= len(cluster_labels) or idx_b >= len(cluster_labels):
                    st.session_state["jsonld_merge_suggestions"] = []
                    st.session_state["jsonld_merge_suggestion_idx"] = 0
                    st.rerun()
                else:
                    idx, target_idx = (idx_a, idx_b) if idx_a < idx_b else (idx_b, idx_a)
                    merged_urls = list(set(cluster_urls[idx] + cluster_urls[target_idx]))
                    if len(cluster_urls[idx]) >= len(cluster_urls[target_idx]):
                        m_dom, m_jld, base_lbl = cluster_dom[idx], cluster_jsonld[idx], cluster_labels[idx]
                    else:
                        m_dom, m_jld, base_lbl = cluster_dom[target_idx], cluster_jsonld[target_idx], cluster_labels[target_idx]
                    new_label = base_lbl

                    mistral_key = _get_mistral_key()
                    if mistral_key:
                        crawl_res = st.session_state.get("jsonld_analyzer_crawl_results", [])
                        sample = [p for u in merged_urls[:5] for p in crawl_res if p.get("url") == u][:5]
                        if sample:
                            with st.spinner("Mistral nomme..."):
                                renamed = name_cluster_with_mistral(mistral_key, sample, list(range(len(sample))))
                                if renamed:
                                    new_label = renamed

                    cl_urls = list(cluster_urls)
                    cl_dom = list(cluster_dom)
                    cl_jld = list(cluster_jsonld)
                    cl_labels = list(cluster_labels)
                    cl_urls[target_idx] = merged_urls
                    cl_dom[target_idx] = m_dom
                    cl_jld[target_idx] = m_jld
                    cl_labels[target_idx] = new_label
                    del cl_urls[idx]
                    del cl_dom[idx]
                    del cl_jld[idx]
                    del cl_labels[idx]

                    rd = st.session_state.get("jsonld_analyzer_results", {})
                    rd["cluster_urls"] = cl_urls
                    rd["cluster_dom_structures"] = cl_dom
                    rd["cluster_jsonld"] = cl_jld
                    rd["cluster_labels"] = cl_labels
                    st.session_state["jsonld_analyzer_results"] = rd

                    for k in list(st.session_state.keys()):
                        if k.startswith(("optimized_jsonld_", "jsonld_prompt_", "jsonld_validated_")):
                            del st.session_state[k]

                    new_suggs = []
                    for s in merge_suggestions:
                        if s["source"] in (idx, target_idx) or s["target"] in (idx, target_idx):
                            continue
                        ns = {"source": s["source"], "target": s["target"], "reason": s.get("reason", "")}
                        if s["source"] > idx:
                            ns["source"] -= 1
                        if s["target"] > idx:
                            ns["target"] -= 1
                        new_suggs.append(ns)
                    st.session_state["jsonld_merge_suggestions"] = new_suggs
                    st.session_state["jsonld_merge_suggestion_idx"] = min(suggestion_idx, len(new_suggs) - 1) if new_suggs else 0
                    st.session_state["jsonld_selected_cluster"] = target_idx - 1 if idx < target_idx else target_idx
                    st.success(f"Fusionné ! {new_label.get('model_name', 'Cluster fusionné')}")
                    st.rerun()

        with col_r:
            if st.button("Refuser", key="merge_refuse"):
                st.session_state["jsonld_merge_suggestion_idx"] = suggestion_idx + 1
                if suggestion_idx + 1 >= len(merge_suggestions):
                    st.session_state["jsonld_merge_suggestions"] = []
                    st.session_state["jsonld_merge_suggestion_idx"] = 0
                st.rerun()

    elif merge_suggestions and suggestion_idx >= len(merge_suggestions):
        st.info("Toutes les suggestions ont été traitées.")
        st.session_state["jsonld_merge_suggestions"] = []
        st.session_state["jsonld_merge_suggestion_idx"] = 0
    elif st.session_state.get("jsonld_merge_suggestions_asked") and not merge_suggestions:
        st.info("Mistral n'a trouvé aucune fusion pertinente.")
