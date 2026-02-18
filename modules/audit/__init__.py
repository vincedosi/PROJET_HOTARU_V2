# Audit : Audit GEO, Authority Score, Scraping, Off-Page, GEO Scoring
# Lazy imports to avoid circular dependencies (views ↔ modules)

from .geo_scoring import GEOScorer


def render_audit_geo(*args, **kwargs):
    from views.audit_geo import render_audit_geo as _fn
    return _fn(*args, **kwargs)


def render_scraping_debug_tab(*args, **kwargs):
    from views.audit_scraping import render_scraping_debug_tab as _fn
    return _fn(*args, **kwargs)


def render_authority_score(*args, **kwargs):
    from views.authority_score import render_authority_score as _fn
    return _fn(*args, **kwargs)


def render_off_page_audit(*args, **kwargs):
    from views.off_page import render_off_page_audit as _fn
    return _fn(*args, **kwargs)


__all__ = [
    "render_audit_geo",
    "render_scraping_debug_tab",
    "render_authority_score",
    "render_off_page_audit",
    "GEOScorer",
]
