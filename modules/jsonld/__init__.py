# JSON-LD : Master, LEAF, JSON-LD TRANSFORMER (analyse), blocs méthodologie
# Lazy imports to avoid circular dependencies


def render_master_tab(*args, **kwargs):
    from views.master import render_master_tab as _fn
    return _fn(*args, **kwargs)


def render_master_tab_for_jsonld(*args, **kwargs):
    from views.master import render_master_tab_for_jsonld as _fn
    return _fn(*args, **kwargs)


def render_methodologie_for_module(*args, **kwargs):
    from views.methodologie_blocks import render_methodologie_for_module as _fn
    return _fn(*args, **kwargs)


def render_jsonld_analyzer_tab(*args, **kwargs):
    from views.jsonld_analyzer import render_jsonld_analyzer_tab as _fn
    return _fn(*args, **kwargs)


def render_jsonld_fusion_intelligente(*args, **kwargs):
    from views.jsonld_analyzer import render_jsonld_fusion_intelligente as _fn
    return _fn(*args, **kwargs)


__all__ = [
    "render_master_tab",
    "render_master_tab_for_jsonld",
    "render_methodologie_for_module",
    "render_jsonld_analyzer_tab",
    "render_jsonld_fusion_intelligente",
]
