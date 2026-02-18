# Eco-Score : calculatrice d'impact carbone (UI dans views/)


def render_eco_tab(*args, **kwargs):
    from views.eco_impact import render_eco_tab as _fn
    return _fn(*args, **kwargs)


__all__ = ["render_eco_tab"]
