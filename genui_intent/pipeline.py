import json
from .compact import COMPACT_SYSTEM_PROMPT, build_compact_prompt, compact_schema, expand_compact
from .events import Trace, TracedProvider
from .registries import REGISTRIES
from .router import route
from .validation import validate

class IntentGenerationError(RuntimeError):
    pass

class IntentPipeline:
    def __init__(self, provider, on_event=None):
        self.provider, self.on_event = provider, on_event

    def generate(self, user_prompt):
        trace = Trace(self.on_event)
        provider = TracedProvider(self.provider, trace)
        with trace.stage("preprocess", user_prompt) as event:
            text = user_prompt.strip()
            if not text:
                raise ValueError("用户提示词不能为空")
            event["output"] = text
        with trace.stage("route", text) as event:
            domain = route(text, provider)
            event["output"] = domain
            if domain not in REGISTRIES:
                raise IntentGenerationError("请求不属于当前启用的五个领域")
        with trace.stage("prompt", {"domain": domain}) as event:
            prompt = build_compact_prompt(text, domain, REGISTRIES[domain])
            schema = compact_schema(domain, REGISTRIES[domain])
            event["output"] = dict(system=COMPACT_SYSTEM_PROMPT, user=prompt, schema=schema)
        for attempt in range(2):
            raw = provider.complete(COMPACT_SYSTEM_PROMPT, prompt, max_tokens=240,
                                    temperature=0.0, schema=schema)
            try:
                with trace.stage("decode_" + str(attempt), raw) as event:
                    compact = json.loads(raw)
                    event["output"] = compact
                with trace.stage("normalize_" + str(attempt), compact) as event:
                    spec = expand_compact(compact, domain, text)
                    event["output"] = spec
                with trace.stage("validate_" + str(attempt), spec) as event:
                    errors = validate(spec, domain)
                    event["output"] = {"errors": errors}
                    if errors:
                        raise IntentGenerationError("; ".join(errors[:8]))
                trace.emit("result", "completed", output=spec)
                return spec
            except (ValueError, KeyError, TypeError, IntentGenerationError) as exc:
                if attempt:
                    raise IntentGenerationError("模型输出两次校验失败: " + str(exc)) from exc
                with trace.stage("repair", {"error": str(exc)}) as event:
                    prompt += "\n校验错误=" + str(exc) + "\n请修正。"
                    event["output"] = prompt

    @staticmethod
    def _parse_and_validate(raw, domain):
        try:
            spec = json.loads(raw)
        except ValueError as exc:
            return None, [str(exc)]
        return spec, validate(spec, domain)

    @staticmethod
    def _parse_compact(raw, domain, text):
        try:
            spec = expand_compact(json.loads(raw), domain, text)
        except (ValueError, KeyError, TypeError) as exc:
            return None, [str(exc)]
        return spec, validate(spec, domain)
