"""PDF-faithful HTML renderer + A2UI/DSL passthrough.

Fidelity fixes vs v1 (the "渲染与 PDF 不一致" issues):
- The card renders at the token canvas size (e.g. 2x2 = 190x190) with the
  measured corner radius (radius ~= 0.2 * width for squares, ~h/3 for bars),
  instead of a borderless auto-height grid.
- Real card chrome: gradient or white surface, top title row with round icon
  chip, hero number with unit, translucent pill buttons, ring progress via
  conic-gradient, status chips — the visual grammar of the reference pages.
- Two text tones only (content/support) and one accent, like the PDF.
"""
from html import escape
import json

from genui_intent.renderers import A2UIRenderer, DslRenderer
from .tokens import SIZES, SPACING, TYPE, icon_for


def _fmt_value(content, fallback="—"):
    value = content.get("value", fallback)
    return "" if value is None else str(value)


def _component_markup(item, slot, tokens):
    if item is None:
        glyph = {"ICON": "◐", "IMAGE": "▨", "CHART": "▁▃▅▇"}.get(slot.get("placeholder", "ICON"), "◐")
        return '<div class="chip ph">%s</div>' % glyph
    kind = item["type"]
    content = item.get("content", {})
    raw_label = str(item.get("label") or "")
    presentation = item.get("presentation", {})
    show_label = presentation.get("showLabel", True) and raw_label
    label = ('<span class="lbl">%s</span>' % escape(raw_label)) if show_label else ""
    # a hidden label survives as the accessibility name — elision is visual only
    a11y = (' aria-label="%s" title="%s"' % (escape(raw_label), escape(raw_label))) if (raw_label and not show_label) else ""
    unbound = ' data-unbound="1"' if content.get("unbound") else ""
    attrs = unbound + a11y
    if kind == "METRIC":
        unit = escape(str(content.get("unit") or ""))
        return ('<div class="metric"%s>%s'
                '<span class="hero">%s<i>%s</i></span></div>'
                % (attrs, label, escape(_fmt_value(content)), unit))
    if kind == "PROGRESS":
        value = content.get("value") or 0
        try:
            pct = max(0, min(100, float(value)))
        except (TypeError, ValueError):
            pct = 0
        return ('<div class="progress"%s style="--p:%s">'
                '<span class="ring"><b>%s<i>%%</i></b></span>%s</div>'
                % (attrs, pct, escape(str(value)), label))
    if kind == "STATUS":
        return ('<div class="status"%s>%s<b>%s</b></div>'
                % (attrs, label, escape(str(content.get("text", "—")))))
    if kind == "SWITCH":
        checked = " on" if content.get("checked") else ""
        return ('<div class="switchrow"%s>%s'
                '<span class="switch%s"><span class="knob"></span></span></div>'
                % (attrs, label, checked))
    if kind == "SLIDER":
        value = content.get("value") or 50
        return ('<div class="sliderrow"%s>%s'
                '<span class="slider" style="--p:%s"></span></div>' % (attrs, label, value))
    if kind == "BUTTON":
        glyph = icon_for(item.get("semanticKey"), item.get("label"))
        return ('<div class="pill"%s><span class="pilligo">%s</span><span>%s</span></div>'
                % (unbound, glyph, escape(str(content.get("text") or item.get("label") or "执行"))))
    if kind == "LIST":
        if presentation.get("variant") == "chips":
            chips = "".join('<span class="chipbtn">%s</span>' % escape(str(row.get("title", "")))
                            for row in content.get("items", [])[:10])
            return '<div class="chiprow"%s>%s</div>' % (attrs, chips or "")
        rows = "".join('<li><i class="dot"></i>%s</li>' % escape(str(row.get("title", "")))
                       for row in content.get("items", [])[:4])
        return '<div class="listbox"%s>%s<ul class="list">%s</ul></div>' % (attrs, label, rows or "<li>暂无内容</li>")
    if kind == "IMAGE":
        return '<div class="media"%s>▨<span>%s</span></div>' % (attrs, escape(raw_label) if show_label else "")
    if kind == "ICON":
        return '<div class="chip"%s>%s</div>' % (attrs, icon_for(item.get("semanticKey"), raw_label))
    return ('<div class="text"%s>%s<p>%s</p></div>'
            % (attrs, label, escape(str(content.get("text") or item.get("label") or ""))))


def _card_css(size, tokens):
    dims = SIZES[size]
    grad = ("linear-gradient(150deg,%s,%s)" % (tokens["bg"], tokens["bg2"])
            if tokens.get("bg2") else tokens["bg"])
    shadow = "0 10px 28px rgba(20,32,60,.16)" if tokens.get("on") == "dark" else "0 10px 28px rgba(20,32,60,.28)"
    return """
.gv2-card{position:relative;width:%(w)spx;height:%(h)spx;border-radius:%(r)spx;background:%(bg)s;
  color:%(fg)s;padding:%(pad)spx;box-sizing:border-box;overflow:hidden;box-shadow:%(shadow)s;
  font-family:'HarmonyOS Sans','PingFang SC','Microsoft YaHei',system-ui,sans-serif}
.gv2-card .grid{display:grid;width:100%%;height:100%%;grid-template-columns:repeat(12,1fr);
  grid-template-rows:repeat(%(rows)s,1fr);gap:%(gap)spx}
.gv2-card .titlebar{position:absolute;top:%(pad)spx;left:%(pad)spx;right:%(pad)spx;display:flex;
  justify-content:space-between;align-items:center;pointer-events:none}
.gv2-card .titlebar .t{font-size:%(title)spx;font-weight:700}
.gv2-card .chip{width:%(chip)spx;height:%(chip)spx;border-radius:50%%;background:%(chipbg)s;
  display:flex;align-items:center;justify-content:center;font-size:%(chipfs)spx;flex-shrink:0}
.gv2-card .chip.ph{opacity:.85}
.gv2-card section{min-width:0;min-height:0;display:flex;align-items:stretch}
.gv2-card section>*{width:100%%}
.gv2-card .lbl{display:block;font-size:%(label)spx;font-weight:500;color:%(support)s;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gv2-card .metric{display:flex;flex-direction:column;justify-content:center;gap:2px}
.gv2-card .hero{font-size:%(hero)spx;font-weight:700;line-height:1.05;letter-spacing:-.5px}
.gv2-card .hero i{font-style:normal;font-size:%(herounit)spx;font-weight:600;margin-left:2px;color:%(support)s}
.gv2-card .status{display:flex;flex-direction:column;justify-content:center;gap:2px}
.gv2-card .status b{font-size:15px;font-weight:700;line-height:1.3;display:-webkit-box;
  -webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.gv2-card .text p{margin:2px 0 0;font-size:%(body)spx;line-height:1.45;color:%(fg)s;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.gv2-card .pill{display:flex;align-items:center;justify-content:center;gap:6px;height:%(pillh)spx;
  align-self:center;border-radius:%(pillr)spx;background:%(pillbg)s;color:%(pillfg)s;
  font-size:%(btn)spx;font-weight:600;padding:0 14px;white-space:nowrap}
.gv2-card .pilligo{font-size:14px}
.gv2-card .switchrow,.gv2-card .sliderrow{display:flex;flex-direction:column;justify-content:center;gap:6px}
.gv2-card .switch{width:40px;height:22px;border-radius:11px;background:%(chipbg)s;position:relative;transition:.2s}
.gv2-card .switch.on{background:%(accent)s}
.gv2-card .switch .knob{position:absolute;top:2px;left:2px;width:18px;height:18px;border-radius:50%%;
  background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.gv2-card .switch.on .knob{left:20px}
.gv2-card .slider{display:block;height:6px;border-radius:3px;background:%(chipbg)s;position:relative}
.gv2-card .slider::after{content:'';position:absolute;left:0;top:0;bottom:0;width:calc(var(--p)*1%%);
  border-radius:3px;background:%(accent)s}
.gv2-card .progress{display:flex;flex-direction:column;align-items:flex-start;gap:4px;justify-content:center}
.gv2-card .ring{width:%(ring)spx;height:%(ring)spx;border-radius:50%%;display:flex;align-items:center;justify-content:center;
  background:conic-gradient(%(accent)s calc(var(--p)*1%%),%(chipbg)s 0);position:relative}
.gv2-card .ring::before{content:'';position:absolute;inset:6px;border-radius:50%%;background:%(bgflat)s}
.gv2-card .ring b{position:relative;font-size:15px;font-weight:700}
.gv2-card .ring b i{font-style:normal;font-size:10px;font-weight:500;color:%(support)s}
.gv2-card .listbox{display:flex;flex-direction:column;justify-content:center;gap:4px;height:100%%}
.gv2-card .chiprow{display:flex;gap:6px;align-items:center;height:100%%;overflow-x:auto;
  scrollbar-width:none;-webkit-overflow-scrolling:touch}
.gv2-card .chiprow::-webkit-scrollbar{display:none}
.gv2-card .chipbtn{flex-shrink:0;height:28px;line-height:28px;padding:0 13px;border-radius:14px;
  background:%(pillbg)s;color:%(pillfg)s;font-size:12px;font-weight:500;white-space:nowrap}
.gv2-card .media{width:100%%;height:100%%;border-radius:12px;background:%(chipbg)s;display:flex;
  flex-direction:column;align-items:center;justify-content:center;gap:2px;font-size:20px;opacity:.9}
.gv2-card .media span{font-size:10px;color:%(support)s}
.gv2-card .list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;justify-content:center;gap:5px}
.gv2-card .list li{font-size:%(listfs)spx;display:flex;align-items:center;gap:6px;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.gv2-card .dot{width:5px;height:5px;border-radius:50%%;background:%(accent)s;flex-shrink:0}
.gv2-card [data-unbound]{opacity:.55}
""" % {"w": dims["w"], "h": dims["h"], "r": dims["radius"], "pad": dims["padding"],
       "rows": dims["grid_rows"], "gap": SPACING["gap"], "bg": grad,
       "bgflat": tokens.get("bg2") and tokens["bg2"] or tokens["bg"],
       "fg": tokens["fg"], "support": tokens["support"], "accent": tokens["accent"],
       "chipbg": tokens["chip"], "chip": SPACING["chip_small"], "chipfs": 15,
       "pillbg": tokens["pillBg"], "pillfg": tokens["pillFg"],
       "pillh": SPACING["pill_h"], "pillr": SPACING["pill_h"] // 2, "ring": SPACING["ring"],
       "shadow": shadow,
       "title": TYPE["title"]["size"], "label": TYPE["label"]["size"], "body": TYPE["body"]["size"],
       "hero": TYPE["hero"]["size"], "herounit": TYPE["hero_unit"]["size"],
       "metric": TYPE["metric"]["size"], "btn": TYPE["button"]["size"], "listfs": TYPE["list"]["size"]}


def render_html(spec):
    tokens = spec["style"]["tokens"]
    size = spec["surface"]["size"]
    grid = spec["grid"]
    hero_keys = [item.get("component", {}).get("semanticKey") for item in spec["slots"]
                 if item.get("component") and item["component"]["role"] in ("PRIMARY", "WARNING")]
    title_glyph = icon_for(hero_keys[0] if hero_keys else "", spec.get("title") or "")
    sections = []
    for item in spec["slots"]:
        rect = item["rect"]
        markup = _component_markup(item.get("component"), item, tokens)
        sections.append('<section style="grid-column:%d/span %d;grid-row:%d/span %d">%s</section>'
                        % (rect["x"] + 1, rect["w"], rect["y"] + 1, rect["h"], markup))
    show_titlebar = (bool(spec.get("title")) and size != "2x1"
                     and spec.get("layoutMode") == "FREE")
    titlebar = ('<div class="titlebar"><span class="t">%s</span><span class="chip">%s</span></div>'
                % (escape(spec["title"]), title_glyph)) if show_titlebar else ""
    card_class = "gv2-card with-title" if show_titlebar else "gv2-card"
    html = ('<div class="%s" data-template="%s" data-size="%s">%s<div class="grid">%s</div></div>'
            % (card_class, escape(spec["template"]), escape(size), titlebar, "".join(sections)))
    css = _card_css(size, tokens) + (
        ".gv2-card.with-title .grid{height:calc(100%% - %(off)dpx);margin-top:%(off)dpx}"
        % {"off": SPACING["chip_small"] + 6})
    return {"protocol": "html_css", "files": {"card.html": html, "card.css": css},
            "standalone": "<style>%s</style>%s" % (css, html)}


def render_all(spec):
    return {"html_css": render_html(spec),
            "a2ui": A2UIRenderer().render(spec),
            "dsl": DslRenderer().render(spec)}
