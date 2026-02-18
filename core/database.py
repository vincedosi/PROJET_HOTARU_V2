"""
HOTARU v2 - Audit Database (Google Sheets Backend)
Agnostique UI : utilise core.runtime pour secrets et session.
"""

import base64
import datetime
import json
import logging
import re
import time
import zlib

import gspread
from google.oauth2.service_account import Credentials

from core.runtime import get_secrets, get_session

logger = logging.getLogger(__name__)

# Cache simple (ttl 300s) pour _process_user_audits
_audit_cache = {}
_audit_cache_ttl = 300


def _process_user_audits(all_rows_list, user_email):
    """Traite les lignes du sheet pour extraire les audits utilisateur."""
    if not all_rows_list or len(all_rows_list) < 2:
        return []

    data_rows = all_rows_list[1:]
    user_audits = []
    email_normalized = (user_email or "").strip().lower()

    for row in data_rows:
        if len(row) < 2:
            continue
        row_email = (row[1] or "").strip().lower()
        if row_email != email_normalized:
            continue

        workspace_value = row[2] if len(row) > 2 else ""
        master_json = row[9] if len(row) > 9 else ""

        audit = {
            "audit_id": row[0],
            "user_email": row[1],
            "workspace": workspace_value.strip() if workspace_value.strip() else "Non classé",
            "date": row[3] if len(row) > 3 else "",
            "site_url": row[4] if len(row) > 4 else "",
            "nb_pages": row[5] if len(row) > 5 else 0,
            "data_compressed": row[6] if len(row) > 6 else "",
            "nom_site": row[7] if len(row) > 7 else "Site Inconnu",
            "master_json": master_json,
        }
        user_audits.append(audit)

    return user_audits


class AuditDatabase:
    def __init__(self, secrets: dict = None):
        self.client = None
        self.sheet_file = None
        self.sheet = None
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        secrets = secrets or get_secrets()

        try:
            gcp = secrets.get("gcp_service_account")
            if not gcp:
                logger.error("gcp_service_account manquant dans les secrets")
                return
            self.creds = Credentials.from_service_account_info(gcp, scopes=self.scope)
            self.client = gspread.authorize(self.creds)
        except Exception as e:
            logger.error("Erreur de configuration Secrets (GCP): %s", e)
            return

        try:
            sheet_url = secrets.get("sheet_url", "")
            if not sheet_url:
                logger.error("URL du Google Sheet manquante dans les secrets")
                return

            self.sheet_file = self.client.open_by_url(sheet_url)
            try:
                self.sheet = self.sheet_file.worksheet("audits")
            except Exception:
                self.sheet = self.sheet_file.sheet1
        except Exception as e:
            logger.error("Impossible d'ouvrir le GSheet: %s", e)
            self.sheet_file = None
            self.sheet = None
            return

    def load_user_audits(self, user_email):
        """Charge uniquement les audits de l'utilisateur connecté (isolation SaaS)."""
        if not self.sheet:
            return []

        try:
            all_rows = self.sheet.get_all_values()
            # Cache simple par (user_email, hash des données)
            cache_key = (user_email or "", str(len(all_rows)), all_rows[0][0] if all_rows else "")
            now = time.time()
            if cache_key in _audit_cache:
                cached_time, cached_val = _audit_cache[cache_key]
                if now - cached_time < _audit_cache_ttl:
                    return cached_val
            result = _process_user_audits(all_rows, user_email)
            _audit_cache[cache_key] = (now, result)
            return result
        except Exception as e:
            logger.error("Erreur lors de la lecture des audits: %s", e)
            return []

    def save_audit(self, user_email, workspace, site_url, nom_site, json_data):
        if not self.sheet:
            raise ValueError("Impossible de sauvegarder : connexion BDD échouée")

        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            audit_id = f"{int(time.time())}"

            json_str = json.dumps(json_data)
            compressed = base64.b64encode(
                zlib.compress(json_str.encode("utf-8"))
            ).decode("ascii")

            final_ws = workspace if workspace and workspace.strip() else "Non classé"

            new_row = [
                audit_id,
                user_email,
                final_ws,
                date_str,
                site_url,
                len(json_data.get("results", [])),
                compressed,
                nom_site,
            ]

            self.sheet.append_row(new_row)
            session = get_session()
            session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
            return True
        except Exception as e:
            logger.error("Erreur de sauvegarde GSheet: %s", e)
            raise

    def save_master_for_audit(self, user_email, workspace, site_url, master_json):
        """Sauvegarde le JSON-LD Master dans la colonne J de l'onglet audits."""
        if not self.sheet:
            raise ValueError("Impossible de sauvegarder le MASTER : connexion BDD échouée")

        try:
            all_rows = self.sheet.get_all_values()
            if len(all_rows) < 2:
                raise ValueError("Aucun audit existant pour enregistrer le MASTER.")

            email_normalized = (user_email or "").strip().lower()
            ws_normalized = (workspace or "").strip()
            url_normalized = (site_url or "").strip()

            for idx, row in enumerate(all_rows[1:], start=2):
                if len(row) < 5:
                    continue
                row_email = (row[1] or "").strip().lower()
                row_ws = (row[2] or "").strip()
                row_url = (row[4] or "").strip()

                if (
                    row_email == email_normalized
                    and row_ws == ws_normalized
                    and row_url == url_normalized
                ):
                    self.sheet.update_cell(idx, 10, master_json)
                    session = get_session()
                    session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
                    return True

            raise ValueError("Aucune ligne d'audit correspondante trouvée pour ce MASTER.")
        except ValueError:
            raise
        except Exception as e:
            logger.error("Erreur de sauvegarde MASTER GSheet: %s", e)
            raise

    def _get_jsonld_worksheet(self):
        """Retourne l'onglet 'jsonld', le crée si absent avec en-têtes."""
        if not self.sheet_file:
            return None
        try:
            ws = self.sheet_file.worksheet("jsonld")
            if ws.row_count == 0 or not ws.get_all_values():
                headers = [
                    "site_url", "model_id", "model_name", "page_count", "url_pattern",
                    "sample_urls", "dom_structure", "existing_jsonld", "recommended_schema",
                    "optimized_jsonld", "created_at", "workspace", "user_email"
                ]
                ws.append_row(headers)
            return ws
        except Exception:
            try:
                ws = self.sheet_file.add_worksheet(title="jsonld", rows=1000, cols=15)
                headers = [
                    "site_url", "model_id", "model_name", "page_count", "url_pattern",
                    "sample_urls", "dom_structure", "existing_jsonld", "recommended_schema",
                    "optimized_jsonld", "created_at", "workspace", "user_email"
                ]
                ws.append_row(headers)
                return ws
            except Exception as e:
                logger.error("Impossible de créer l'onglet jsonld: %s", e)
                return None

    def _compress_for_sheet(self, data, max_chars: int):
        """Compresse JSON avec zlib+base64. Si > max_chars, tronque."""
        if data is None:
            return ""
        raw = json.dumps(data, ensure_ascii=False)
        if len(raw) <= max_chars:
            return raw
        compressed = base64.b64encode(zlib.compress(raw.encode("utf-8"))).decode("ascii")
        if len(compressed) <= max_chars:
            return compressed
        if isinstance(data, dict):
            data_copy = dict(data)
            data_copy["_truncated"] = True
            return json.dumps(data_copy, ensure_ascii=False)[:max_chars]
        return raw[:max_chars]

    def save_jsonld_models(self, user_email: str, site_url: str, workspace: str, models_data: list) -> bool:
        """Sauvegarde les modèles JSON-LD dans l'onglet 'jsonld' du Google Sheet."""
        ws = self._get_jsonld_worksheet()
        if not ws:
            return False

        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            final_ws = (workspace or "").strip() or "Non classé"
            site_url_trim = (site_url or "")[:500]

            rows = []
            for i, m in enumerate(models_data):
                model_name = (m.get("model_name") or "").strip() or f"Cluster {i + 1}"
                model_id = re.sub(r"[^a-z0-9_]", "_", model_name.lower())[:100] or f"cluster_{i}"
                schema_type = (m.get("schema_type") or "").strip()[:100] or "WebPage"
                page_count = m.get("page_count", 0)
                url_pattern = (m.get("url_pattern") or "")[:300]
                sample_urls_str = json.dumps((m.get("sample_urls") or [])[:5], ensure_ascii=False)
                if len(sample_urls_str) > 2000:
                    sample_urls_str = base64.b64encode(zlib.compress(sample_urls_str.encode())).decode("ascii")
                dom_str = self._compress_for_sheet(m.get("dom_structure"), 5000)
                existing_str = self._compress_for_sheet(m.get("existing_jsonld"), 50000)
                optimized_str = self._compress_for_sheet(m.get("optimized_jsonld"), 50000)

                rows.append([
                    site_url_trim,
                    model_id,
                    model_name[:200],
                    page_count,
                    url_pattern,
                    sample_urls_str[:2000],
                    dom_str[:5000],
                    existing_str[:50000],
                    schema_type,
                    optimized_str[:50000],
                    date_str,
                    final_ws[:200],
                    user_email,
                ])
            if rows:
                ws.append_rows(rows, value_input_option="RAW")
            return True
        except Exception as e:
            logger.error("Erreur sauvegarde JSON-LD GSheet: %s", e)
            raise

    def _decompress_from_sheet(self, s: str):
        """Parse une chaîne du Sheet : JSON brut ou base64+zlib."""
        if not s or not s.strip():
            return None
        s = s.strip()
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        try:
            raw = base64.b64decode(s)
            return json.loads(zlib.decompress(raw).decode("utf-8"))
        except Exception:
            return None

    def list_jsonld_sites(self, user_email: str):
        """Retourne la liste des (site_url, workspace) sauvegardés pour l'utilisateur."""
        models = self.load_jsonld_models(user_email, site_url=None)
        seen = {}
        for m in models:
            key = (m.get("site_url") or "", m.get("workspace") or "Non classé")
            if key not in seen or (m.get("created_at") or "") > (seen[key].get("created_at") or ""):
                seen[key] = {"site_url": key[0], "workspace": key[1], "created_at": m.get("created_at", "")}
        return list(seen.values())

    def load_jsonld_models(self, user_email: str, site_url: str = None):
        """Charge les modèles JSON-LD depuis l'onglet 'jsonld'."""
        ws = self._get_jsonld_worksheet()
        if not ws:
            return []

        try:
            all_rows = ws.get_all_values()
            if len(all_rows) < 2:
                return []
            email_norm = (user_email or "").strip().lower()
            url_norm = (site_url or "").strip() if site_url else None
            models = []
            for row in all_rows[1:]:
                if len(row) < 5:
                    continue
                row_email = (row[12] if len(row) > 12 else "").strip().lower()
                if row_email != email_norm:
                    continue
                row_url = (row[0] or "").strip()
                if url_norm and row_url != url_norm:
                    continue
                models.append({
                    "site_url": row[0],
                    "model_id": row[1],
                    "model_name": row[2],
                    "page_count": int(row[3]) if row[3] else 0,
                    "url_pattern": row[4] if len(row) > 4 else "",
                    "sample_urls": row[5] if len(row) > 5 else "",
                    "dom_structure": row[6] if len(row) > 6 else "",
                    "existing_jsonld": row[7] if len(row) > 7 else "",
                    "recommended_schema": row[8] if len(row) > 8 else "",
                    "optimized_jsonld": row[9] if len(row) > 9 else "",
                    "created_at": row[10] if len(row) > 10 else "",
                    "workspace": row[11] if len(row) > 11 else "",
                })
            return models
        except Exception as e:
            logger.error("Erreur lecture JSON-LD GSheet: %s", e)
            return []

    # =========================================================================
    # SAUVEGARDES UNIFIÉES (onglet unified_saves) — 100 % décomposé, aucune compression
    # Données en JSON brut (lisible). Si > 45k caractères, réparti sur plusieurs colonnes.
    # =========================================================================

    _UNIFIED_MAX_CELL = 45000  # limite Google Sheets ~50k

    UNIFIED_HEADERS = [
        "save_id", "user_email", "workspace", "site_url", "nom_site", "created_at",
        "crawl_pages_count", "geo_score", "geo_clusters_count", "jsonld_models_count",
        "geo_stats_pages_crawled", "geo_stats_links_discovered", "geo_stats_links_filtered",
        "geo_stats_links_duplicate", "geo_stats_errors",
        "geo_infra_1", "geo_infra_2", "geo_infra_3", "geo_infra_4",
        "crawl_data_1", "crawl_data_2", "geo_data_1", "geo_data_2", "jsonld_data_1", "jsonld_data_2",
        "master_json_1", "master_json_2",
    ]
    UNIFIED_COLS = 27

    # Indices des colonnes (après en-têtes)
    _U_SAVE_ID, _U_EMAIL, _U_WS, _U_SITE_URL, _U_NOM, _U_CREATED = 0, 1, 2, 3, 4, 5
    _U_CRAWL_CNT, _U_GEO_SCORE, _U_GEO_CLUST_CNT, _U_JSONLD_CNT = 6, 7, 8, 9
    _U_STATS_PAGES, _U_STATS_LINKS, _U_STATS_FILT, _U_STATS_DUP, _U_STATS_ERR = 10, 11, 12, 13, 14
    _U_INFRA_1, _U_INFRA_2, _U_INFRA_3, _U_INFRA_4 = 15, 16, 17, 18
    _U_CRAWL_1, _U_CRAWL_2, _U_GEO_1, _U_GEO_2, _U_JSONLD_1, _U_JSONLD_2 = 19, 20, 21, 22, 23, 24
    _U_MASTER_1, _U_MASTER_2 = 25, 26

    def _get_unified_worksheet(self):
        """Retourne l'onglet 'unified_saves' (à créer dans le GSheet si absent)."""
        if not self.sheet_file:
            return None
        try:
            ws = self.sheet_file.worksheet("unified_saves")
            vals = ws.get_all_values()
            if not vals or len(vals) == 0:
                ws.append_row(self.UNIFIED_HEADERS)
            return ws
        except Exception:
            try:
                ws = self.sheet_file.add_worksheet(title="unified_saves", rows=1000, cols=self.UNIFIED_COLS)
                ws.append_row(self.UNIFIED_HEADERS)
                return ws
            except Exception as e:
                logger.error("Impossible de créer l'onglet unified_saves: %s", e)
                return None

    def _json_to_cells(self, data, max_chars=None):
        """Sérialise en JSON et découpe en morceaux pour cellules (max_chars par cellule).
        Si le JSON dépasse 2 cellules, on compresse (zlib+base64) pour tenir."""
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
        """Reconstruit un objet JSON à partir de plusieurs cellules (concat puis json.loads, ou décompression si format compressé)."""
        parts = []
        for i in range(max_cols):
            idx = start_idx + i
            if idx < len(row):
                parts.append((row[idx] or "").strip())
        joined = "".join(parts)
        if not joined:
            return None
        try:
            return json.loads(joined)
        except Exception:
            pass
        try:
            decoded = base64.b64decode(joined)
            decompressed = zlib.decompress(decoded).decode("utf-8")
            return json.loads(decompressed)
        except Exception:
            return None

    def save_unified(self, user_email: str, workspace: str, site_url: str, nom_site: str,
                     crawl_data: list, geo_data: dict = None, jsonld_data: list = None,
                     master_json: str = None) -> str:
        """
        Sauvegarde unifiée : tout en colonnes décomposées, JSON brut (aucune compression).
        """
        ws = self._get_unified_worksheet()
        if not ws:
            raise ValueError("Onglet unified_saves indisponible")

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
        stats_pages = stats.get("pages_crawled", "")
        stats_links = stats.get("links_discovered", "")
        stats_filtered = stats.get("links_filtered", "")
        stats_dup = stats.get("links_duplicate", "")
        stats_err = stats.get("errors", "")

        infra = (geo_data or {}).get("geo_infra") or {}
        infra_names = list(infra.keys())[:4] if isinstance(infra, dict) else []
        infra_vals = []
        for i in range(4):
            name = infra_names[i] if i < len(infra_names) else ""
            if name and infra.get(name):
                status = "Present" if infra[name].get("status") else "Absent"
                infra_vals.append(f"{name}:{status}")
            else:
                infra_vals.append("")

        crawl_chunks = self._json_to_cells(crawl_data)
        geo_chunks = self._json_to_cells(geo_data)
        jsonld_chunks = self._json_to_cells(jsonld_data)
        master_str = (master_json or "").strip() if isinstance(master_json, str) else ""
        master_chunks = []
        if master_str:
            for i in range(0, len(master_str), self._UNIFIED_MAX_CELL):
                master_chunks.append(master_str[i : i + self._UNIFIED_MAX_CELL])

        row = [
            save_id, (user_email or "").strip(), final_ws, site_url, nom_site, created_at,
            crawl_pages_count, geo_score_str, geo_clusters_count, jsonld_models_count,
            stats_pages, stats_links, stats_filtered, stats_dup, stats_err,
            infra_vals[0] if len(infra_vals) > 0 else "",
            infra_vals[1] if len(infra_vals) > 1 else "",
            infra_vals[2] if len(infra_vals) > 2 else "",
            infra_vals[3] if len(infra_vals) > 3 else "",
            crawl_chunks[0] if len(crawl_chunks) > 0 else "",
            crawl_chunks[1] if len(crawl_chunks) > 1 else "",
            geo_chunks[0] if len(geo_chunks) > 0 else "",
            geo_chunks[1] if len(geo_chunks) > 1 else "",
            jsonld_chunks[0] if len(jsonld_chunks) > 0 else "",
            jsonld_chunks[1] if len(jsonld_chunks) > 1 else "",
            master_chunks[0] if len(master_chunks) > 0 else "",
            master_chunks[1] if len(master_chunks) > 1 else "",
        ]
        ws.append_row(row, value_input_option="RAW")
        session = get_session()
        session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
        return save_id

    def list_unified_saves(self, user_email: str, workspace: str = None):
        """
        Liste les sauvegardes unifiées de l'utilisateur (SaaS).
        workspace=None => toutes; sinon filtre par workspace.
        Retourne liste de {save_id, site_url, nom_site, created_at, workspace, has_geo, has_jsonld}.
        """
        ws = self._get_unified_worksheet()
        if not ws:
            return []

        try:
            rows = ws.get_all_values()
            if len(rows) < 2:
                return []
            email_norm = (user_email or "").strip().lower()
            ws_filter = (workspace or "").strip() if workspace else None
            out = []
            for row in rows[1:]:
                if len(row) < 6:
                    continue
                row_email = (row[1] or "").strip().lower()
                if row_email != email_norm:
                    continue
                row_ws = (row[2] or "").strip() or "Non classé"
                if ws_filter is not None and row_ws != ws_filter:
                    continue
                # Format 27 colonnes (décomposé): geo 21-22, jsonld 23-24, master 25-26
                if len(row) > self._U_GEO_1:
                    has_geo = bool((row[self._U_GEO_1] or "").strip())
                    has_jsonld = bool((row[self._U_JSONLD_1] or "").strip())
                    has_master = bool((row[self._U_MASTER_1] or "").strip()) if len(row) > self._U_MASTER_1 else False
                else:
                    # Ancien format 9/13 colonnes (compressé)
                    geo_col = row[11] if len(row) > 11 else (row[7] if len(row) > 7 else "")
                    jsonld_col = row[12] if len(row) > 12 else (row[8] if len(row) > 8 else "")
                    has_geo = bool((geo_col or "").strip())
                    has_jsonld = bool((jsonld_col or "").strip())
                    has_master = False
                out.append({
                    "save_id": row[0],
                    "site_url": row[3] if len(row) > 3 else "",
                    "nom_site": row[4] if len(row) > 4 else "Site",
                    "created_at": row[5] if len(row) > 5 else "",
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
        """
        Charge une sauvegarde unifiée par save_id (vérifie user_email = SaaS).
        Retourne {crawl_data, geo_data, jsonld_data, site_url, nom_site, workspace, created_at}.
        Lit le format 25 colonnes (JSON brut) ou l'ancien format compressé (9/13 colonnes).
        """
        ws = self._get_unified_worksheet()
        if not ws:
            return None

        def _decompress_blob(s):
            if not s or not (s or "").strip():
                return None
            s = (s or "").strip()
            if s[0] == "{" or s[0] == "[":
                try:
                    return json.loads(s)
                except Exception:
                    pass
            try:
                raw = base64.b64decode(s)
                return json.loads(zlib.decompress(raw).decode("utf-8"))
            except Exception:
                return None

        try:
            rows = ws.get_all_values()
            if len(rows) < 2:
                return None
            email_norm = (user_email or "").strip().lower()
            for row in rows[1:]:
                if len(row) < 6:
                    continue
                if (row[0] or "").strip() != str(save_id).strip():
                    continue
                row_email = (row[1] or "").strip().lower()
                if row_email != email_norm:
                    return None
                # Format 27 colonnes (décomposé, JSON brut) ou 25 / ancien
                if len(row) > self._U_JSONLD_2:
                    crawl_data = self._cells_to_json(row, self._U_CRAWL_1, 2)
                    geo_data = self._cells_to_json(row, self._U_GEO_1, 2)
                    jsonld_data = self._cells_to_json(row, self._U_JSONLD_1, 2)
                    master_json_val = ""
                    if len(row) > self._U_MASTER_2:
                        master_json_val = ((row[self._U_MASTER_1] or "") + (row[self._U_MASTER_2] or "")).strip()
                    elif len(row) > self._U_MASTER_1:
                        master_json_val = (row[self._U_MASTER_1] or "").strip()
                else:
                    # Ancien format 9/13 colonnes (compressé)
                    if len(row) >= 12:
                        crawl_data = _decompress_blob(row[10] if len(row) > 10 else "")
                        geo_data = _decompress_blob(row[11] if len(row) > 11 else "")
                        jsonld_data = _decompress_blob(row[12] if len(row) > 12 else "")
                    else:
                        crawl_data = _decompress_blob(row[6] if len(row) > 6 else "")
                        geo_data = _decompress_blob(row[7] if len(row) > 7 else "")
                        jsonld_data = _decompress_blob(row[8] if len(row) > 8 else "")
                    master_json_val = ""
                return {
                    "site_url": row[3] if len(row) > 3 else "",
                    "nom_site": row[4] if len(row) > 4 else "Site",
                    "workspace": (row[2] or "").strip() or "Non classé",
                    "created_at": row[5] if len(row) > 5 else "",
                    "crawl_data": crawl_data,
                    "geo_data": geo_data,
                    "jsonld_data": jsonld_data,
                    "master_json": master_json_val,
                }
            return None
        except Exception as e:
            logger.error("Erreur load_unified: %s", e)
            return None

    def update_master_for_unified(self, user_email: str, workspace: str, site_url: str, master_json: str) -> bool:
        """
        Met à jour ou crée une ligne unified_saves avec le master_json (MASTER DATA).
        Cherche la dernière sauvegarde user_email + workspace + site_url et met à jour master_json_1/2.
        Si aucune ligne ne correspond, en ajoute une (minimale) avec master uniquement.
        """
        ws = self._get_unified_worksheet()
        if not ws:
            return False
        master_str = (master_json or "").strip() if isinstance(master_json, str) else ""
        master_chunks = []
        if master_str:
            for i in range(0, len(master_str), self._UNIFIED_MAX_CELL):
                master_chunks.append(master_str[i : i + self._UNIFIED_MAX_CELL])
        try:
            rows = ws.get_all_values()
            if len(rows) < 2:
                return self._append_unified_master_only(user_email, workspace, site_url, master_chunks, ws)
            email_norm = (user_email or "").strip().lower()
            ws_norm = (workspace or "").strip() or "Non classé"
            site_norm = (site_url or "").strip()
            candidates = []
            for idx, row in enumerate(rows[1:], start=2):
                if len(row) < 6:
                    continue
                if (row[1] or "").strip().lower() != email_norm:
                    continue
                if ((row[2] or "").strip() or "Non classé") != ws_norm:
                    continue
                if (row[3] or "").strip() != site_norm:
                    continue
                candidates.append((idx, row[5] if len(row) > 5 else ""))
            if not candidates:
                return self._append_unified_master_only(user_email, workspace, site_url, master_chunks, ws)
            candidates.sort(key=lambda x: x[1], reverse=True)
            row_idx = candidates[0][0]
            col_m1, col_m2 = self._U_MASTER_1 + 1, self._U_MASTER_2 + 1
            ws.update_cell(row_idx, col_m1, master_chunks[0] if len(master_chunks) > 0 else "")
            ws.update_cell(row_idx, col_m2, master_chunks[1] if len(master_chunks) > 1 else "")
            session = get_session()
            session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
            return True
        except Exception as e:
            logger.error("Erreur update_master_for_unified: %s", e)
            return False

    def _append_unified_master_only(self, user_email: str, workspace: str, site_url: str,
                                    master_chunks: list, ws) -> bool:
        """Append une ligne unified_saves avec uniquement master (pour MASTER sans audit préalable)."""
        try:
            save_id = str(int(time.time()))
            created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            final_ws = (workspace or "").strip() or "Non classé"
            row = [
                save_id, (user_email or "").strip(), final_ws, (site_url or "")[:500], "Site", created_at,
                "", "", "", "",
                "", "", "", "", "",
                "", "", "", "",
                "", "", "", "", "", "",
                master_chunks[0] if len(master_chunks) > 0 else "",
                master_chunks[1] if len(master_chunks) > 1 else "",
            ]
            ws.append_row(row, value_input_option="RAW")
            session = get_session()
            session["audit_cache_version"] = session.get("audit_cache_version", 0) + 1
            return True
        except Exception as e:
            logger.error("Erreur _append_unified_master_only: %s", e)
            return False

    def _get_workspace_access_worksheet(self):
        """Onglet user_workspace_access (user_email, workspace_name)."""
        if not self.sheet_file:
            return None
        try:
            ws = self.sheet_file.worksheet("user_workspace_access")
            vals = ws.get_all_values()
            if not vals or len(vals) == 0:
                ws.append_row(["user_email", "workspace_name"])
            return ws
        except Exception:
            try:
                ws = self.sheet_file.add_worksheet(title="user_workspace_access", rows=500, cols=2)
                ws.append_row(["user_email", "workspace_name"])
                return ws
            except Exception as e:
                logger.error("Impossible de créer user_workspace_access: %s", e)
                return None

    def get_user_workspaces(self, user_email: str) -> list:
        """Liste des workspaces auxquels l'utilisateur a accès (vide = tous)."""
        ws = self._get_workspace_access_worksheet()
        if not ws:
            return []
        try:
            email_norm = (user_email or "").strip().lower()
            rows = ws.get_all_values()
            if len(rows) < 2:
                return []
            out = []
            for row in rows[1:]:
                if len(row) < 2:
                    continue
                if (row[0] or "").strip().lower() == email_norm:
                    w = (row[1] or "").strip()
                    if w and w not in out:
                        out.append(w)
            return out
        except Exception as e:
            logger.error("Erreur get_user_workspaces: %s", e)
            return []

    def set_user_workspaces(self, user_email: str, workspace_names: list) -> bool:
        """Remplace la liste des workspaces accessibles pour un utilisateur."""
        ws = self._get_workspace_access_worksheet()
        if not ws:
            return False
        try:
            email_norm = (user_email or "").strip().lower()
            rows = ws.get_all_values()
            new_rows = []
            for row in rows[1:]:
                if len(row) >= 2 and (row[0] or "").strip().lower() != email_norm:
                    new_rows.append(row)
            for wn in (workspace_names or []):
                name = (wn or "").strip()
                if name:
                    new_rows.append([email_norm, name])
            ws.clear()
            ws.append_row(["user_email", "workspace_name"])
            if new_rows:
                ws.append_rows(new_rows, value_input_option="RAW")
            return True
        except Exception as e:
            logger.error("Erreur set_user_workspaces: %s", e)
            raise

    def list_all_workspaces(self) -> list:
        """Liste tous les noms de workspaces distincts (unified_saves + user_workspace_access)."""
        seen = set()
        out = []
        ws = self._get_unified_worksheet()
        if ws:
            try:
                rows = ws.get_all_values()
                for row in rows[1:]:
                    w = (row[2] if len(row) > 2 else "").strip() or "Non classé"
                    if w not in seen:
                        seen.add(w)
                        out.append(w)
            except Exception as e:
                logger.error("Erreur list_all_workspaces (unified): %s", e)
        wa = self._get_workspace_access_worksheet()
        if wa:
            try:
                rows = wa.get_all_values()
                for row in rows[1:]:
                    w = (row[1] if len(row) > 1 else "").strip()
                    if w and w not in seen:
                        seen.add(w)
                        out.append(w)
            except Exception:
                pass
        return sorted(out)

    # ─── Workspace CRUD (backoffice) ─────────────────────────────────────────

    def create_workspace(self, name: str) -> bool:
        """Register a new workspace (adds to user_workspace_access)."""
        wa = self._get_workspace_access_worksheet()
        if not wa:
            return False
        try:
            name = (name or "").strip()
            if not name:
                return False
            wa.append_row(["__workspace_registry__", name], value_input_option="RAW")
            return True
        except Exception as e:
            logger.error("Erreur create_workspace: %s", e)
            return False

    def rename_workspace(self, old_name: str, new_name: str) -> bool:
        """Rename workspace across all worksheets."""
        old = (old_name or "").strip()
        new = (new_name or "").strip()
        if not old or not new or old == new:
            return False
        ok = True
        for get_ws, col_idx in [
            (self._get_unified_worksheet, 2),
            (self._get_workspace_access_worksheet, 1),
        ]:
            ws = get_ws()
            if not ws:
                continue
            try:
                rows = ws.get_all_values()
                cells_to_update = []
                for r_idx, row in enumerate(rows):
                    if r_idx == 0:
                        continue
                    if col_idx < len(row) and (row[col_idx] or "").strip() == old:
                        cells_to_update.append((r_idx + 1, col_idx + 1))
                for (r, c) in cells_to_update:
                    ws.update_cell(r, c, new)
            except Exception as e:
                logger.error("Erreur rename_workspace sheet: %s", e)
                ok = False
        return ok

    def move_saves_to_workspace(self, save_ids: list, target_workspace: str) -> int:
        """Move saves to target workspace. Returns count."""
        ws = self._get_unified_worksheet()
        if not ws:
            return 0
        try:
            target = (target_workspace or "").strip() or "Non classé"
            rows = ws.get_all_values()
            moved = 0
            for r_idx, row in enumerate(rows):
                if r_idx == 0:
                    continue
                sid = (row[0] if len(row) > 0 else "").strip()
                if sid in [str(s).strip() for s in (save_ids or [])]:
                    ws.update_cell(r_idx + 1, 3, target)
                    moved += 1
            return moved
        except Exception as e:
            logger.error("Erreur move_saves_to_workspace: %s", e)
            return 0

    def list_workspace_saves_admin(self, workspace: str) -> list:
        """List all saves in a workspace (admin, no user filter)."""
        ws = self._get_unified_worksheet()
        if not ws:
            return []
        try:
            target = (workspace or "").strip()
            if not target:
                return []
            rows = ws.get_all_values()
            out = []
            for row in rows[1:]:
                if len(row) < 6:
                    continue
                row_ws = (row[2] or "").strip() or "Non classé"
                if row_ws == target:
                    out.append({
                        "save_id": (row[0] or "").strip(),
                        "user_email": (row[1] or "").strip(),
                        "site_url": (row[3] or "").strip() if len(row) > 3 else "",
                        "nom_site": (row[4] or "").strip() if len(row) > 4 else "Site",
                        "created_at": (row[5] or "").strip() if len(row) > 5 else "",
                        "workspace": row_ws,
                    })
            return sorted(out, key=lambda x: x.get("created_at", ""), reverse=True)
        except Exception as e:
            logger.error("Erreur list_workspace_saves_admin: %s", e)
            return []
