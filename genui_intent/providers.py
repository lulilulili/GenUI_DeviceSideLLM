import json
import copy
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict

from .config import Settings


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "raw-intent.schema.json"
RAW_INTENT_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def schema_for_domain(domain: str, registry: Dict[str, object]) -> Dict[str, object]:
    """Tighten the base schema with runtime candidates before constrained decoding."""
    schema = copy.deepcopy(RAW_INTENT_SCHEMA)
    schema["properties"]["domain"] = {"const": domain}
    schema["$defs"]["entity"]["properties"]["entityCategoryKey"] = {
        "enum": list(registry.get("entities", [])) + [None]
    }
    properties = sorted({item for values in registry.get("properties", {}).values() for item in values})
    schema["$defs"]["operation"]["properties"]["propertyKey"] = {"enum": properties + [None]}
    schema["$defs"]["parameter"]["properties"]["parameterKey"] = {
        "enum": list(registry.get("parameters", []))
    }
    return schema


class ProviderError(RuntimeError):
    pass


class HttpProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _post(self, url: str, payload: Dict[str, object]) -> Dict[str, object]:
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = "Bearer " + self.settings.api_key
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError("端侧模型请求失败: " + str(exc)) from exc


class OllamaProvider(HttpProvider):
    def complete(self, system: str, user: str, max_tokens: int = 600, temperature: float = 0.0, schema=None) -> str:
        payload = {
            "model": self.settings.model, "stream": False, "format": schema or RAW_INTENT_SCHEMA,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if max_tokens <= 12:
            payload.pop("format")
        data = self._post(self.settings.base_url + "/api/chat", payload)
        self.last_usage = {"inputTokens": data.get("prompt_eval_count"), "outputTokens": data.get("eval_count"), "source": "provider", "loadMs": data.get("load_duration", 0) / 1e6, "prefillMs": data.get("prompt_eval_duration", 0) / 1e6, "decodeMs": data.get("eval_duration", 0) / 1e6}
        return str(data["message"]["content"])


class OpenAICompatibleProvider(HttpProvider):
    def complete(self, system: str, user: str, max_tokens: int = 600, temperature: float = 0.0, schema=None) -> str:
        payload = {
            "model": self.settings.model, "temperature": temperature, "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if max_tokens <= 12:
            payload.pop("response_format")
        elif self.settings.response_mode == "json_schema" and schema:
            payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "intent", "schema": schema}}
        elif self.settings.response_mode == "none":
            payload.pop("response_format")
        data = self._post(self.settings.base_url + "/chat/completions", payload)
        usage = data.get("usage") or {}
        self.last_usage = {"inputTokens": usage.get("prompt_tokens"), "outputTokens": usage.get("completion_tokens"), "source": "provider" if usage else "unavailable"}
        return str(data["choices"][0]["message"]["content"])


class MockProvider:
    def complete(self, system: str, user: str, max_tokens: int = 600, temperature: float = 0.0, schema=None) -> str:
        if max_tokens <= 12:
            return "CONTENT"
        if schema and set(schema.get("required", [])) == {"s", "z", "d", "t", "m"}:
            self.last_usage = {"inputTokens": 96, "outputTokens": 88, "source": "mock"}
            items = [
                {"k": "PROGRESS", "r": "PRIMARY", "l": "耳机电量", "q": "headphones.battery.level", "f": "PERCENTAGE"},
                {"k": "STATUS", "r": "SECONDARY", "l": "连接状态", "q": "headphones.connection.status", "f": "ENUM"},
                {"k": "SWITCH", "r": "PRIMARY_ACTION", "l": "蓝牙", "q": "bluetooth.power", "f": "BOOLEAN"}
            ]
            return json.dumps({
                "s": "CARD", "z": schema["properties"]["z"]["enum"][0], "d": "COMPACT", "t": "耳机状态",
                "m": items[:schema["properties"]["m"]["maxItems"]]
            }, ensure_ascii=False)
        if schema and "entity" in schema.get("$defs", {}).get("task", {}).get("properties", {}):
            return json.dumps({
                "tasks": [{"entity": "encouragement_message", "mention": None, "operation": "CREATE",
                           "property": "content", "params": {"recipient": "SELF", "topic": "exam", "tone": "ENCOURAGING"},
                           "context": {"event": "exam", "temporal": "IMMINENT"}, "dependsOn": []}],
            }, ensure_ascii=False)
        return json.dumps({
            "version": "1.0", "intentType": "CREATE", "domain": "CONTENT",
            "goalType": "OBTAIN_EMOTIONAL_SUPPORT", "tasks": [{
                "taskId": "task_1",
                "entity": {"entityType": "CONTENT", "entityCategoryKey": "encouragement_message", "entityMention": None, "referenceType": "UNSPECIFIED"},
                "operation": {"operationType": "CREATE", "propertyKey": "content"},
                "parameters": [
                    {"parameterKey": "recipient", "value": "SELF", "valueType": "ENUM", "expressionType": "EXACT", "direction": None, "degree": None, "unit": None, "valueSource": "INFERRED"},
                    {"parameterKey": "topic", "value": "exam", "valueType": "STRING", "expressionType": "EXACT", "direction": None, "degree": None, "unit": None, "valueSource": "USER"},
                    {"parameterKey": "tone", "value": "ENCOURAGING", "valueType": "ENUM", "expressionType": "EXACT", "direction": None, "degree": None, "unit": None, "valueSource": "INFERRED"}],
                "contexts": [{"contextType": "EVENT", "value": "exam", "temporalType": "IMMINENT", "valueSource": "USER"}], "dependsOn": []}],
            "presentation": {"surfaceType": "AUTO", "interactionMode": "VIEW", "density": "AUTO", "requestedSize": None},
            "resolution": {"status": "RESOLVED", "certainty": "HIGH", "missingFields": []},
        }, ensure_ascii=False)


def create_provider(settings: Settings):
    if settings.provider == "ollama":
        return OllamaProvider(settings)
    if settings.provider == "openai_compatible":
        return OpenAICompatibleProvider(settings)
    if settings.provider == "mock":
        return MockProvider()
    raise ValueError("未知 provider: " + settings.provider)
