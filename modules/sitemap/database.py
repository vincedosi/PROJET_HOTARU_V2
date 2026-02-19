"""Sitemap Supabase CRUD — database layer for the sitemap module.

All methods accept explicit parameters (no session_state, no globals)
so they can be reused in a FastAPI/Flask context.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from modules.sitemap.strategies import (
    calculate_geo_priority,
    calculate_seo_priority,
    is_citable,
)

logger = logging.getLogger(__name__)


class SitemapDatabase:
    """Manages all Supabase interactions for the sitemap module."""

    def __init__(self, supabase_client):
        self.client = supabase_client

    # ── PROJECTS ──────────────────────────────────────────────────────────

    def create_project(self, workspace: str, user_email: str, data: Dict) -> Dict:
        payload = {
            "workspace": (workspace or "").strip() or "Non classé",
            "user_email": (user_email or "").strip().lower(),
            "name": data["name"],
            "description": data.get("description", ""),
            "domain": data["domain"],
            "max_urls_geo": int(data.get("max_urls_geo", 500)),
            "exclude_content_types": json.dumps(data.get("exclude_content_types", [])),
            "min_content_quality": float(data.get("min_content_quality", 0.5)),
            "min_jsonld_quality": float(data.get("min_jsonld_quality", 0.5)),
        }
        r = self.client.table("sitemap_projects").insert(payload).execute()
        logger.info("create_project '%s' → OK", data["name"])
        return r.data[0] if r.data else {}

    def get_projects(self, workspace: str) -> List[Dict]:
        ws = (workspace or "").strip() or "Non classé"
        r = (
            self.client.table("sitemap_projects")
            .select("*")
            .eq("workspace", ws)
            .order("created_at", desc=True)
            .execute()
        )
        return r.data or []

    def get_project(self, project_id: int) -> Optional[Dict]:
        r = (
            self.client.table("sitemap_projects")
            .select("*")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        return r.data[0] if r.data else None

    def update_project(self, project_id: int, data: Dict) -> Dict:
        payload = {}
        for key in ("name", "description", "domain", "max_urls_geo",
                     "min_content_quality", "min_jsonld_quality"):
            if key in data:
                payload[key] = data[key]
        if "exclude_content_types" in data:
            payload["exclude_content_types"] = json.dumps(data["exclude_content_types"])
        r = (
            self.client.table("sitemap_projects")
            .update(payload)
            .eq("id", project_id)
            .execute()
        )
        logger.info("update_project %d → OK", project_id)
        return r.data[0] if r.data else {}

    def delete_project(self, project_id: int) -> bool:
        self.client.table("sitemap_projects").delete().eq("id", project_id).execute()
        logger.info("delete_project %d → OK", project_id)
        return True

    # ── PAGES ─────────────────────────────────────────────────────────────

    def import_pages(self, project_id: int, pages: List[Dict]) -> int:
        if not pages:
            return 0
        rows = []
        for p in pages:
            url = (p.get("url") or "").strip()
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                continue
            rows.append({
                "project_id": project_id,
                "url": url,
                "content_type": (p.get("content_type") or "page").lower()[:100],
                "has_jsonld": bool(p.get("has_jsonld", False)),
                "jsonld_quality": min(1.0, max(0.0, float(p.get("jsonld_quality") or 0))),
                "content_quality": min(1.0, max(0.0, float(p.get("content_quality") or 0))),
                "monthly_traffic": max(0, int(p.get("monthly_traffic") or 0)),
                "backlinks": max(0, int(p.get("backlinks") or 0)),
                "last_modified": p.get("last_modified") or None,
                "status": "active",
            })
        if not rows:
            return 0
        batch_size = 200
        imported = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i: i + batch_size]
            try:
                self.client.table("sitemap_pages").upsert(
                    batch, on_conflict="project_id,url"
                ).execute()
                imported += len(batch)
            except Exception as e:
                logger.error("import_pages batch error: %s", e)
        logger.info("import_pages project=%d → %d pages", project_id, imported)
        return imported

    def get_pages(self, project_id: int, filters: Optional[Dict] = None) -> List[Dict]:
        q = (
            self.client.table("sitemap_pages")
            .select("*")
            .eq("project_id", project_id)
        )
        if filters:
            if "status" in filters:
                q = q.eq("status", filters["status"])
            if "is_citable" in filters:
                q = q.eq("is_citable", filters["is_citable"])
            if "content_type" in filters:
                q = q.eq("content_type", filters["content_type"])
        q = q.order("seo_priority", desc=True).limit(5000)
        r = q.execute()
        return r.data or []

    def get_pages_count(self, project_id: int) -> int:
        r = (
            self.client.table("sitemap_pages")
            .select("id", count="exact")
            .eq("project_id", project_id)
            .execute()
        )
        return r.count or 0

    def update_page(self, page_id: int, data: Dict) -> Dict:
        payload = {}
        for key in ("status", "content_type", "has_jsonld", "jsonld_quality",
                     "content_quality", "monthly_traffic", "backlinks"):
            if key in data:
                payload[key] = data[key]
        r = self.client.table("sitemap_pages").update(payload).eq("id", page_id).execute()
        return r.data[0] if r.data else {}

    def delete_pages(self, project_id: int, page_ids: Optional[List[int]] = None) -> int:
        if page_ids:
            for pid in page_ids:
                self.client.table("sitemap_pages").delete().eq("id", pid).execute()
            return len(page_ids)
        r = self.client.table("sitemap_pages").delete().eq("project_id", project_id).execute()
        return len(r.data) if r.data else 0

    def calculate_priorities(self, project_id: int, config: Optional[Dict] = None) -> int:
        """Recalculate SEO/GEO priorities and is_citable for all pages."""
        pages = self.get_pages(project_id, {"status": "active"})
        config = config or {}
        updated = 0
        for p in pages:
            seo_p = calculate_seo_priority(p)
            geo_p = calculate_geo_priority(p)
            citable = is_citable(p, config)
            try:
                self.client.table("sitemap_pages").update({
                    "seo_priority": seo_p,
                    "geo_priority": geo_p,
                    "is_citable": citable,
                }).eq("id", p["id"]).execute()
                updated += 1
            except Exception as e:
                logger.error("calculate_priorities page %s: %s", p.get("id"), e)
        logger.info("calculate_priorities project=%d → %d updated", project_id, updated)
        return updated

    # ── GENERATIONS ────────────────────────────────────────────────────────

    def save_generation(self, project_id: int, gen_type: str,
                        urls_count: int, xml_content: str, user_email: str) -> Dict:
        payload = {
            "project_id": project_id,
            "type": gen_type,
            "urls_count": urls_count,
            "xml_content": xml_content,
            "generated_by": (user_email or "").strip().lower(),
        }
        r = self.client.table("sitemap_generations").insert(payload).execute()
        logger.info("save_generation project=%d type=%s urls=%d", project_id, gen_type, urls_count)
        return r.data[0] if r.data else {}

    def get_generations(self, project_id: int, limit: int = 20) -> List[Dict]:
        r = (
            self.client.table("sitemap_generations")
            .select("*")
            .eq("project_id", project_id)
            .order("generated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return r.data or []

    def delete_generation(self, generation_id: int) -> bool:
        self.client.table("sitemap_generations").delete().eq("id", generation_id).execute()
        return True
