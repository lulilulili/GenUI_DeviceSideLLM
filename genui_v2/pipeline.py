"""GenUI v2 pipeline: one LLM call for semantics, deterministic everything else.

用户话语 → 规则路由(领域) → LLM MorphemeDraft v2(≤1次纠错)
→ 组件推导 → 能力绑定(真实注册表, 不再mock) → 尺寸/信息预算
→ PDF原型匹配 或 层级式自由布局 → RenderSpec → HTML/A2UI/DSL
"""
import json

from genui_intent.events import Trace, TracedProvider
from . import protocol
from .capability import bind, keys_for_domain
from .derive import apply as derive_components
from .elision import plan_label_visibility
from .layout import plan as plan_layout, render_spec as build_render_spec
from .render import render_all
from .router import route


class GenerationError(RuntimeError):
    pass


class PipelineV2:
    def __init__(self, provider, on_event=None):
        self.provider, self.on_event = provider, on_event

    def generate(self, user_prompt, card_size="AUTO", style_id="auto"):
        if card_size not in ("AUTO", "2x1", "2x2", "3x2", "3x3"):
            raise ValueError("未知卡片尺寸")
        trace = Trace(self.on_event)
        provider = TracedProvider(self.provider, trace)
        with trace.stage("preprocess", user_prompt) as event:
            text = user_prompt.strip()
            if not text:
                raise ValueError("用户提示词不能为空")
            event["output"] = text
        with trace.stage("route", text) as event:
            domain = route(text, provider)
            event["output"] = domain or "UNKNOWN"
        with trace.stage("prompt", {"domain": domain, "size": card_size}) as event:
            system, user = protocol.build_messages(
                text, card_size, domain, keys_for_domain(domain) if domain else ())
            schema = protocol.schema(card_size)
            event["output"] = {"system": system, "user": user, "schema": schema}
        draft = None
        for attempt in range(2):
            raw = provider.complete(system, user, max_tokens=280, temperature=0.0, schema=schema)
            try:
                with trace.stage("decode_%d" % attempt, raw) as event:
                    draft = json.loads(raw)
                    event["output"] = draft
                with trace.stage("validate_%d" % attempt, draft) as event:
                    errors = protocol.validate_draft(draft, card_size)
                    event["output"] = {"errors": errors}
                    if errors:
                        raise GenerationError("; ".join(errors))
                break
            except (ValueError, TypeError, GenerationError) as exc:
                if attempt:
                    raise GenerationError("模型输出两次校验失败: " + str(exc)) from exc
                with trace.stage("repair", {"error": str(exc)}) as event:
                    user += "\n校验错误=" + str(exc) + "\n只输出修正后的单行JSON。"
                    event["output"] = user
        with trace.stage("normalize", draft) as event:
            draft, role_corrections = protocol.normalize_draft(draft)
            event["output"] = {"draft": draft, "corrections": role_corrections}
        with trace.stage("expand", draft) as event:
            spec = protocol.expand_draft(draft, card_size)
            event["output"] = spec
        with trace.stage("capability_bind", spec) as event:
            spec, bind_report = bind(spec, domain)
            event["output"] = {"spec": spec, "report": bind_report}
        with trace.stage("derive_components", spec) as event:
            spec, decisions = derive_components(spec)
            event["output"] = {"spec": spec, "decisions": decisions}
        with trace.stage("budget", spec) as event:
            size = card_size if card_size != "AUTO" else protocol.resolve_auto_size(spec)
            spec, budget = protocol.apply_information_budget(spec, size)
            event["output"] = {"spec": spec, "budget": budget}
        with trace.stage("label_elision", spec) as event:
            spec, label_decisions = plan_label_visibility(spec)
            event["output"] = {"decisions": label_decisions}
        with trace.stage("layout", {"size": spec["surface"]["size"], "style": style_id}) as event:
            layout = plan_layout(spec, style_id, domain)
            event["output"] = layout
        with trace.stage("render_spec", layout) as event:
            spec_out = build_render_spec(spec, layout)
            event["output"] = spec_out
        with trace.stage("codegen", {"template": spec_out["template"]}) as event:
            outputs = render_all(spec_out)
            event["output"] = {"outputs": {"html_css": {"files": list(outputs["html_css"]["files"])},
                                           "a2ui": "…", "dsl": "…"}}
        result = {"domain": domain, "draft": draft, "roleCorrections": role_corrections,
                  "labelDecisions": label_decisions, "morphemeSpec": spec,
                  "bindReport": bind_report, "componentDecisions": decisions,
                  "budget": budget, "layout": layout, "renderSpec": spec_out,
                  "protocolOutputs": outputs, "code": outputs["html_css"]["standalone"]}
        trace.emit("result", "completed", output=result)
        return result


class MockProviderV2:
    """Offline demo provider emitting a draft v2 for the classic headphone case."""

    def complete(self, system, user, max_tokens=280, temperature=0.0, schema=None):
        if max_tokens <= 12:
            return "DEVICE"
        self.last_usage = {"inputTokens": 410, "outputTokens": 96, "source": "mock"}
        return json.dumps({
            "t": "耳机状态",
            "m": [{"l": "耳机电量", "q": "headphones.battery.level", "f": "PERCENTAGE", "r": "PRIMARY"},
                  {"l": "连接状态", "q": "headphones.connection.status", "f": "ENUM", "r": "SECONDARY"},
                  {"l": "蓝牙", "q": "bluetooth.power", "f": "BOOLEAN", "r": "PRIMARY_ACTION"}],
        }, ensure_ascii=False)
