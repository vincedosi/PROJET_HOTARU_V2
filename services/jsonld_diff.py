"""
HOTARU — JSON-LD Diff & Comparison
Compares two JSON-LD objects for visual rendering (gray/green/red).
Reusable by future API.
"""

import json
from typing import Any, Dict, List, Optional


def compute_jsonld_diff(original: Optional[dict], optimized: Optional[dict]) -> List[dict]:
    """
    Field-level diff between original and optimized JSON-LD.
    Returns list of {path, status, original_value, optimized_value}.
    status: 'same' | 'enriched' | 'added' | 'removed'
    """
    if not optimized:
        return []
    diffs: List[dict] = []
    _diff_recursive(original or {}, optimized, "", diffs)
    return diffs


def _diff_recursive(orig: Any, opt: Any, prefix: str, diffs: list):
    if isinstance(opt, dict):
        orig_d = orig if isinstance(orig, dict) else {}
        all_keys = list(dict.fromkeys(list(opt.keys()) + list(orig_d.keys())))
        for key in all_keys:
            path = f"{prefix}.{key}" if prefix else key
            in_opt, in_orig = key in opt, key in orig_d
            if in_opt and in_orig:
                if opt[key] == orig_d[key]:
                    diffs.append({"path": path, "status": "same", "original_value": orig_d[key], "optimized_value": opt[key]})
                elif isinstance(opt[key], (dict, list)):
                    _diff_recursive(orig_d[key], opt[key], path, diffs)
                else:
                    diffs.append({"path": path, "status": "enriched", "original_value": orig_d[key], "optimized_value": opt[key]})
            elif in_opt:
                diffs.append({"path": path, "status": "added", "original_value": None, "optimized_value": opt[key]})
            else:
                diffs.append({"path": path, "status": "removed", "original_value": orig_d[key], "optimized_value": None})
    elif isinstance(opt, list):
        orig_l = orig if isinstance(orig, list) else []
        for i in range(max(len(opt), len(orig_l))):
            path = f"{prefix}[{i}]"
            if i < len(opt) and i < len(orig_l):
                if opt[i] == orig_l[i]:
                    diffs.append({"path": path, "status": "same", "original_value": orig_l[i], "optimized_value": opt[i]})
                elif isinstance(opt[i], (dict, list)):
                    _diff_recursive(orig_l[i], opt[i], path, diffs)
                else:
                    diffs.append({"path": path, "status": "enriched", "original_value": orig_l[i], "optimized_value": opt[i]})
            elif i < len(opt):
                diffs.append({"path": path, "status": "added", "original_value": None, "optimized_value": opt[i]})
            else:
                diffs.append({"path": path, "status": "removed", "original_value": orig_l[i], "optimized_value": None})


def extract_modified_fields(original: Optional[dict], optimized: Optional[dict]) -> dict:
    """Extract only added or modified fields from optimized (delta vs original)."""
    if not optimized:
        return {}
    if not original:
        return optimized
    delta = {}
    for key, value in optimized.items():
        if key not in original:
            delta[key] = value
        elif isinstance(value, dict) and isinstance(original.get(key), dict):
            sub = extract_modified_fields(original[key], value)
            if sub:
                delta[key] = sub
        elif value != original.get(key):
            delta[key] = value
    return delta


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_comparison_html(original: Optional[dict], optimized: Optional[dict]) -> str:
    """
    Side-by-side colored HTML comparing two JSON-LD objects.
    Gray = identical, Green = added/enriched, Red = removed.
    """
    if not optimized:
        return '<p style="color:#64748b;">Aucun JSON-LD optimisé disponible.</p>'

    orig = original or {}
    diffs = compute_jsonld_diff(orig, optimized)
    status_map: Dict[str, str] = {}
    for d in diffs:
        top_key = d["path"].split(".")[0].split("[")[0]
        cur = status_map.get(top_key)
        s = d["status"]
        if cur is None or s in ("added", "enriched") or (cur == "same" and s != "same"):
            status_map[top_key] = s

    orig_str = json.dumps(orig, ensure_ascii=False, indent=2) if orig else "{ }"

    all_keys = list(dict.fromkeys(list(optimized.keys()) + list(orig.keys())))
    opt_lines = []
    opt_lines.append('<span style="display:block;padding:0 4px;">{</span>')
    for ki, key in enumerate(all_keys):
        in_opt = key in optimized
        in_orig = key in orig
        st_val = status_map.get(key, "same")

        if in_opt and in_orig:
            bg = "#f1f5f9" if st_val == "same" else "#dcfce7"
            tag = "" if st_val == "same" else " ← enrichi"
        elif in_opt:
            bg = "#dcfce7"
            tag = " ← ajouté"
        else:
            bg = "#fee2e2"
            tag = " ← supprimé"

        value = optimized.get(key, orig.get(key))
        val_str = json.dumps(value, ensure_ascii=False, indent=2)
        if "\n" in val_str:
            lines = val_str.split("\n")
            val_str = lines[0] + "\n" + "\n".join("    " + l for l in lines[1:])

        comma = "," if ki < len(all_keys) - 1 else ""
        opt_lines.append(
            f'<span style="display:block;background:{bg};padding:1px 6px;">'
            f'  &quot;{_esc(key)}&quot;: {_esc(val_str)}{comma}'
            f'<span style="color:#94a3b8;font-size:0.7rem;">{tag}</span></span>'
        )
    opt_lines.append('<span style="display:block;padding:0 4px;">}</span>')

    html = (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-family:monospace;font-size:0.78rem;">'
        '<div>'
        '<div style="background:#0f172a;color:#fff;padding:6px 12px;font-weight:700;font-size:0.72rem;text-transform:uppercase;letter-spacing:.06em;">JSON-LD Actuel</div>'
        f'<pre style="background:#f8fafc;border:1px solid #e2e8f0;padding:8px;overflow:auto;max-height:500px;margin:0;white-space:pre-wrap;">{_esc(orig_str)}</pre>'
        '</div>'
        '<div>'
        '<div style="background:#0f172a;color:#fff;padding:6px 12px;font-weight:700;font-size:0.72rem;text-transform:uppercase;letter-spacing:.06em;">JSON-LD Optimisé</div>'
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;padding:8px;overflow:auto;max-height:500px;font-family:monospace;font-size:0.78rem;white-space:pre-wrap;">'
        + "".join(opt_lines) +
        '</div></div></div>'
        '<div style="margin-top:6px;font-size:0.72rem;color:#64748b;display:flex;gap:16px;">'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#f1f5f9;border:1px solid #cbd5e1;vertical-align:middle;margin-right:3px;"></span>Identique</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#dcfce7;border:1px solid #86efac;vertical-align:middle;margin-right:3px;"></span>Ajouté / Enrichi</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#fee2e2;border:1px solid #fca5a5;vertical-align:middle;margin-right:3px;"></span>Supprimé</span>'
        '</div>'
    )
    return html


def diff_summary(original: Optional[dict], optimized: Optional[dict]) -> dict:
    """Quick summary: counts of added, enriched, same, removed fields."""
    diffs = compute_jsonld_diff(original, optimized)
    out = {"added": 0, "enriched": 0, "same": 0, "removed": 0, "total": len(diffs)}
    for d in diffs:
        out[d["status"]] = out.get(d["status"], 0) + 1
    return out
