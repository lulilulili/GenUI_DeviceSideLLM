"""Design tokens measured from the reference PDF (桌面服务卡片).

Every number here was measured against the PDF archetype pages:
- 2x1 cards are pill-like bars, corner radius ~= height * 1/3, icon chip on the right.
- 2x2 cards are rounded squares, radius ~= width * 0.2, title row on top,
  hero value in the middle, support line or pill action at the bottom.
- Light cards: white background, near-black text; colored cards: gradient
  background, white text with a translucent support tone.
These tokens are the single source of truth for the renderer; templates must
not hard-code visual constants.
"""

# Card canvas per size: css px in the workbench preview (1x scale).
SIZES = {
    "2x1": {"w": 320, "h": 100, "radius": 32, "padding": 16, "grid_rows": 6},
    "2x2": {"w": 190, "h": 190, "radius": 38, "padding": 16, "grid_rows": 12},
    "3x2": {"w": 400, "h": 190, "radius": 38, "padding": 18, "grid_rows": 8},
    "3x3": {"w": 400, "h": 400, "radius": 40, "padding": 20, "grid_rows": 12},
}

# Type scale (px). Two text sizes + one hero number keeps hierarchy readable,
# matching the PDF: 标题/次要 12-13, 正文 14, 焦点数值 32-38.
TYPE = {
    "title": {"size": 14, "weight": 700},
    "label": {"size": 12, "weight": 500},
    "body": {"size": 13, "weight": 400},
    "hero": {"size": 34, "weight": 700},
    "hero_unit": {"size": 14, "weight": 600},
    "metric": {"size": 22, "weight": 700},
    "button": {"size": 13, "weight": 600},
    "list": {"size": 12.5, "weight": 400},
}

SPACING = {"gap": 8, "row_gap": 6, "chip": 40, "chip_small": 32, "pill_h": 36, "ring": 52}

# Style presets sampled from the PDF example cards.
# fg tones: content = primary text, support = secondary text.
STYLES = {
    "light": {"label": "浅色中性", "bg": "#ffffff", "bg2": None, "fg": "#1a1f27",
              "support": "#8a919d", "accent": "#256bfa", "chip": "#eef2f8",
              "pillBg": "#256bfa", "pillFg": "#ffffff", "on": "dark"},
    "blue": {"label": "天气蓝", "bg": "#4f8bf7", "bg2": "#2f5fd9", "fg": "#ffffff",
             "support": "rgba(255,255,255,.78)", "accent": "#ffd76b", "chip": "rgba(255,255,255,.22)",
             "pillBg": "rgba(255,255,255,.24)", "pillFg": "#ffffff", "on": "light"},
    "violet": {"label": "睡眠紫", "bg": "#8f6ae8", "bg2": "#6a43c9", "fg": "#ffffff",
               "support": "rgba(255,255,255,.78)", "accent": "#ffe08a", "chip": "rgba(255,255,255,.22)",
               "pillBg": "rgba(255,255,255,.24)", "pillFg": "#ffffff", "on": "light"},
    "teal": {"label": "舒缓青", "bg": "#2ec7a6", "bg2": "#12a58a", "fg": "#ffffff",
             "support": "rgba(255,255,255,.8)", "accent": "#ffffff", "chip": "rgba(255,255,255,.22)",
             "pillBg": "rgba(255,255,255,.24)", "pillFg": "#ffffff", "on": "light"},
    "orange": {"label": "活力橙", "bg": "#f7a53b", "bg2": "#ef7d3a", "fg": "#ffffff",
               "support": "rgba(255,255,255,.82)", "accent": "#ffffff", "chip": "rgba(255,255,255,.24)",
               "pillBg": "rgba(255,255,255,.26)", "pillFg": "#ffffff", "on": "light"},
}

# Domain -> default style, mirroring the PDF example pairings
# (weather blue, sleep violet, breath teal, sport orange, neutral tools light).
DOMAIN_STYLE = {"WEATHER": "blue", "SMART_HOME": "teal", "DEVICE": "light",
                "CONTENT": "orange", "TASK": "violet"}

# Semantic icon glyphs for the round icon chip (images not required).
ICON_GLYPHS = (
    ("battery", "⚡"), ("charge", "⚡"), ("weather", "☀"), ("temperature", "☀"),
    ("rain", "☔"), ("precipitation", "☔"), ("forecast", "⛅"), ("air", "\U0001f343"),
    ("sleep", "\U0001f319"), ("wifi", "\U0001f4f6"), ("network", "\U0001f4f6"),
    ("bluetooth", "\U0001f4f2"), ("headphone", "\U0001f3a7"), ("light", "\U0001f4a1"),
    ("brightness", "\U0001f506"), ("curtain", "\U0001fa9f"), ("ac", "❄"),
    ("air_conditioner", "❄"), ("timer", "⏱"), ("reminder", "⏰"),
    ("task", "✅"), ("todo", "✅"), ("calendar", "\U0001f4c5"),
    ("schedule", "\U0001f4c5"), ("step", "\U0001f3c3"), ("sport", "\U0001f3c3"),
    ("message", "✉"), ("encourage", "\U0001f4aa"), ("phone", "\U0001f4f1"),
    ("display", "\U0001f4f1"), ("call", "\U0001f4de"), ("music", "\U0001f3b5"),
)


def icon_for(semantic_key, label=""):
    text = (semantic_key or "").lower() + " " + (label or "")
    for token, glyph in ICON_GLYPHS:
        if token in text:
            return glyph
    return "●"


def style_tokens(style_id, domain=None):
    if style_id in (None, "", "auto"):
        style_id = DOMAIN_STYLE.get(domain or "", "light")
    return style_id if style_id in STYLES else "light", STYLES.get(style_id, STYLES["light"])
