"""Sitemap XML generator — pure logic, no Streamlit dependency.

Generates standard sitemap XML (protocol 0.9) from a list of page dicts.
Can be reused in a FastAPI/Flask context.
"""

from __future__ import annotations

from typing import Dict, List
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString


SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
MAX_URLS_PER_SITEMAP = 50_000


def generate_sitemap_xml(pages: List[Dict], pretty: bool = True) -> str:
    """Generate a sitemap XML string from a list of page dicts.

    Each page dict should have: url, lastmod (optional), priority (optional),
    changefreq (optional).

    Returns a UTF-8 XML string.
    """
    urlset = Element("urlset")
    urlset.set("xmlns", SITEMAP_NS)

    for page in pages[:MAX_URLS_PER_SITEMAP]:
        url_el = SubElement(urlset, "url")
        loc = SubElement(url_el, "loc")
        loc.text = page.get("url", "")

        lastmod = page.get("lastmod")
        if lastmod:
            lm_el = SubElement(url_el, "lastmod")
            lm_el.text = str(lastmod)[:10]

        changefreq = page.get("changefreq")
        if changefreq:
            cf_el = SubElement(url_el, "changefreq")
            cf_el.text = changefreq

        priority_val = page.get("priority")
        if priority_val is not None:
            pr_el = SubElement(url_el, "priority")
            pr_el.text = f"{float(priority_val):.2f}"

    raw_xml = tostring(urlset, encoding="unicode", xml_declaration=False)
    full_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + raw_xml

    if pretty:
        try:
            return parseString(full_xml).toprettyxml(indent="  ", encoding=None)
        except Exception:
            return full_xml
    return full_xml


def generate_sitemap_index_xml(sitemap_urls: List[str], pretty: bool = True) -> str:
    """Generate a sitemap index XML for multiple sitemaps."""
    sitemapindex = Element("sitemapindex")
    sitemapindex.set("xmlns", SITEMAP_NS)

    for url in sitemap_urls:
        sitemap_el = SubElement(sitemapindex, "sitemap")
        loc = SubElement(sitemap_el, "loc")
        loc.text = url

    raw_xml = tostring(sitemapindex, encoding="unicode", xml_declaration=False)
    full_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + raw_xml

    if pretty:
        try:
            return parseString(full_xml).toprettyxml(indent="  ", encoding=None)
        except Exception:
            return full_xml
    return full_xml
