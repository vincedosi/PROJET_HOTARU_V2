# HOME - UI dans views/ (découplage Streamlit)


def render_home(*args, **kwargs):
    from views.home import render_home as _fn
    return _fn(*args, **kwargs)
