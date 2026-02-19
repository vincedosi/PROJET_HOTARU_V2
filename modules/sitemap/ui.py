"""Sitemap Dynamique — Streamlit UI.

5 sections: Project selector, Import, Configuration, Generation, History.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime

import pandas as pd
import streamlit as st

from core.session_keys import get_current_user_email

logger = logging.getLogger(__name__)


def _get_db():
    """Lazy-load SitemapDatabase with the current Supabase client."""
    from modules.sitemap.database import SitemapDatabase
    db_instance = st.session_state.get("db_instance")
    client = getattr(db_instance, "client", None) if db_instance else None
    if not client:
        return None
    return SitemapDatabase(client)


def _get_workspace() -> str:
    return st.session_state.get("audit_workspace_select") or st.session_state.get("current_ws") or "Non classé"


# =============================================================================
# MAIN RENDER
# =============================================================================

def render_sitemap_tab():
    """Main entry point for the Sitemap Dynamique tab."""
    st.markdown('<h1 class="zen-title">SITEMAP DYNAMIQUE</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="zen-subtitle">Sitemaps optimisés SEO et GEO — citabilité LLM maximale</p>',
        unsafe_allow_html=True,
    )

    sdb = _get_db()
    if not sdb:
        st.warning("Connexion Supabase requise pour le module Sitemap.")
        return

    workspace = _get_workspace()
    user_email = get_current_user_email()

    _render_project_selector(sdb, workspace, user_email)

    project = st.session_state.get("sitemap_current_project")
    if not project:
        st.info("Sélectionnez ou créez un projet pour commencer.")
        return

    tab_import, tab_config, tab_gen, tab_history = st.tabs([
        "Import",
        "Configuration",
        "Génération",
        "Historique",
    ])

    with tab_import:
        _render_import_section(sdb, project)
    with tab_config:
        _render_config_section(sdb, project)
    with tab_gen:
        _render_generation_section(sdb, project, user_email)
    with tab_history:
        _render_history_section(sdb, project)


# =============================================================================
# SECTION 1 : PROJECT SELECTOR
# =============================================================================

def _render_project_selector(sdb, workspace: str, user_email: str):
    st.markdown("### Projet Sitemap")

    projects = []
    try:
        projects = sdb.get_projects(workspace)
    except Exception as e:
        logger.error("get_projects error: %s", e)
        st.error(f"Erreur chargement projets : {str(e)[:150]}")

    project_names = ["— Nouveau projet —"] + [
        f"{p['name']} ({p['domain']})" for p in projects
    ]
    project_map = {f"{p['name']} ({p['domain']})": p for p in projects}

    col_sel, col_del = st.columns([4, 1])
    with col_sel:
        choice = st.selectbox("Projet", project_names, key="sitemap_project_select")
    with col_del:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if choice != "— Nouveau projet —":
            if st.button("Supprimer", key="sitemap_del_project", type="secondary"):
                proj = project_map.get(choice)
                if proj:
                    try:
                        sdb.delete_project(proj["id"])
                        st.toast(f"Projet « {proj['name']} » supprimé.")
                        st.session_state.pop("sitemap_current_project", None)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e)[:150])

    if choice == "— Nouveau projet —":
        st.session_state.pop("sitemap_current_project", None)
        with st.form("sitemap_new_project"):
            st.markdown("**Créer un projet**")
            name = st.text_input("Nom du projet", placeholder="Mon site e-commerce")
            domain = st.text_input("Domaine", placeholder="https://example.com")
            description = st.text_area("Description (optionnel)", height=68)
            c1, c2 = st.columns(2)
            with c1:
                max_geo = st.number_input("Max URLs GEO", 50, 5000, 500, step=50)
            with c2:
                min_cq = st.slider("Qualité contenu min.", 0.0, 1.0, 0.5, 0.05)
            min_jld = st.slider("Qualité JSON-LD min.", 0.0, 1.0, 0.5, 0.05)
            if st.form_submit_button("Créer le projet", type="primary"):
                if not name or not domain:
                    st.error("Nom et domaine requis.")
                else:
                    try:
                        proj = sdb.create_project(workspace, user_email, {
                            "name": name.strip(),
                            "domain": domain.strip(),
                            "description": description.strip(),
                            "max_urls_geo": max_geo,
                            "min_content_quality": min_cq,
                            "min_jsonld_quality": min_jld,
                        })
                        st.session_state["sitemap_current_project"] = proj
                        st.toast(f"Projet « {name} » créé.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {str(e)[:200]}")
    else:
        st.session_state["sitemap_current_project"] = project_map.get(choice)

    st.markdown("---")


# =============================================================================
# SECTION 2 : IMPORT
# =============================================================================

def _render_import_section(sdb, project: dict):
    st.subheader("Import des pages crawlées")

    pages_count = 0
    try:
        pages_count = sdb.get_pages_count(project["id"])
    except Exception:
        pass

    if pages_count:
        st.info(f"Ce projet contient **{pages_count} pages**. Un nouvel import met à jour les pages existantes (upsert par URL).")

    st.markdown("**Format CSV attendu** (colonnes obligatoires : `url`, `content_type`)")
    st.code(
        "url,content_type,has_jsonld,jsonld_quality,content_quality,monthly_traffic,backlinks,last_modified\n"
        "https://example.com/guide-seo,guide,true,0.85,0.90,1200,15,2026-02-15\n"
        "https://example.com/produit-xyz,product,true,0.70,0.60,450,3,2026-02-18",
        language="csv",
    )

    uploaded = st.file_uploader("Uploadez un CSV", type=["csv"], key="sitemap_csv_upload")

    if uploaded:
        try:
            df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Erreur lecture CSV : {e}")
            return

        required = ["url", "content_type"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"Colonnes manquantes : {', '.join(missing)}")
            return

        st.dataframe(df.head(15), use_container_width=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Pages", len(df))
        c2.metric("Types", df["content_type"].nunique())
        if "has_jsonld" in df.columns:
            c3.metric("Avec JSON-LD", int(df["has_jsonld"].sum()))

        if st.button("Importer les pages", type="primary", key="sitemap_import_btn"):
            with st.spinner(f"Import de {len(df)} pages..."):
                pages = df.to_dict("records")
                count = sdb.import_pages(project["id"], pages)
                sdb.calculate_priorities(project["id"], {
                    "min_content_quality": float(project.get("min_content_quality", 0.5)),
                    "min_jsonld_quality": float(project.get("min_jsonld_quality", 0.5)),
                })
            st.success(f"{count} pages importées. Priorités recalculées.")
            st.rerun()

    use_crawl = st.checkbox("Importer depuis les données crawlées en session", key="sitemap_from_crawl")
    if use_crawl:
        results = st.session_state.get("results") or []
        if not results:
            st.warning("Aucune donnée crawlée en session. Lancez d'abord un audit.")
        else:
            st.info(f"{len(results)} pages en session.")
            if st.button("Importer depuis la session", key="sitemap_import_session"):
                pages = []
                for r in results:
                    pages.append({
                        "url": r.get("url", ""),
                        "content_type": r.get("content_type", "page"),
                        "has_jsonld": bool(r.get("jsonld")),
                        "jsonld_quality": 0.7 if r.get("jsonld") else 0.0,
                        "content_quality": 0.6,
                        "monthly_traffic": 0,
                        "backlinks": 0,
                    })
                with st.spinner("Import..."):
                    count = sdb.import_pages(project["id"], pages)
                    sdb.calculate_priorities(project["id"])
                st.success(f"{count} pages importées depuis la session.")
                st.rerun()


# =============================================================================
# SECTION 3 : CONFIGURATION & PREVIEW
# =============================================================================

def _render_config_section(sdb, project: dict):
    st.subheader("Configuration et prévisualisation")

    pages = sdb.get_pages(project["id"], {"status": "active"})
    if not pages:
        st.warning("Aucune page importée. Allez dans l'onglet Import.")
        return

    tab_seo, tab_geo, tab_pages = st.tabs(["Config SEO", "Config GEO", "Pages"])

    with tab_seo:
        st.markdown("**Paramètres SEO**")
        st.caption("Le sitemap SEO inclut toutes les pages actives, triées par priorité SEO.")
        exclude_seo = st.multiselect(
            "Exclure les types",
            sorted({p.get("content_type", "page") for p in pages}),
            default=["legal"],
            key="sitemap_seo_exclude",
        )
        if st.button("Prévisualiser SEO", key="sitemap_preview_seo"):
            from modules.sitemap.engine import SitemapEngine
            engine = SitemapEngine(pages)
            result = engine.generate_seo_sitemap({"exclude_content_types": exclude_seo})
            stats = engine.get_stats(result)
            c1, c2, c3 = st.columns(3)
            c1.metric("URLs", stats["total"])
            c2.metric("Priorité moy.", f"{stats['avg_priority']:.2f}")
            c3.metric("Types", len(stats["by_type"]))
            st.markdown("**Top 10 URLs :**")
            top_df = pd.DataFrame(result[:10])[["url", "priority", "changefreq", "content_type"]]
            st.dataframe(top_df, use_container_width=True)
            st.markdown("**Distribution par type :**")
            st.bar_chart(pd.Series(stats["by_type"]))

    with tab_geo:
        st.markdown("**Paramètres GEO**")
        st.caption("Le sitemap GEO ne retient que les pages citables (JSON-LD + qualité contenu).")
        max_geo = st.number_input("Max URLs", 50, 5000, int(project.get("max_urls_geo", 500)),
                                   step=50, key="sitemap_geo_max")
        min_jld = st.slider("Qualité JSON-LD min.", 0.0, 1.0,
                             float(project.get("min_jsonld_quality", 0.5)), 0.05,
                             key="sitemap_geo_min_jld")
        min_cq = st.slider("Qualité contenu min.", 0.0, 1.0,
                            float(project.get("min_content_quality", 0.5)), 0.05,
                            key="sitemap_geo_min_cq")
        if st.button("Prévisualiser GEO", key="sitemap_preview_geo"):
            from modules.sitemap.engine import SitemapEngine
            engine = SitemapEngine(pages)
            result = engine.generate_geo_sitemap({
                "max_urls_geo": max_geo,
                "min_jsonld_quality": min_jld,
                "min_content_quality": min_cq,
            })
            stats = engine.get_stats(result)
            c1, c2, c3 = st.columns(3)
            c1.metric("URLs citables", stats["total"])
            c2.metric("Priorité moy.", f"{stats['avg_priority']:.2f}")
            c3.metric("Types", len(stats["by_type"]))
            if result:
                st.markdown("**Top 10 URLs citables :**")
                top_df = pd.DataFrame(result[:10])[["url", "priority", "jsonld_quality", "content_type"]]
                st.dataframe(top_df, use_container_width=True)
            else:
                st.warning("Aucune page ne remplit les critères de citabilité. Ajustez les seuils ou enrichissez vos pages.")

    with tab_pages:
        st.markdown("**Gestion des pages**")
        df_pages = pd.DataFrame(pages)
        if df_pages.empty:
            st.info("Aucune page.")
            return
        cols_display = ["url", "content_type", "seo_priority", "geo_priority", "is_citable", "status"]
        cols_available = [c for c in cols_display if c in df_pages.columns]
        st.dataframe(df_pages[cols_available].head(100), use_container_width=True)
        st.caption(f"Affichage limité à 100 lignes sur {len(df_pages)} pages.")

        if st.button("Recalculer les priorités", key="sitemap_recalc"):
            with st.spinner("Recalcul..."):
                n = sdb.calculate_priorities(project["id"], {
                    "min_content_quality": float(project.get("min_content_quality", 0.5)),
                    "min_jsonld_quality": float(project.get("min_jsonld_quality", 0.5)),
                })
            st.success(f"{n} pages recalculées.")
            st.rerun()


# =============================================================================
# SECTION 4 : GENERATION
# =============================================================================

def _render_generation_section(sdb, project: dict, user_email: str):
    st.subheader("Génération de sitemaps")

    pages = sdb.get_pages(project["id"], {"status": "active"})
    if not pages:
        st.warning("Aucune page. Importez des données d'abord.")
        return

    from modules.sitemap.engine import SitemapEngine
    engine = SitemapEngine(pages)

    col_seo, col_geo = st.columns(2)

    with col_seo:
        st.markdown("#### Sitemap SEO")
        st.caption(f"{len(pages)} pages actives")
        if st.button("Générer Sitemap SEO", type="primary", key="sitemap_gen_seo", use_container_width=True):
            bar = st.progress(0, "Calcul des priorités SEO...")
            exclude = st.session_state.get("sitemap_seo_exclude", ["legal"])
            result = engine.generate_seo_sitemap(
                {"exclude_content_types": exclude},
                progress_callback=lambda msg, v: bar.progress(min(v, 1.0), msg),
            )
            bar.progress(1.0, "Génération XML...")
            xml = engine.generate_xml(result)
            bar.empty()

            stats = engine.get_stats(result)
            st.success(f"Sitemap SEO généré : **{stats['total']} URLs**")
            st.metric("Priorité moyenne", f"{stats['avg_priority']:.2f}")

            st.download_button(
                "Télécharger sitemap-seo.xml",
                data=xml,
                file_name=f"sitemap-seo-{project['domain'].replace('https://','').replace('http://','').split('/')[0]}.xml",
                mime="application/xml",
                use_container_width=True,
            )

            if st.button("Sauvegarder en base", key="sitemap_save_seo"):
                sdb.save_generation(project["id"], "seo", stats["total"], xml, user_email)
                st.toast("Sitemap SEO sauvegardé.")
                st.rerun()

            with st.expander("Aperçu XML"):
                st.code(xml[:5000], language="xml")

    with col_geo:
        st.markdown("#### Sitemap GEO")
        citable_count = sum(1 for p in pages if p.get("is_citable"))
        st.caption(f"{citable_count} pages citables sur {len(pages)}")
        if st.button("Générer Sitemap GEO", type="primary", key="sitemap_gen_geo", use_container_width=True):
            bar = st.progress(0, "Calcul des priorités GEO...")
            config = {
                "max_urls_geo": st.session_state.get("sitemap_geo_max", int(project.get("max_urls_geo", 500))),
                "min_jsonld_quality": st.session_state.get("sitemap_geo_min_jld", float(project.get("min_jsonld_quality", 0.5))),
                "min_content_quality": st.session_state.get("sitemap_geo_min_cq", float(project.get("min_content_quality", 0.5))),
            }
            result = engine.generate_geo_sitemap(
                config,
                progress_callback=lambda msg, v: bar.progress(min(v, 1.0), msg),
            )
            bar.progress(1.0, "Génération XML...")
            xml = engine.generate_xml(result)
            bar.empty()

            stats = engine.get_stats(result)
            if stats["total"] == 0:
                st.warning("Aucune page citable. Enrichissez vos pages ou ajustez les seuils.")
                return
            st.success(f"Sitemap GEO généré : **{stats['total']} URLs citables**")
            st.metric("Priorité moyenne", f"{stats['avg_priority']:.2f}")

            st.download_button(
                "Télécharger sitemap-geo.xml",
                data=xml,
                file_name=f"sitemap-geo-{project['domain'].replace('https://','').replace('http://','').split('/')[0]}.xml",
                mime="application/xml",
                use_container_width=True,
            )

            if st.button("Sauvegarder en base", key="sitemap_save_geo"):
                sdb.save_generation(project["id"], "geo", stats["total"], xml, user_email)
                st.toast("Sitemap GEO sauvegardé.")
                st.rerun()

            with st.expander("Aperçu XML"):
                st.code(xml[:5000], language="xml")


# =============================================================================
# SECTION 5 : HISTORY
# =============================================================================

def _render_history_section(sdb, project: dict):
    st.subheader("Historique des générations")

    gens = []
    try:
        gens = sdb.get_generations(project["id"])
    except Exception as e:
        st.error(f"Erreur : {str(e)[:150]}")
        return

    if not gens:
        st.info("Aucune génération sauvegardée. Générez un sitemap puis cliquez « Sauvegarder en base ».")
        return

    for g in gens:
        gen_type = g.get("type", "?").upper()
        gen_date = (g.get("generated_at") or "")[:16]
        urls_count = g.get("urls_count", 0)
        gen_id = g.get("id")

        cols = st.columns([1, 2, 1, 1, 1])
        with cols[0]:
            badge_color = "#2196f3" if gen_type == "SEO" else "#4caf50"
            st.markdown(f'<span style="background:{badge_color};color:white;padding:2px 10px;border-radius:4px;font-weight:bold;">{gen_type}</span>', unsafe_allow_html=True)
        with cols[1]:
            st.caption(gen_date)
        with cols[2]:
            st.caption(f"{urls_count} URLs")
        with cols[3]:
            xml_content = g.get("xml_content") or ""
            if xml_content:
                domain = project.get("domain", "site").replace("https://", "").replace("http://", "").split("/")[0]
                st.download_button(
                    "XML",
                    data=xml_content,
                    file_name=f"sitemap-{gen_type.lower()}-{domain}-{gen_id}.xml",
                    mime="application/xml",
                    key=f"dl_gen_{gen_id}",
                )
            else:
                st.caption("—")
        with cols[4]:
            if st.button("Suppr.", key=f"del_gen_{gen_id}"):
                sdb.delete_generation(gen_id)
                st.toast("Génération supprimée.")
                st.rerun()
