"""Domain routing driven by the capability manifests (one source of truth)."""
from .capability import DOMAINS, domain_keywords

KEYWORDS = domain_keywords()


def rule_route(text):
    lowered = text.lower()
    if any(word in lowered for word in ("write a", "greeting", "summary", "copywriting")):
        return "CONTENT"
    if "提醒" in text:
        return "TASK"
    scores = {domain: sum(word.lower() in lowered for word in words)
              for domain, words in KEYWORDS.items()}
    best = max(scores, key=lambda domain: scores[domain])
    winners = [domain for domain, score in scores.items() if score == scores[best] and score > 0]
    return winners[0] if len(winners) == 1 else None


def model_route(text, provider):
    system = "你是领域路由器。只输出一个枚举：" + "|".join(DOMAINS + ["UNKNOWN"])
    result = provider.complete(system, text, max_tokens=12, temperature=0.0, schema=None)
    result = result.strip().strip('`" \n').upper()
    return result if result in DOMAINS else None


def route(text, provider):
    return rule_route(text) or model_route(text, provider)
