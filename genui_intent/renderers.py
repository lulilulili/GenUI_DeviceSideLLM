"""Pluggable output protocols consuming one stable RenderSpec."""
from html import escape
import json


def _component_markup(component):
    if component is None:
        return '<div class="media-placeholder">IMAGE PLACEHOLDER</div>'
    kind, label, content = component["type"], escape(component.get("label") or ""), component.get("content", {})
    if kind in ("METRIC", "PROGRESS"):
        value = escape(str(content.get("value", "—"))) + escape(str(content.get("unit", "")))
        body = f'<strong>{value}</strong>'
    elif kind == "STATUS":
        body = '<strong>' + escape(str(content.get("text", "状态正常"))) + '</strong>'
    elif kind == "SWITCH":
        body = '<button type="button" role="switch" aria-checked="true"></button>'
    elif kind == "SLIDER":
        body = '<input type="range">'
    elif kind == "BUTTON":
        body = '<button type="button">' + escape(str(content.get("text", label or "执行"))) + '</button>'
    elif kind == "LIST":
        body = '<ul>' + ''.join('<li>' + escape(str(item.get("title", ""))) + '</li>' for item in content.get("items", [])) + '</ul>'
    else:
        body = '<p>' + escape(str(content.get("text", label))) + '</p>'
    return f'<div class="morpheme morpheme-{kind.lower()}" data-morpheme="{escape(kind)}"><span>{label}</span>{body}</div>'


class HtmlCssRenderer:
    protocol = "html_css"

    def render(self, spec):
        tokens = spec["style"]["tokens"]
        slots = []
        for item in spec["slots"]:
            rect = item["rect"]
            markup = _component_markup(item.get("component")) if not item.get("placeholder") else '<div class="media-placeholder">' + escape(item["placeholder"]) + ' PLACEHOLDER</div>'
            slots.append(f'<section data-slot="{escape(item["id"])}" style="grid-column:{rect["x"]+1}/span {rect["w"]};grid-row:{rect["y"]+1}/span {rect["h"]}">{markup}</section>')
        html = f'<article class="genui-card" data-template="{escape(spec["template"])}" data-size="{escape(spec["surface"]["size"])}"><h2>{escape(spec.get("title") or "")}</h2><div class="layout-grid">{"".join(slots)}</div></article>'
        css = '.genui-card{background:var(--card-bg);color:var(--card-fg);border-radius:var(--radius);padding:20px}.layout-grid{display:grid;grid-template-columns:repeat(12,1fr);grid-template-rows:repeat(' + str(spec["grid"]["rows"]) + ',1fr);gap:8px}'
        variables = {"--card-bg": tokens["cardBg"], "--card-fg": tokens["cardFg"], "--accent": tokens["accent"], "--muted": tokens["muted"], "--radius": str(tokens["radius"]) + "px"}
        return {"protocol": self.protocol, "files": {"card.html": html, "card.css": css}, "variables": variables}


class A2UIRenderer:
    protocol = "a2ui"

    def render(self, spec):
        messages = _a2ui_messages(spec)
        return {"protocol": self.protocol, "version": "v0.9", "messages": messages,
                "ndjson": "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in messages)}


def _node_type_and_props(component, placeholder=None):
    if component is None:
        return "Image", {"src": "", "width": "fill_container", "height": "fill_container",
                         "alt": (placeholder or "IMAGE") + " PLACEHOLDER"}
    kind, content = component["type"], component.get("content", {})
    if kind in ("BUTTON", "SWITCH", "SLIDER"):
        return "Button", {"label": str(content.get("text") or component.get("label") or kind), "enabled": True}
    if kind in ("IMAGE", "ICON"):
        return "Image", {"src": str(content.get("src", "")), "width": "fill_container", "height": "fill_container"}
    if kind == "LIST":
        text = " · ".join(str(x.get("title", "")) for x in content.get("items", [])) or component.get("label", "列表")
    elif kind in ("METRIC", "PROGRESS"):
        text = str(content.get("value", "—")) + str(content.get("unit", ""))
    else:
        text = str(content.get("text") or component.get("label") or "")
    return "Text", {"content": text, "fontSize": 24 if kind in ("METRIC", "PROGRESS") else 14,
                    "fontWeight": "500", "fontColor": "#E7F0FA", "maxLines": 4, "textOverflow": "ellipsis"}


def _protocol_nodes(spec):
    slot_ids = ["slot_" + item["id"] for item in spec["slots"]]
    nodes = [("root", "Card", {"title": spec.get("title"), "layout": "vertical", "gap": 8,
              "width": "fill_container", "fill": spec["style"]["tokens"]["cardBg"],
              "radius": spec["style"]["tokens"]["radius"]}, ["layout_grid"]),
             ("layout_grid", "Grid", {"columnsTemplate": " ".join(["1fr"] * 12), "space": 8,
              "width": "fill_container", "height": "fill_container"}, slot_ids)]
    for item, slot_id in zip(spec["slots"], slot_ids):
        rect = item["rect"]
        content_id = slot_id + "_content"
        nodes.append((slot_id, "Card", {"layout": "vertical", "width": "fill_container",
                      "gridColumn": f"{rect['x'] + 1} / span {rect['w']}",
                      "gridRow": f"{rect['y'] + 1} / span {rect['h']}", "padding": 8,
                      "fill": spec["style"]["tokens"]["muted"], "radius": 12}, [content_id]))
        kind, props = _node_type_and_props(item.get("component"), item.get("placeholder"))
        nodes.append((content_id, kind, props, None))
    return nodes


def _a2ui_messages(spec):
    surface = "generated-card"
    messages = [{"version": "v0.9", "createSurface": {"surfaceId": surface,
                "catalogId": "genUI_basic_catalog", "theme": {"primaryColor": spec["style"]["tokens"]["accent"]}}}]
    for node_id, kind, props, children in _protocol_nodes(spec):
        component = {"id": node_id, "component": "Extended." + kind, **props}
        if children is not None:
            component["children"] = children
        messages.append({"version": "v0.9", "updateComponents": {"surfaceId": surface,
                         "components": [component]}})
    return messages


class DslRenderer:
    protocol = "dsl"

    def render(self, spec):
        surface = "generated-card"
        lines = ['{"@' + surface + '","genUI_basic_catalog",' +
                 json.dumps({"primaryColor": spec["style"]["tokens"]["accent"]}, ensure_ascii=False, separators=(",", ":")) + '}']
        for node_id, kind, props, children in _protocol_nodes(spec):
            parts = [json.dumps(surface), json.dumps(node_id), json.dumps(kind),
                     json.dumps(props, ensure_ascii=False, separators=(",", ":"))]
            if children is not None:
                parts.append(json.dumps(children, ensure_ascii=False, separators=(",", ":")))
            lines.append("{" + ",".join(parts) + "}")
        return {"protocol": self.protocol, "format": "minimal-genui-brace-tuple-jsonl",
                "parserTarget": "GenUI_askr/genui-sdk/mini-parser", "lines": lines, "code": "\n".join(lines)}


RENDERERS = {"dsl": DslRenderer(), "a2ui": A2UIRenderer(), "html_css": HtmlCssRenderer()}


def render(spec, protocol="html_css"):
    if protocol not in RENDERERS:
        raise ValueError("未知渲染协议: " + protocol)
    return RENDERERS[protocol].render(spec)
