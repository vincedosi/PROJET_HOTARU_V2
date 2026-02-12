"""
HOTARU v2 - Audit Database (Google Sheets Backend)
"""

import re
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import time
import datetime
import zlib
import base64


@st.cache_data(ttl=300)
def _cached_load_user_audits_from_sheet(all_rows_list, user_email):
    """Fonction cachée pour traiter les audits (wrapper pour @st.cache_data)."""
    if not all_rows_list or len(all_rows_list) < 2:
        return []

    data_rows = all_rows_list[1:]
    user_audits = []
    email_normalized = (user_email or "").strip().lower()

    for row in data_rows:
        if len(row) < 2:
            continue
        # Isolation SaaS : ne retourner que les lignes de cet utilisateur
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
    def __init__(self):
        self.client = None
        self.sheet_file = None
        self.sheet = None
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        try:
            self.creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=self.scope
            )
            self.client = gspread.authorize(self.creds)
        except Exception as e:
            st.error(f"Erreur de configuration Secrets (GCP): {e}")
            return

        try:
            sheet_url = st.secrets.get("sheet_url", "")
            if not sheet_url:
                st.error("URL du Google Sheet manquante dans les secrets Streamlit")
                return

            self.sheet_file = self.client.open_by_url(sheet_url)

            try:
                self.sheet = self.sheet_file.worksheet("audits")
            except Exception:
                self.sheet = self.sheet_file.sheet1

        except Exception as e:
            st.error(f"Impossible d'ouvrir le GSheet. Erreur: {e}")
            self.sheet_file = None
            self.sheet = None

    def load_user_audits(self, user_email):
        """Charge uniquement les audits de l'utilisateur connecté (isolation SaaS).
        Résultats cachés 5 minutes par email utilisateur."""
        if not self.sheet:
            return []

        try:
            all_rows = self.sheet.get_all_values()
            # Appel à la fonction cachée avec les données (et non self)
            return _cached_load_user_audits_from_sheet(all_rows, user_email)

        except Exception as e:
            st.error(f"Erreur lors de la lecture des audits : {e}")
            return []

    def save_audit(self, user_email, workspace, site_url, nom_site, json_data):
        if not self.sheet:
            st.error("Impossible de sauvegarder : connexion BDD échouée")
            return False

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
            return True

        except Exception as e:
            st.error(f"Erreur de sauvegarde GSheet : {e}")
            return False

    def save_master_for_audit(self, user_email, workspace, site_url, master_json):
        """
        Sauvegarde le JSON-LD Master dans la colonne J ('master') de l'onglet audits
        pour la ligne correspondant à (user_email, workspace, site_url).
        """
        if not self.sheet:
            st.error("Impossible de sauvegarder le MASTER : connexion BDD échouée")
            return False

        try:
            all_rows = self.sheet.get_all_values()
            if len(all_rows) < 2:
                st.error("Aucun audit existant pour enregistrer le MASTER.")
                return False

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
                    # Colonne J = index 10 (1-based)
                    self.sheet.update_cell(idx, 10, master_json)
                    return True

            st.error("Aucune ligne d'audit correspondante trouvée pour ce MASTER.")
            return False
        except Exception as e:
            st.error(f"Erreur de sauvegarde MASTER GSheet : {e}")
            return False

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
                st.error(f"Impossible de créer l'onglet jsonld : {e}")
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
        """
        Sauvegarde les modèles JSON-LD dans l'onglet 'jsonld' du Google Sheet.
        models_data: liste de dicts avec model_name, schema_type, page_count, url_pattern,
                     sample_urls, dom_structure, existing_jsonld, optimized_jsonld (optionnel).
        """
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
            st.error(f"Erreur sauvegarde JSON-LD GSheet : {e}")
            return False

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
        """
        Retourne la liste des (site_url, workspace) sauvegardés pour l'utilisateur.
        Format: [{"site_url": str, "workspace": str, "created_at": str}, ...]
        """
        models = self.load_jsonld_models(user_email, site_url=None)
        seen = {}
        for m in models:
            key = (m.get("site_url") or "", m.get("workspace") or "Non classé")
            if key not in seen or (m.get("created_at") or "") > (seen[key].get("created_at") or ""):
                seen[key] = {"site_url": key[0], "workspace": key[1], "created_at": m.get("created_at", "")}
        return list(seen.values())

    def load_jsonld_models(self, user_email: str, site_url: str = None):
        """
        Charge les modèles JSON-LD depuis l'onglet 'jsonld'.
        Filtre par user_email et optionnellement par site_url.
        """
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
            st.error(f"Erreur lecture JSON-LD GSheet : {e}")
            return []
