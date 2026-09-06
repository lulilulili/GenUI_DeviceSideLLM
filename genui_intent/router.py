import json
from typing import Optional

from .registries import DOMAINS


KEYWORDS = {
    "SMART_HOME": ("灯", "空调", "窗帘", "恒温", "智能家居"),
    "WEATHER": ("天气", "下雨", "温度", "湿度", "空气质量", "预报"),
    "DEVICE": ("电量", "电池", "多少电", "充上电", "充电", "蓝牙", "耳机", "网络", "Wi-Fi", "wifi", "屏幕", "手机亮度"),
    "CONTENT": ("写", "文案", "总结", "鼓励", "加油", "祝福", "创作", "创意", "greeting"),
    "TASK": ("提醒", "待办", "计时", "任务", "目标", "闹钟", "标记为", "marked as"),
}


def rule_route(text: str) -> Optional[str]:
    lowered = text.lower()
    if any(word in lowered for word in ("write a", "greeting", "summary", "copywriting")):
        return "CONTENT"
    if "提醒" in text and any(word in text for word in ("如果", "的话", "后", "每天", "点")):
        return "TASK"
    if "如果" in text and any(word in text for word in ("灯", "空调", "窗帘")):
        return "SMART_HOME"
    scores = {domain: sum(word in text for word in words) for domain, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    winners = [domain for domain, score in scores.items() if score == scores[best] and score > 0]
    return winners[0] if len(winners) == 1 else None


def route_with_model(text: str, provider) -> str:
    system = "你是领域路由器。只输出一个枚举：" + "|".join(DOMAINS + ["UNKNOWN"])
    result = provider.complete(system, text, max_tokens=12, temperature=0.0, schema=None).strip().upper()
    result = result.strip('`" \n')
    return result if result in DOMAINS else "UNKNOWN"


def route(text: str, provider) -> str:
    return rule_route(text) or route_with_model(text, provider)
