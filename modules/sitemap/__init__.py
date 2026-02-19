"""Sitemap Dynamique module — lazy imports to avoid circular dependencies."""


def render_sitemap_tab(*args, **kwargs):
    from modules.sitemap.ui import render_sitemap_tab as _fn
    return _fn(*args, **kwargs)
