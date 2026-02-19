"""Sitemap generation engine — pure logic, no Streamlit dependency.

Orchestrates strategy calculations and XML generation.
Can be reused in a FastAPI/Flask context.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from modules.sitemap.strategies import (
    EXCLUDED_TYPES_DEFAULT,
    calculate_geo_priority,
    calculate_seo_priority,
    determine_changefreq,
    is_citable,
)
from modules.sitemap.xml_generator import generate_sitemap_xml


class SitemapEngine:
    """Main engine for sitemap generation.

    Accepts raw page data (list of dicts) and produces sorted,
    prioritized page lists for SEO and GEO sitemaps.
    """

    def __init__(self, pages_data: List[Dict]):
        self.pages = [p for p in pages_data if p.get("url")]

    def _apply_exclusions(self, pages: List[Dict], config: Dict) -> List[Dict]:
        exclude_types = set(config.get("exclude_content_types") or [])
        exclude_types |= EXCLUDED_TYPES_DEFAULT
        return [
            p for p in pages
            if (p.get("content_type") or "page").lower() not in exclude_types
            and (p.get("status") or "active") == "active"
        ]

    def generate_seo_sitemap(
        self,
        config: Optional[Dict] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[Dict]:
        """Generate an SEO-optimized sitemap.

        Returns list of dicts with: url, lastmod, priority, changefreq.
        """
        config = config or {}
        pages = self._apply_exclusions(self.pages, config)

        result = []
        total = len(pages)
        for i, p in enumerate(pages):
            prio = calculate_seo_priority(p)
            entry = {
                "url": p["url"],
                "lastmod": (p.get("last_modified") or "")[:10] or None,
                "priority": prio,
                "changefreq": determine_changefreq(p),
                "content_type": p.get("content_type", "page"),
            }
            result.append(entry)
            if progress_callback and total > 0:
                progress_callback("Calcul SEO...", (i + 1) / total)

        result.sort(key=lambda x: x["priority"], reverse=True)
        return result

    def generate_geo_sitemap(
        self,
        config: Optional[Dict] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> List[Dict]:
        """Generate a GEO-optimized sitemap for LLM discoverability.

        Only includes citable pages (good JSON-LD + content quality).
        Respects max_urls_geo from config.
        """
        config = config or {}
        pages = self._apply_exclusions(self.pages, config)
        max_urls = int(config.get("max_urls_geo", 500))

        citable = [p for p in pages if is_citable(p, config)]

        result = []
        total = len(citable)
        for i, p in enumerate(citable):
            prio = calculate_geo_priority(p)
            entry = {
                "url": p["url"],
                "lastmod": (p.get("last_modified") or "")[:10] or None,
                "priority": prio,
                "changefreq": determine_changefreq(p),
                "content_type": p.get("content_type", "page"),
                "has_jsonld": p.get("has_jsonld", False),
                "jsonld_quality": float(p.get("jsonld_quality") or 0),
            }
            result.append(entry)
            if progress_callback and total > 0:
                progress_callback("Calcul GEO...", (i + 1) / total)

        result.sort(key=lambda x: x["priority"], reverse=True)
        return result[:max_urls]

    def generate_xml(self, pages_list: List[Dict]) -> str:
        """Convenience wrapper around xml_generator."""
        return generate_sitemap_xml(pages_list)

    def get_stats(self, pages_list: List[Dict]) -> Dict:
        """Return summary statistics for a generated sitemap."""
        if not pages_list:
            return {"total": 0, "avg_priority": 0, "by_type": {}, "by_changefreq": {}}
        by_type: Dict[str, int] = {}
        by_freq: Dict[str, int] = {}
        total_prio = 0.0
        for p in pages_list:
            ct = p.get("content_type", "page")
            by_type[ct] = by_type.get(ct, 0) + 1
            cf = p.get("changefreq", "monthly")
            by_freq[cf] = by_freq.get(cf, 0) + 1
            total_prio += float(p.get("priority", 0))
        return {
            "total": len(pages_list),
            "avg_priority": round(total_prio / len(pages_list), 3),
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
            "by_changefreq": dict(sorted(by_freq.items(), key=lambda x: -x[1])),
        }
