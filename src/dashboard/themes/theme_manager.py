import os

THEMES_DIR = os.path.dirname(os.path.abspath(__file__))

# Map of UI-friendly theme names to their corresponding CSS files
THEMES = {
    "FinPulse Dark": "dark.css",
    "Bloomberg Terminal": "bloomberg.css",
    "Light Professional": "light.css"
}

def get_theme_css(theme_name: str) -> str:
    """Returns the CSS string for the specified theme."""
    filename = THEMES.get(theme_name, "dark.css")
    css_path = os.path.join(THEMES_DIR, filename)
    
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def get_chart_theme(theme_name: str) -> dict:
    """Returns the Plotly chart configuration for the specified theme."""
    if theme_name == "Bloomberg Terminal":
        return dict(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#BDBDBD", size=11),
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(gridcolor="rgba(255,152,0,0.1)", linecolor="rgba(255,152,0,0.2)"),
            yaxis=dict(gridcolor="rgba(255,152,0,0.1)", linecolor="rgba(255,152,0,0.2)"),
            hoverlabel=dict(bgcolor="#121212", bordercolor="#FF9800", font_size=12, font_family="Inter"),
        )
    elif theme_name == "Light Professional":
        return dict(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#64748B", size=11),
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(gridcolor="rgba(0,0,0,0.06)", linecolor="rgba(0,0,0,0.12)"),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)", linecolor="rgba(0,0,0,0.12)"),
            hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#2563EB", font_size=12, font_family="Inter"),
        )
    else:
        # FinPulse Dark (Default)
        return dict(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#5C6370", size=11),
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.06)"),
            hoverlabel=dict(bgcolor="#131720", bordercolor="#F5A623", font_size=12, font_family="Inter"),
        )

def get_sentiment_scale(theme_name: str) -> list:
    """Returns the Plotly colorscale array for sentiment mapping based on theme."""
    if theme_name == "Bloomberg Terminal":
        # Green / Yellow / Red from the bloomberg theme tokens
        return [[0.0,"#FF1744"],[0.5,"#FFEA00"],[1.0,"#00E676"]]
    elif theme_name == "Light Professional":
        return [[0.0,"#DC2626"],[0.5,"#D97706"],[1.0,"#059669"]]
    else:
        return [[0.0,"#E74C3C"],[0.5,"#F39C12"],[1.0,"#2ECC71"]]
