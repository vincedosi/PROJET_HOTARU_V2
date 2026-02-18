"""
HOTARU v2 - Audit Database (Supabase / PostgreSQL Backend)
Même interface que core.database.AuditDatabase.
Secrets Streamlit : backend = "supabase", supabase_url, supabase_service_role_key.
"""

import base64
import datetime
import json
import logging
import re
import time
import zlib

from core.runtime import get_secrets, get_session

logger = logging.getLogger(__name__)

_audit_cache = {}
_audit_cache_ttl = 300


class AuditDatabase:
    def __init__(self, secrets: dict = None):
        self.sheet_file = None  # compat app (getattr(db, "sheet_file"))
        self.client = None
        secrets = secrets or get_secrets()
        # Accepter [supabase] ou clés à la racine
        supabase = secrets.get("supabase") or {}
        url = (supabase.get("supabase_url") or secrets.get("supabase_url") or "").strip()
        key = (supabase.get("supabase_service_role_key") or supabase.get("supabase_key") or secrets.get("supabase_service_role_key") or secrets.get("supabase_key") or "").strip()
        if not url or not key:
            logger.error("supabase_url ou supabase_service_role_key manquant")
            return
        try:
            from supabase import create_client
            self.client = create_client(url, key)
        except Exception as e:
            logger.error("Erreur config Supabase: %s", e)
            self.client = None

        self._UNIFIED_MAX_CELL = 45000
        self._U_SAVE_ID, self._U_EMAIL, self._U_WS, self._U_SITE_URL, self._U_NOM, self._U_CREATED = 0, 1, 2, 3, 4, 5
        self._U_CRAWL_CNT, self._U_GEO_SCORE, self._U_GEO_CLUST_CNT, self._U_JSONLD_CNT = 6, 7, 8, 9
        self._U_STATS_PAGES, self._U_STATS_LINKS, self._U_STATS_FILT, self._U_STATS_DUP, self._U_STATS_ERR = 10, 11, 12, 13, 14
        self._U_INFRA_1, self._U_INFRA_2, self._U_INFRA_3, self._U_INFRA_4 = 15, 16, 17, 18
        self._U_CRAWL_1, self._U_CRAWL_2, self._U_GEO_1, self._U_GEO_2, self._U_JSONLD_1, self._U_JSONLD_2 = 19, 20, 21, 22, 23, 24
        self._U_MASTER_1, self._U_MASTER_2 = 25, 26

    def load_user_audits(self, user_email):
        if not self.client:
            return []
        try:
            email_norm = (user_email or "").strip().lower()
            r = self.client.table("audits").select("*").eq("user_email", email_norm).execute()
            cache_key = (user_email or "", str(len(r.data or [])), "")
            now = time.time()
            if cache_key in _audit_cache:
                ct, cv = _audit_cache[cache_key]
                if now - ct < _audit_cache_ttl:
                    return cv
            out = []
            for row in (r.data or []):
                out.append({
                    "audit_id": row.get("audit_id", ""),
                    "user_email": row.get("user_email", ""),
                    "workspace": (row.get("workspace") or "").strip() or "Non classé",
                    "date": row.get("date", ""),
                    "site_url": row.get("site_url", ""),
                    "nb_pages": row.get("nb_pages") or 0,
                    "data_compressed": row.get("data_compressed", ""),
                    "nom_site": row.get("nom_site", "Site Inconnu"),
                    "master_json": row.get("master_json", ""),
                })
            _audit_cache[cache_key] = (now, out)
            return out
        except Exception as e:
            logger.error("Erreur load_user_audits: %s", e)
            return []

    def save_audit(self, user_email, workspace, site_url, nom_site, json_data):
        if not self.client:
            raise ValueError("Impossible de sauvegarder : connexion BDD échouée")
        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            audit_id = str(int(time.time()))
            json_str = json.dumps(json_data)
            compressed = base64.b64encode(zlib.compress(json_str.encode("utf-8"))).decode("ascii")
            final_ws = (workspace or "").strip() or "Non classé"
            self.client.table("audits").insert({
                "audit_id": audit_id,
                "user_email": (user_email or "").strip().lower(),
                "workspace": final_ws,
                "date": date_str,
                "site_url": (site_url or "")[:500],
                "nb_pages": len(json_data.get("results", [])),
                "data_compressed": compressed,
                "nom_site": (nom_site or "Site")[:200],
            }).execute()
            session = get_session()
            session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
            return True
        except Exception as e:
            logger.error("Erreur save_audit Supabase: %s", e)
            raise

    def save_master_for_audit(self, user_email, workspace, site_url, master_json):
        if not self.client:
            raise ValueError("Impossible de sauvegarder le MASTER : connexion BDD échouée")
        try:
            email_norm = (user_email or "").strip().lower()
            ws_norm = (workspace or "").strip() or "Non classé"
            url_norm = (site_url or "").strip()
            r = self.client.table("audits").select("id", "date").eq("user_email", email_norm).eq("workspace", ws_norm).eq("site_url", url_norm).order("date", desc=True).limit(1).execute()
            if not r.data or len(r.data) == 0:
                raise ValueError("Aucun audit correspondant pour ce MASTER.")
            row_id = r.data[0]["id"]
            self.client.table("audits").update({"master_json": (master_json or "")}).eq("id", row_id).execute()
            session = get_session()
            session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error("Erreur save_master_for_audit: %s", e)
            raise

    def _get_jsonld_worksheet(self):
        return True  # pas d'onglet ; save_jsonld_models écrit dans la table jsonld

    def _compress_for_sheet(self, data, max_chars: int):
        if data is None:
            return ""
        raw = json.dumps(data, ensure_ascii=False)
        if len(raw) <= max_chars:
            return raw
        compressed = base64.b64encode(zlib.compress(raw.encode("utf-8"))).decode("ascii")
        return compressed if len(compressed) <= max_chars else raw[:max_chars]

    def save_jsonld_models(self, user_email: str, site_url: str, workspace: str, models_data: list) -> bool:
        if not self.client:
            return False
        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            final_ws = (workspace or "").strip() or "Non classé"
            site_url_trim = (site_url or "")[:500]
            rows = []
            for i, m in enumerate(models_data):
                model_name = (m.get("model_name") or "").strip() or f"Cluster {i + 1}"
                model_id = re.sub(r"[^a-z0-9_]", "_", model_name.lower())[:100] or "cluster_{}".format(i + 1)
                schema_type = (m.get("schema_type") or "").strip()[:100] or "WebPage"
                page_count = m.get("page_count", 0)
                url_pattern = (m.get("url_pattern") or "")[:300]
                sample_urls_str = json.dumps((m.get("sample_urls") or [])[:5], ensure_ascii=False)
                if len(sample_urls_str) > 2000:
                    sample_urls_str = base64.b64encode(zlib.compress(sample_urls_str.encode())).decode("ascii")
                dom_str = self._compress_for_sheet(m.get("dom_structure"), 5000)
                existing_str = self._compress_for_sheet(m.get("existing_jsonld"), 50000)
                optimized_str = self._compress_for_sheet(m.get("optimized_jsonld"), 50000)
                rows.append({
                    "site_url": site_url_trim,
                    "model_id": model_id,
                    "model_name": model_name[:200],
                    "page_count": page_count,
                    "url_pattern": url_pattern,
                    "sample_urls": sample_urls_str[:2000],
                    "dom_structure": (dom_str or "")[:5000],
                    "existing_jsonld": (existing_str or "")[:50000],
                    "recommended_schema": schema_type,
                    "optimized_jsonld": (optimized_str or "")[:50000],
                    "created_at": date_str,
                    "workspace": final_ws[:200],
                    "user_email": (user_email or "").strip().lower(),
                })
            if rows:
                self.client.table("jsonld").insert(rows).execute()
            return True
        except Exception as e:
            logger.error("Erreur save_jsonld_models Supabase: %s", e)
            raise

    def _decompress_from_sheet(self, s: str):
        if not s or not (s or "").strip():
            return None
        s = (s or "").strip()
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        try:
            raw = base64.b64decode(s)
            return json.loads(zlib.decompress(raw).decode("utf-8"))
        except (base64.binascii.Error, zlib.error, json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("_cells_to_json: decompression/parse failed for input length=%d", len(s))
            return None

    def list_jsonld_sites(self, user_email: str):
        models = self.load_jsonld_models(user_email, site_url=None)
        seen = {}
        for m in models:
            key = (m.get("site_url") or "", m.get("workspace") or "Non classé")
            if key not in seen or (m.get("created_at") or "") > (seen[key].get("created_at") or ""):
                seen[key] = {"site_url": key[0], "workspace": key[1], "created_at": m.get("created_at", "")}
        return list(seen.values())

    def load_jsonld_models(self, user_email: str, site_url: str = None):
        if not self.client:
            return []
        try:
            email_norm = (user_email or "").strip().lower()
            q = self.client.table("jsonld").select("*").eq("user_email", email_norm)
            if site_url and (site_url or "").strip():
                q = q.eq("site_url", (site_url or "").strip())
            r = q.execute()
            models = []
            for row in (r.data or []):
                models.append({
                    "site_url": row.get("site_url", ""),
                    "model_id": row.get("model_id", ""),
                    "model_name": row.get("model_name", ""),
                    "page_count": int(row.get("page_count") or 0),
                    "url_pattern": row.get("url_pattern", ""),
                    "sample_urls": row.get("sample_urls", ""),
                    "dom_structure": row.get("dom_structure", ""),
                    "existing_jsonld": row.get("existing_jsonld", ""),
                    "recommended_schema": row.get("recommended_schema", ""),
                    "optimized_jsonld": row.get("optimized_jsonld", ""),
                    "created_at": row.get("created_at", ""),
                    "workspace": row.get("workspace", ""),
                })
            return models
        except Exception as e:
            logger.error("Erreur load_jsonld_models: %s", e)
            return []

    def _json_to_cells(self, data, max_chars=None):
        if data is None:
            return []
        max_chars = max_chars or self._UNIFIED_MAX_CELL
        raw = json.dumps(data, ensure_ascii=False)
        if not raw:
            return []
        chunks = []
        s = raw
        while s:
            chunks.append(s[:max_chars])
            s = s[max_chars:]
        if len(chunks) > 2:
            try:
                compressed = base64.b64encode(zlib.compress(raw.encode("utf-8"))).decode("ascii")
            except Exception:
                compressed = raw
            chunks = []
            s = compressed
            while s:
                chunks.append(s[:max_chars])
                s = s[max_chars:]
        return chunks[:2]

    def _cells_to_json(self, row, start_idx, max_cols=2):
        if isinstance(row, dict):
            keys = ["crawl_data_1", "crawl_data_2", "geo_data_1", "geo_data_2", "jsonld_data_1", "jsonld_data_2", "master_json_1", "master_json_2"]
            key_map = {19: "crawl_data_1", 20: "crawl_data_2", 21: "geo_data_1", 22: "geo_data_2", 23: "jsonld_data_1", 24: "jsonld_data_2", 25: "master_json_1", 26: "master_json_2"}
            parts = []
            for i in range(max_cols):
                k = key_map.get(start_idx + i)
                if k:
                    parts.append((row.get(k) or "").strip())
                else:
                    parts.append("")
            joined = "".join(parts)
        else:
            parts = []
            for i in range(max_cols):
                idx = start_idx + i
                if idx < len(row):
                    parts.append((row[idx] or "").strip())
                else:
                    parts.append("")
            joined = "".join(parts)
        if not joined:
            return None
        try:
            return json.loads(joined)
        except (json.JSONDecodeError, ValueError):
            pass
        try:
            decoded = base64.b64decode(joined)
            decompressed = zlib.decompress(decoded).decode("utf-8")
            return json.loads(decompressed)
        except (base64.binascii.Error, zlib.error, json.JSONDecodeError, UnicodeDecodeError, ValueError):
            logger.warning("_reassemble_json: failed to parse/decompress data (length=%d)", len(joined))
            return None

    def save_unified(self, user_email: str, workspace: str, site_url: str, nom_site: str,
                     crawl_data: list, geo_data: dict = None, jsonld_data: list = None,
                     master_json: str = None) -> str:
        if not self.client:
            raise ValueError("Connexion Supabase indisponible")
        try:
            save_id = str(int(time.time()))
            created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            final_ws = (workspace or "").strip() or "Non classé"
            site_url = (site_url or "")[:500]
            nom_site = (nom_site or "Site")[:200]
            crawl_pages_count = len(crawl_data) if crawl_data else 0
            geo_score_val = (geo_data or {}).get("geo_score")
            geo_score_str = str(int(geo_score_val)) if geo_score_val is not None else ""
            geo_clusters = (geo_data or {}).get("clusters") or {}
            geo_clusters_count = len(geo_clusters) if isinstance(geo_clusters, dict) else 0
            jsonld_models_count = len(jsonld_data) if jsonld_data else 0
            stats = (geo_data or {}).get("stats") or {}
            infra = (geo_data or {}).get("geo_infra") or {}
            infra_names = list(infra.keys())[:4] if isinstance(infra, dict) else []
            infra_vals = []
            for i in range(4):
                name = infra_names[i] if i < len(infra_names) else ""
                if name and infra.get(name):
                    status = "Present" if infra[name].get("status") else "Absent"
                    infra_vals.append("{}:{}".format(name, status))
                else:
                    infra_vals.append("")
            crawl_chunks = self._json_to_cells(crawl_data)
            geo_chunks = self._json_to_cells(geo_data)
            jsonld_chunks = self._json_to_cells(jsonld_data)
            master_str = (master_json or "").strip() if isinstance(master_json, str) else ""
            master_chunks = []
            if master_str:
                for i in range(0, len(master_str), self._UNIFIED_MAX_CELL):
                    master_chunks.append(master_str[i:i + self._UNIFIED_MAX_CELL])
            payload = {
                "save_id": save_id,
                "user_email": (user_email or "").strip().lower(),
                "workspace": final_ws,
                "site_url": site_url,
                "nom_site": nom_site,
                "created_at": created_at,
                "crawl_pages_count": crawl_pages_count,
                "geo_score": geo_score_str,
                "geo_clusters_count": geo_clusters_count,
                "jsonld_models_count": jsonld_models_count,
                "geo_stats_pages_crawled": stats.get("pages_crawled", ""),
                "geo_stats_links_discovered": stats.get("links_discovered", ""),
                "geo_stats_links_filtered": stats.get("links_filtered", ""),
                "geo_stats_links_duplicate": stats.get("links_duplicate", ""),
                "geo_stats_errors": stats.get("errors", ""),
                "geo_infra_1": infra_vals[0] if len(infra_vals) > 0 else "",
                "geo_infra_2": infra_vals[1] if len(infra_vals) > 1 else "",
                "geo_infra_3": infra_vals[2] if len(infra_vals) > 2 else "",
                "geo_infra_4": infra_vals[3] if len(infra_vals) > 3 else "",
                "crawl_data_1": crawl_chunks[0] if len(crawl_chunks) > 0 else "",
                "crawl_data_2": crawl_chunks[1] if len(crawl_chunks) > 1 else "",
                "geo_data_1": geo_chunks[0] if len(geo_chunks) > 0 else "",
                "geo_data_2": geo_chunks[1] if len(geo_chunks) > 1 else "",
                "jsonld_data_1": jsonld_chunks[0] if len(jsonld_chunks) > 0 else "",
                "jsonld_data_2": jsonld_chunks[1] if len(jsonld_chunks) > 1 else "",
                "master_json_1": master_chunks[0] if len(master_chunks) > 0 else "",
                "master_json_2": master_chunks[1] if len(master_chunks) > 1 else "",
            }
            self.client.table("unified_saves").insert(payload).execute()
            session = get_session()
            session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
            return save_id
        except Exception as e:
            logger.error("Erreur save_unified Supabase: %s", e)
            raise

    def list_unified_saves(self, user_email: str, workspace: str = None):
        if not self.client:
            return []
        try:
            email_norm = (user_email or "").strip().lower()
            if not email_norm:
                return []
            q = self.client.table("unified_saves").select("*").eq("user_email", email_norm)
            if workspace and (workspace or "").strip():
                q = q.eq("workspace", (workspace or "").strip())
            r = q.order("created_at", desc=True).execute()
            out = []
            for row in (r.data or []):
                row_ws = (row.get("workspace") or "").strip() or "Non classé"
                has_geo = bool((row.get("geo_data_1") or "").strip())
                has_jsonld = bool((row.get("jsonld_data_1") or "").strip())
                has_master = bool((row.get("master_json_1") or "").strip())
                out.append({
                    "save_id": row.get("save_id", ""),
                    "site_url": row.get("site_url", ""),
                    "nom_site": row.get("nom_site", "Site"),
                    "created_at": row.get("created_at", ""),
                    "workspace": row_ws,
                    "has_geo": has_geo,
                    "has_jsonld": has_jsonld,
                    "has_master": has_master,
                })
            return sorted(out, key=lambda x: (x.get("created_at") or ""), reverse=True)
        except Exception as e:
            logger.error("Erreur list_unified_saves: %s", e)
            return []

    def load_unified(self, save_id: str, user_email: str) -> dict:
        if not self.client:
            return None
        try:
            email_norm = (user_email or "").strip().lower()
            r = self.client.table("unified_saves").select("*").eq("save_id", str(save_id).strip()).eq("user_email", email_norm).limit(1).execute()
            if not r.data or len(r.data) == 0:
                return None
            row = r.data[0]
            crawl_data = self._cells_to_json(row, self._U_CRAWL_1, 2)
            geo_data = self._cells_to_json(row, self._U_GEO_1, 2)
            jsonld_data = self._cells_to_json(row, self._U_JSONLD_1, 2)
            master_json_val = ((row.get("master_json_1") or "") + (row.get("master_json_2") or "")).strip()
            return {
                "site_url": row.get("site_url", ""),
                "nom_site": row.get("nom_site", "Site"),
                "workspace": (row.get("workspace") or "").strip() or "Non classé",
                "created_at": row.get("created_at", ""),
                "crawl_data": crawl_data,
                "geo_data": geo_data,
                "jsonld_data": jsonld_data,
                "master_json": master_json_val,
            }
        except Exception as e:
            logger.error("Erreur load_unified: %s", e)
            return None

    def update_master_for_unified(self, user_email: str, workspace: str, site_url: str, master_json: str) -> bool:
        if not self.client:
            return False
        try:
            master_str = (master_json or "").strip() if isinstance(master_json, str) else ""
            master_chunks = []
            if master_str:
                for i in range(0, len(master_str), self._UNIFIED_MAX_CELL):
                    master_chunks.append(master_str[i:i + self._UNIFIED_MAX_CELL])
            email_norm = (user_email or "").strip().lower()
            ws_norm = (workspace or "").strip() or "Non classé"
            site_norm = (site_url or "").strip()
            r = self.client.table("unified_saves").select("id").eq("user_email", email_norm).eq("workspace", ws_norm).eq("site_url", site_norm).order("created_at", desc=True).limit(1).execute()
            if not r.data or len(r.data) == 0:
                return self._append_unified_master_only(user_email, workspace, site_url, master_chunks)
            row_id = r.data[0]["id"]
            self.client.table("unified_saves").update({
                "master_json_1": master_chunks[0] if len(master_chunks) > 0 else "",
                "master_json_2": master_chunks[1] if len(master_chunks) > 1 else "",
            }).eq("id", row_id).execute()
            session = get_session()
            session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
            return True
        except Exception as e:
            logger.error("Erreur update_master_for_unified: %s", e)
            return False

    def _append_unified_master_only(self, user_email: str, workspace: str, site_url: str, master_chunks: list) -> bool:
        if not self.client:
            return False
        try:
            save_id = str(int(time.time()))
            created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            final_ws = (workspace or "").strip() or "Non classé"
            payload = {
                "save_id": save_id,
                "user_email": (user_email or "").strip().lower(),
                "workspace": final_ws,
                "site_url": (site_url or "")[:500],
                "nom_site": "Site",
                "created_at": created_at,
                "master_json_1": master_chunks[0] if len(master_chunks) > 0 else "",
                "master_json_2": master_chunks[1] if len(master_chunks) > 1 else "",
            }
            self.client.table("unified_saves").insert(payload).execute()
            session = get_session()
            session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
            return True
        except Exception as e:
            logger.error("Erreur _append_unified_master_only: %s", e)
            return False

    def get_user_workspaces(self, user_email: str) -> list:
        """Liste des workspaces auxquels l'utilisateur a accès (vide = tous)."""
        if not self.client:
            logger.warning("get_user_workspaces: client Supabase est None")
            return []
        try:
            email_norm = (user_email or "").strip().lower()
            r = self.client.table("user_workspace_access").select("workspace_name").eq("user_email", email_norm).execute()
            out = [(row.get("workspace_name") or "").strip() for row in (r.data or []) if (row.get("workspace_name") or "").strip()]
            logger.debug("get_user_workspaces('%s') → %s", email_norm, out)
            return out
        except Exception as e:
            logger.error("get_user_workspaces('%s') EXCEPTION: %s", user_email, e, exc_info=True)
            return []

    def set_user_workspaces(self, user_email: str, workspace_names: list) -> bool:
        """Remplace la liste des workspaces accessibles pour un utilisateur."""
        logger.info("set_user_workspaces('%s', %s) — début", user_email, workspace_names)
        if not self.client:
            logger.error("set_user_workspaces: client Supabase est None")
            return False
        try:
            email_norm = (user_email or "").strip().lower()
            logger.debug("set_user_workspaces: DELETE FROM user_workspace_access WHERE user_email='%s'", email_norm)
            self.client.table("user_workspace_access").delete().eq("user_email", email_norm).execute()
            for wn in (workspace_names or []):
                name = (wn or "").strip()
                if name:
                    logger.debug("set_user_workspaces: INSERT ('%s', '%s')", email_norm, name)
                    self.client.table("user_workspace_access").insert({"user_email": email_norm, "workspace_name": name}).execute()
            logger.info("set_user_workspaces('%s', %s) → OK", email_norm, workspace_names)
            return True
        except Exception as e:
            logger.error("set_user_workspaces('%s') EXCEPTION: %s", user_email, e, exc_info=True)
            raise

    def list_all_workspaces(self) -> list:
        """Liste tous les noms de workspaces distincts (unified_saves + user_workspace_access)."""
        if not self.client:
            logger.warning("list_all_workspaces: client Supabase est None")
            return []
        try:
            seen = set()
            out = []
            logger.debug("list_all_workspaces: requête unified_saves...")
            r = self.client.table("unified_saves").select("workspace").execute()
            logger.debug("list_all_workspaces: unified_saves → %d rows", len(r.data or []))
            for row in (r.data or []):
                w = (row.get("workspace") or "").strip() or "Non classé"
                if w not in seen:
                    seen.add(w)
                    out.append(w)
            logger.debug("list_all_workspaces: requête user_workspace_access...")
            try:
                r2 = self.client.table("user_workspace_access").select("workspace_name").execute()
                logger.debug("list_all_workspaces: user_workspace_access → %d rows", len(r2.data or []))
                for row in (r2.data or []):
                    w = (row.get("workspace_name") or "").strip()
                    if w and w not in seen:
                        seen.add(w)
                        out.append(w)
            except Exception as e2:
                if "PGRST205" in str(e2):
                    logger.warning("list_all_workspaces: table user_workspace_access introuvable (PGRST205) — NOTIFY pgrst, 'reload schema'; dans le SQL Editor")
                else:
                    logger.warning("list_all_workspaces: erreur user_workspace_access: %s", e2)
            result = sorted(out)
            logger.info("list_all_workspaces → %d workspace(s): %s", len(result), result)
            return result
        except Exception as e:
            logger.error("Erreur list_all_workspaces: %s", e, exc_info=True)
            return []

    # ─── Workspace CRUD (backoffice) ─────────────────────────────────────────

    def _has_workspace_access_table(self) -> bool:
        """Check if user_workspace_access table is reachable."""
        if not self.client:
            return False
        try:
            self.client.table("user_workspace_access").select("id").limit(1).execute()
            return True
        except Exception as e:
            if "PGRST205" in str(e) or "schema cache" in str(e).lower():
                logger.warning("Table user_workspace_access introuvable (PGRST205). Fallback unified_saves.")
                return False
            return False

    def create_workspace(self, name: str) -> bool:
        """Register a new workspace. Uses user_workspace_access if available, otherwise unified_saves fallback."""
        logger.info("create_workspace('%s') — début", name)
        if not self.client:
            logger.error("create_workspace: client Supabase est None")
            raise ValueError("Connexion Supabase indisponible")
        name = (name or "").strip()
        if not name:
            logger.warning("create_workspace: nom vide")
            raise ValueError("Nom de workspace requis")

        existing = self.list_all_workspaces()
        if name in existing:
            raise ValueError(f"Le workspace « {name} » existe déjà.")

        if self._has_workspace_access_table():
            try:
                logger.debug("create_workspace: INSERT into user_workspace_access (workspace_name='%s')", name)
                result = self.client.table("user_workspace_access").insert({
                    "user_email": "__workspace_registry__",
                    "workspace_name": name,
                }).execute()
                logger.info("create_workspace('%s') → OK via user_workspace_access", name)
                return True
            except Exception as e:
                err_str = str(e)
                logger.error("create_workspace('%s') EXCEPTION user_workspace_access: %s", name, err_str, exc_info=True)
                if "duplicate" in err_str.lower() or "unique" in err_str.lower() or "23505" in err_str:
                    raise ValueError(f"Le workspace « {name} » existe déjà.")
                raise

        logger.info("create_workspace: fallback → unified_saves placeholder pour '%s'", name)
        try:
            import uuid
            placeholder_id = f"__ws_placeholder_{uuid.uuid4().hex[:8]}"
            self.client.table("unified_saves").insert({
                "save_id": placeholder_id,
                "user_email": "__workspace_registry__",
                "workspace": name,
                "site_url": "",
                "nom_site": f"[workspace:{name}]",
                "created_at": "",
            }).execute()
            logger.info("create_workspace('%s') → OK via unified_saves fallback", name)
            return True
        except Exception as e2:
            logger.error("create_workspace('%s') EXCEPTION fallback: %s", name, e2, exc_info=True)
            raise ValueError(f"Échec création workspace : {str(e2)[:200]}")

    def rename_workspace(self, old_name: str, new_name: str) -> bool:
        """Rename workspace across all tables."""
        logger.info("rename_workspace('%s' → '%s') — début", old_name, new_name)
        if not self.client:
            logger.error("rename_workspace: client Supabase est None")
            raise ValueError("Connexion Supabase indisponible")
        old = (old_name or "").strip()
        new = (new_name or "").strip()
        if not old or not new or old == new:
            raise ValueError("Ancien et nouveau nom requis (et différents)")
        has_access_table = self._has_workspace_access_table()
        tables = [("unified_saves", "workspace"), ("jsonld", "workspace"), ("audits", "workspace")]
        if has_access_table:
            tables.append(("user_workspace_access", "workspace_name"))
        try:
            for table, col in tables:
                try:
                    logger.debug("rename_workspace: UPDATE %s SET %s='%s' WHERE %s='%s'", table, col, new, col, old)
                    self.client.table(table).update({col: new}).eq(col, old).execute()
                except Exception as te:
                    if "PGRST205" in str(te):
                        logger.warning("rename_workspace: table %s introuvable — skipped", table)
                    else:
                        raise
            logger.info("rename_workspace('%s' → '%s') → OK", old, new)
            return True
        except Exception as e:
            logger.error("rename_workspace('%s' → '%s') EXCEPTION: %s", old, new, e, exc_info=True)
            raise

    def move_saves_to_workspace(self, save_ids: list, target_workspace: str) -> int:
        """Move saves to target workspace. Returns count of moved saves."""
        logger.info("move_saves_to_workspace(ids=%s, target='%s') — début", save_ids, target_workspace)
        if not self.client:
            logger.error("move_saves_to_workspace: client Supabase est None")
            return 0
        try:
            target = (target_workspace or "").strip() or "Non classé"
            moved = 0
            for sid in (save_ids or []):
                sid_str = str(sid).strip()
                logger.debug("move_saves_to_workspace: UPDATE unified_saves SET workspace='%s' WHERE save_id='%s'", target, sid_str)
                self.client.table("unified_saves").update({"workspace": target}).eq("save_id", sid_str).execute()
                moved += 1
            logger.info("move_saves_to_workspace → %d déplacée(s)", moved)
            return moved
        except Exception as e:
            logger.error("move_saves_to_workspace EXCEPTION: %s", e, exc_info=True)
            return 0

    def list_workspace_saves_admin(self, workspace: str) -> list:
        """List all saves in a workspace (admin, no user filter). Excludes fallback placeholders."""
        logger.debug("list_workspace_saves_admin('%s')...", workspace)
        if not self.client:
            logger.warning("list_workspace_saves_admin: client Supabase est None")
            return []
        try:
            ws = (workspace or "").strip()
            if not ws:
                return []
            r = self.client.table("unified_saves").select(
                "save_id,user_email,site_url,nom_site,created_at,workspace"
            ).eq("workspace", ws).order("created_at", desc=True).execute()
            out = [
                {
                    "save_id": row.get("save_id", ""),
                    "user_email": row.get("user_email", ""),
                    "site_url": row.get("site_url", ""),
                    "nom_site": row.get("nom_site", "Site"),
                    "created_at": row.get("created_at", ""),
                    "workspace": (row.get("workspace") or "").strip() or "Non classé",
                }
                for row in (r.data or [])
                if not (row.get("save_id") or "").startswith("__ws_placeholder_")
            ]
            logger.info("list_workspace_saves_admin('%s') → %d save(s)", ws, len(out))
            return out
        except Exception as e:
            logger.error("list_workspace_saves_admin('%s') EXCEPTION: %s", workspace, e, exc_info=True)
            return []
