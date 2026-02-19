"""Sitemap scoring strategies — pure logic, no Streamlit dependency.

Provides SEO and GEO priority calculators, citability checks, and
changefreq heuristics that can be reused in a FastAPI/Flask context.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, Optional

CONTENT_TYPE_WEIGHTS_SEO: Dict[str, float] = {
    "guide": 0.90,
    "article": 0.85,
    "product": 0.80,
    "category": 0.75,
    "service": 0.75,
    "landing": 0.70,
    "page": 0.60,
    "faq": 0.65,
    "blog": 0.70,
    "news": 0.80,
    "event": 0.65,
    "job": 0.55,
    "legal": 0.20,
    "other": 0.40,
}

CONTENT_TYPE_WEIGHTS_GEO: Dict[str, float] = {
    "guide": 0.95,
    "article": 0.90,
    "faq": 0.85,
    "product": 0.70,
    "service": 0.80,
    "category": 0.50,
    "landing": 0.55,
    "page": 0.45,
    "blog": 0.75,
    "news": 0.70,
    "event": 0.60,
    "job": 0.40,
    "legal": 0.10,
    "other": 0.30,
}

EXCLUDED_TYPES_DEFAULT = {"legal", "login", "404", "redirect", "admin"}


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _freshness_score(last_modified: Optional[str | datetime]) -> float:
    """Return 0.0–1.0 based on how recently the page was modified."""
    if not last_modified:
        return 0.3
    try:
        if isinstance(last_modified, str):
            for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    last_modified = datetime.strptime(last_modified, fmt)
                    break
                except ValueError:
                    continue
            else:
                return 0.3
        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - last_modified).days
        if days_old <= 7:
            return 1.0
        if days_old <= 30:
            return 0.9
        if days_old <= 90:
            return 0.7
        if days_old <= 365:
            return 0.5
        return 0.3
    except Exception:
        return 0.3


def _traffic_score(monthly_traffic: int) -> float:
    """Logarithmic traffic score 0.0–1.0."""
    if monthly_traffic <= 0:
        return 0.0
    return _clamp(math.log10(monthly_traffic + 1) / 5.0)


def _backlinks_score(backlinks: int) -> float:
    if backlinks <= 0:
        return 0.0
    return _clamp(math.log10(backlinks + 1) / 4.0)


def calculate_seo_priority(page: Dict) -> float:
    """Calculate SEO priority 0.0–1.0 for a page.

    Weights: content_type 25%, content_quality 20%, traffic 20%,
    backlinks 15%, freshness 10%, jsonld 10%.
    """
    ct = (page.get("content_type") or "page").lower()
    type_w = CONTENT_TYPE_WEIGHTS_SEO.get(ct, 0.40)
    cq = float(page.get("content_quality") or 0)
    traffic = _traffic_score(int(page.get("monthly_traffic") or 0))
    bl = _backlinks_score(int(page.get("backlinks") or 0))
    fresh = _freshness_score(page.get("last_modified"))
    jld = float(page.get("jsonld_quality") or 0) if page.get("has_jsonld") else 0.0

    priority = (
        0.25 * type_w
        + 0.20 * cq
        + 0.20 * traffic
        + 0.15 * bl
        + 0.10 * fresh
        + 0.10 * jld
    )
    return round(_clamp(priority), 2)


def calculate_geo_priority(page: Dict) -> float:
    """Calculate GEO priority 0.0–1.0 for a page.

    GEO favors content rich for LLM citation: JSON-LD quality and
    content quality are dominant factors.
    Weights: jsonld_quality 30%, content_quality 25%, content_type 20%,
    freshness 15%, traffic 10%.
    """
    ct = (page.get("content_type") or "page").lower()
    type_w = CONTENT_TYPE_WEIGHTS_GEO.get(ct, 0.30)
    cq = float(page.get("content_quality") or 0)
    jld = float(page.get("jsonld_quality") or 0) if page.get("has_jsonld") else 0.0
    fresh = _freshness_score(page.get("last_modified"))
    traffic = _traffic_score(int(page.get("monthly_traffic") or 0))

    priority = (
        0.30 * jld
        + 0.25 * cq
        + 0.20 * type_w
        + 0.15 * fresh
        + 0.10 * traffic
    )
    return round(_clamp(priority), 2)


def is_citable(page: Dict, config: Optional[Dict] = None) -> bool:
    """A page is citable by LLMs if it has good JSON-LD AND content quality."""
    config = config or {}
    min_jld = float(config.get("min_jsonld_quality", 0.5))
    min_cq = float(config.get("min_content_quality", 0.5))
    ct = (page.get("content_type") or "page").lower()
    if ct in EXCLUDED_TYPES_DEFAULT:
        return False
    if (page.get("status") or "active") != "active":
        return False
    has_jld = page.get("has_jsonld", False)
    jld_q = float(page.get("jsonld_quality") or 0)
    cq = float(page.get("content_quality") or 0)
    return has_jld and jld_q >= min_jld and cq >= min_cq


def determine_changefreq(page: Dict) -> str:
    """Heuristic change frequency based on content type and freshness."""
    ct = (page.get("content_type") or "page").lower()
    if ct in ("news", "blog"):
        return "daily"
    if ct in ("product", "event", "job"):
        return "weekly"
    fresh = _freshness_score(page.get("last_modified"))
    if fresh >= 0.9:
        return "daily"
    if fresh >= 0.7:
        return "weekly"
    if fresh >= 0.5:
        return "monthly"
    return "yearly"
