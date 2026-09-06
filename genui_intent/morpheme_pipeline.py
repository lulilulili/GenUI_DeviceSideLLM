"""Observable MorphemeDraft-to-render pipeline."""
import json

from .events import Trace, TracedProvider
from .morpheme import (MORPHEME_SYSTEM_PROMPT, build_morpheme_prompt,
                       apply_information_budget, expand_draft, fill_mock_data,
                       morpheme_schema, reconcile_types, validate_draft,
                       SEMANTIC_REVIEW_SYSTEM_PROMPT, build_semantic_review_prompt)
from .layout_engine import plan as plan_layout, render_spec as build_render_spec
from .renderers import render
from .pipeline import IntentGenerationError


class MorphemePipeline:
    def __init__(self, provider, on_event=None):
        self.provider, self.on_event = provider, on_event

    def generate(self, user_prompt, card_size="AUTO", render_protocol="html_css", style_id="neutral", semantic_review=False):
        if card_size not in ("AUTO", "2x1", "2x2", "3x2", "3x3"):
            raise ValueError("未知卡片尺寸")
        trace = Trace(self.on_event)
        provider = TracedProvider(self.provider, trace)
        with trace.stage("preprocess", user_prompt) as event:
            text = user_prompt.strip()
            if not text:
                raise ValueError("用户提示词不能为空")
            event["output"] = text
        with trace.stage("morpheme_prompt", text) as event:
            prompt, schema = build_morpheme_prompt(text, card_size), morpheme_schema(card_size)
            event["output"] = {"system": MORPHEME_SYSTEM_PROMPT, "user": prompt, "schema": schema}
        for attempt in range(2):
            raw = provider.complete(MORPHEME_SYSTEM_PROMPT, prompt, max_tokens=320, temperature=0.0, schema=schema)
            try:
                with trace.stage("morpheme_decode_" + str(attempt), raw) as event:
                    draft = json.loads(raw)
                    event["output"] = draft
                with trace.stage("morpheme_validate_" + str(attempt), draft) as event:
                    errors = validate_draft(draft, card_size)
                    event["output"] = {"errors": errors}
                    if errors:
                        raise IntentGenerationError("; ".join(errors))
                break
            except (ValueError, TypeError, IntentGenerationError) as exc:
                if attempt:
                    raise IntentGenerationError("Morpheme输出两次校验失败: " + str(exc)) from exc
                with trace.stage("repair", {"error": str(exc)}) as event:
                    prompt += "\n校验错误=" + str(exc) + "\n只修正JSON。"
                    event["output"] = prompt
        if semantic_review:
            with trace.stage("semantic_review_prompt", draft) as event:
                review_prompt = build_semantic_review_prompt(text, draft)
                event["output"] = {"system": SEMANTIC_REVIEW_SYSTEM_PROMPT, "user": review_prompt, "schema": schema}
            reviewed_raw = provider.complete(SEMANTIC_REVIEW_SYSTEM_PROMPT, review_prompt, max_tokens=320, temperature=0.0, schema=schema)
            with trace.stage("semantic_review", reviewed_raw) as event:
                reviewed = json.loads(reviewed_raw)
                review_errors = validate_draft(reviewed, card_size)
                if review_errors:
                    raise IntentGenerationError("语义审校输出无效: " + "; ".join(review_errors))
                event["output"] = {"before": draft, "after": reviewed}
                draft = reviewed
        with trace.stage("morpheme_expand", draft) as event:
            spec = expand_draft(draft)
            event["output"] = spec
        with trace.stage("type_reconcile", spec) as event:
            spec, corrections = reconcile_types(spec)
            event["output"] = {"spec": spec, "corrections": corrections}
        with trace.stage("information_budget", {"size": card_size, "spec": spec}) as event:
            spec, budget = apply_information_budget(spec, card_size)
            event["output"] = {"spec": spec, "budget": budget}
        with trace.stage("mock_data", spec) as event:
            spec = fill_mock_data(spec)
            event["output"] = spec
        with trace.stage("layout", {"spec": spec, "style": style_id}) as event:
            layout = plan_layout(spec, style_id)
            event["output"] = layout
        with trace.stage("render_spec", layout) as event:
            render_spec = build_render_spec(spec, layout)
            event["output"] = render_spec
        with trace.stage("codegen", {"renderSpec": render_spec, "protocol": render_protocol}) as event:
            protocol_outputs = {name: render(render_spec, name) for name in ("dsl", "a2ui", "html_css")}
            rendered = protocol_outputs[render_protocol]
            event["output"] = {"selectedProtocol": render_protocol, "outputs": protocol_outputs}
        code = (rendered.get("files", {}).get("card.html") or rendered.get("code") or
                rendered.get("ndjson"))
        result = {"draft": draft, "morphemeSpec": spec, "layout": layout,
                  "renderSpec": render_spec, "rendered": rendered,
                  "protocolOutputs": protocol_outputs, "code": code}
        trace.emit("result", "completed", output=result)
        return result
