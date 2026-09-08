"""Declarative on-device capability registry.

This is the answer to "系统 API 要以什么形式注册获取":

Every data/action capability is a *declarative manifest entry* — the same shape
an app or system service would ship at install time (HarmonyOS InsightIntent /
CreateMyCard provider.json style). The framework aggregates the manifests into
this index; the pipeline resolves the model's free-form semantic key against it
by exact key -> alias -> token overlap. The model NEVER sees or emits real API
names, deeplinks or permissions; an unresolved key degrades to static text.

Entry fields:
  key         canonical semantic key (stable, versioned by the provider)
  aliases     chinese/english words used for routing and fuzzy resolution
  path        data-model JSON pointer the runtime writes results to
  valueType   declared shape; a resolved morpheme inherits it (overrides model)
  sample      preview/first-frame value (production: cached last value)
  unit        display unit
  action      optional whitelisted action descriptor (deeplink / intent id)
  permission  permission gate checked by the host before binding
  freshness   PULL (query on show) or PUSH (subscription)
"""

PROVIDERS = [
    {"providerId": "system.battery", "domain": "DEVICE",
     "permission": None, "entries": [
        {"key": "phone.battery.level", "aliases": ["电量", "电池", "battery", "剩多少电"],
         "path": "/device/battery/level", "valueType": "PERCENTAGE", "sample": 67, "unit": "%",
         "freshness": "PUSH"},
        {"key": "phone.battery.charging", "aliases": ["充电", "charging", "充上电"],
         "path": "/device/battery/charging", "valueType": "ENUM", "sample": "未在充电", "freshness": "PUSH"},
        {"key": "phone.battery.remain_time", "aliases": ["剩余时间", "可用时长", "remain"],
         "path": "/device/battery/remainTime", "valueType": "STRING", "sample": "约 9 小时", "freshness": "PULL"},
     ]},
    {"providerId": "system.connectivity", "domain": "DEVICE",
     "permission": "ohos.permission.GET_NETWORK_INFO", "entries": [
        {"key": "network.status", "aliases": ["网络", "网络状态", "network", "没网"],
         "path": "/device/network/status", "valueType": "ENUM", "sample": "已连接", "freshness": "PUSH"},
        {"key": "wifi.power", "aliases": ["wifi", "Wi-Fi", "无线"],
         "path": "/device/wifi/power", "valueType": "BOOLEAN", "sample": True,
         "action": {"call": "toggleAbility", "args": {"ability": "wifi"}}, "freshness": "PUSH"},
        {"key": "bluetooth.power", "aliases": ["蓝牙", "bluetooth"],
         "path": "/device/bluetooth/power", "valueType": "BOOLEAN", "sample": True,
         "action": {"call": "toggleAbility", "args": {"ability": "bluetooth"}}, "freshness": "PUSH"},
        {"key": "headphones.battery.level", "aliases": ["耳机电量", "耳机", "headphone"],
         "path": "/device/headphones/battery", "valueType": "PERCENTAGE", "sample": 82, "unit": "%",
         "freshness": "PULL"},
        {"key": "headphones.connection.status", "aliases": ["耳机连接", "连接状态", "connection"],
         "path": "/device/headphones/connection", "valueType": "ENUM", "sample": "已连接", "freshness": "PUSH"},
     ]},
    {"providerId": "system.display", "domain": "DEVICE", "permission": None, "entries": [
        {"key": "display.brightness", "aliases": ["屏幕亮度", "亮度", "brightness", "屏幕"],
         "path": "/device/display/brightness", "valueType": "PERCENTAGE", "sample": 60, "unit": "%",
         "action": {"call": "setSystemSetting", "args": {"setting": "brightness"}}, "freshness": "PULL"},
     ]},
    {"providerId": "app.weather", "domain": "WEATHER",
     "permission": "ohos.permission.LOCATION", "entries": [
        {"key": "weather.temperature", "aliases": ["温度", "气温", "temperature", "天气"],
         "path": "/weather/current/temperature", "valueType": "NUMBER", "sample": 26, "unit": "°",
         "action": {"call": "clickToDeeplink", "args": {"bundleName": "com.huawei.hmsapp.totemweather"}},
         "freshness": "PULL"},
        {"key": "weather.condition", "aliases": ["天气现象", "condition", "晴", "下雨吗"],
         "path": "/weather/current/condition", "valueType": "ENUM", "sample": "晴", "freshness": "PULL"},
        {"key": "weather.city", "aliases": ["城市", "city", "位置"],
         "path": "/weather/location/city", "valueType": "STRING", "sample": "北京", "freshness": "PULL"},
        {"key": "weather.humidity", "aliases": ["湿度", "humidity"],
         "path": "/weather/current/humidity", "valueType": "PERCENTAGE", "sample": 48, "unit": "%",
         "freshness": "PULL"},
        {"key": "weather.air_quality", "aliases": ["空气质量", "空气", "aqi", "air"],
         "path": "/weather/current/airQuality", "valueType": "ENUM", "sample": "优", "freshness": "PULL"},
        {"key": "weather.precipitation.probability", "aliases": ["降水", "下雨", "雨", "伞", "precipitation"],
         "path": "/weather/current/rainProbability", "valueType": "PERCENTAGE", "sample": 20, "unit": "%",
         "freshness": "PULL"},
        {"key": "weather.forecast.daily", "aliases": ["预报", "未来", "七天", "forecast"],
         "path": "/weather/forecast/daily", "valueType": "LIST",
         "sample": [{"title": "周一 晴 26°/16°"}, {"title": "周二 多云 24°/15°"}, {"title": "周三 小雨 21°/14°"}],
         "freshness": "PULL"},
     ]},
    {"providerId": "app.smart_home", "domain": "SMART_HOME",
     "permission": "ohos.permission.SMART_HOME", "entries": [
        {"key": "light.power", "aliases": ["灯", "台灯", "灯光", "light"],
         "path": "/home/light/power", "valueType": "BOOLEAN", "sample": True,
         "action": {"call": "deviceCommand", "args": {"device": "light", "command": "setPower"}},
         "freshness": "PUSH"},
        {"key": "light.brightness", "aliases": ["灯亮度", "调暗", "调亮", "brightness"],
         "path": "/home/light/brightness", "valueType": "PERCENTAGE", "sample": 40, "unit": "%",
         "action": {"call": "deviceCommand", "args": {"device": "light", "command": "setBrightness"}},
         "freshness": "PULL"},
        {"key": "ac.temperature", "aliases": ["空调", "空调温度", "度", "air_conditioner", "ac"],
         "path": "/home/ac/temperature", "valueType": "NUMBER", "sample": 24, "unit": "°C",
         "action": {"call": "deviceCommand", "args": {"device": "ac", "command": "setTemperature"}},
         "freshness": "PULL"},
        {"key": "ac.power", "aliases": ["空调开关", "开空调", "关空调"],
         "path": "/home/ac/power", "valueType": "BOOLEAN", "sample": False,
         "action": {"call": "deviceCommand", "args": {"device": "ac", "command": "setPower"}},
         "freshness": "PUSH"},
        {"key": "curtain.position", "aliases": ["窗帘", "curtain"],
         "path": "/home/curtain/position", "valueType": "PERCENTAGE", "sample": 100, "unit": "%",
         "action": {"call": "deviceCommand", "args": {"device": "curtain", "command": "setPosition"}},
         "freshness": "PULL"},
     ]},
    {"providerId": "app.tasks", "domain": "TASK",
     "permission": "ohos.permission.READ_CALENDAR", "entries": [
        {"key": "task.list", "aliases": ["待办", "任务", "todo", "task", "清单"],
         "path": "/task/list", "valueType": "LIST",
         "sample": [{"title": "交周报", "state": "ACTIVE"}, {"title": "预约体检", "state": "DEFAULT"},
                    {"title": "买牛奶", "state": "DEFAULT"}],
         "action": {"call": "clickToDeeplink", "args": {"bundleName": "com.huawei.hmos.notepad"}},
         "freshness": "PULL"},
        {"key": "reminder.create", "aliases": ["提醒", "喊我", "reminder", "闹钟"],
         "path": "/task/reminder/next", "valueType": "STRING", "sample": "明早 8:00 交报告",
         "action": {"call": "createReminder", "args": {}}, "freshness": "PULL"},
        {"key": "timer.duration", "aliases": ["计时", "计时器", "timer", "倒计时"],
         "path": "/task/timer/remaining", "valueType": "DURATION", "sample": "25:00",
         "action": {"call": "startTimer", "args": {}}, "freshness": "PUSH"},
        {"key": "calendar.next_event", "aliases": ["日程", "日历", "会议", "schedule", "calendar"],
         "path": "/task/calendar/next", "valueType": "STRING", "sample": "14:30 项目评审会 · 3F 会议室",
         "action": {"call": "clickToDeeplink", "args": {"bundleName": "com.huawei.hmos.calendar"}},
         "freshness": "PULL"},
        {"key": "goal.progress", "aliases": ["目标", "进度", "goal", "步数"],
         "path": "/task/goal/progress", "valueType": "PERCENTAGE", "sample": 72, "unit": "%",
         "freshness": "PULL"},
     ]},
    {"providerId": "module.content", "domain": "CONTENT", "permission": None, "entries": [
        {"key": "content.encouragement", "aliases": ["打气", "鼓励", "加油", "encourage"],
         "path": None, "valueType": "STRING", "sample": "别紧张，你复习过的都会考到，稳住就赢了！",
         "generator": True, "freshness": "PULL"},
        {"key": "content.greeting", "aliases": ["祝福", "greeting", "生日"],
         "path": None, "valueType": "STRING", "sample": "生日快乐，愿新的一岁万事顺意！",
         "generator": True, "freshness": "PULL"},
        {"key": "content.summary", "aliases": ["总结", "summary", "摘要"],
         "path": None, "valueType": "STRING", "sample": "（摘要将由内容模块生成）",
         "generator": True, "freshness": "PULL"},
        {"key": "content.copy", "aliases": ["文案", "copy", "写一句", "通知"],
         "path": None, "valueType": "STRING", "sample": "（文案将由内容模块生成）",
         "generator": True, "freshness": "PULL"},
     ]},
]


def _index():
    by_key, alias_rows = {}, []
    for provider in PROVIDERS:
        for entry in provider["entries"]:
            record = dict(entry)
            record["providerId"] = provider["providerId"]
            record["domain"] = provider["domain"]
            record["permission"] = entry.get("permission", provider.get("permission"))
            by_key[entry["key"]] = record
            for alias in [entry["key"]] + list(entry.get("aliases", [])):
                alias_rows.append((alias.lower(), record))
    return by_key, alias_rows


BY_KEY, ALIAS_ROWS = _index()
DOMAINS = sorted({provider["domain"] for provider in PROVIDERS})


def domain_keywords():
    """Router keywords derived from the same manifests — one source of truth."""
    keywords = {}
    for provider in PROVIDERS:
        bucket = keywords.setdefault(provider["domain"], set())
        for entry in provider["entries"]:
            bucket.update(alias for alias in entry.get("aliases", []) if not alias.isascii())
    keywords["CONTENT"].update({"写", "创作", "文一段"})
    return {domain: tuple(sorted(words)) for domain, words in keywords.items()}


def keys_for_domain(domain):
    return tuple(sorted(entry["key"] for entry in BY_KEY.values() if entry["domain"] == domain))


def _tokens(text):
    out, word = set(), []
    for char in (text or "").lower():
        if char.isalnum():
            word.append(char)
        else:
            if word:
                out.add("".join(word))
            word = []
    if word:
        out.add("".join(word))
    return out


def resolve(semantic_key, label=None, domain=None):
    """key -> alias substring -> token overlap. Returns (entry|None, how)."""
    key = (semantic_key or "").strip().lower()
    if key in BY_KEY:
        return BY_KEY[key], "EXACT"
    haystack = key + " " + (label or "").lower()
    candidates = [row for row in ALIAS_ROWS if domain in (None, row[1]["domain"])]
    for alias, record in candidates:
        if alias and alias in haystack:
            return record, "ALIAS"
    query_tokens = _tokens(haystack)
    best, best_score = None, 0
    for record in {id(row[1]): row[1] for row in candidates}.values():
        entry_tokens = _tokens(record["key"] + " " + " ".join(record.get("aliases", [])))
        score = len(query_tokens & entry_tokens)
        if score > best_score:
            best, best_score = record, score
    if best is not None and best_score >= 1:
        return best, "TOKENS"
    return None, "MISS"


def bind(spec, domain=None):
    """Attach real bindings/samples to morphemes; never invent data.

    Resolved   -> path/action/permission/sample from the manifest, and the
                  manifest valueType overrides the model's guess.
    Generator  -> handed to the content module (sample stands in for demo).
    Unresolved -> static text fallback, flagged UNBOUND for the UI to surface.
    """
    report = []
    for item in spec["morphemes"]:
        entry, how = resolve(item["semanticKey"], item["label"], domain)
        cross_domain = False
        if entry is None and domain is not None:
            # 跨域营救：路由领域内 MISS 时放开领域约束再试一次
            entry, how = resolve(item["semanticKey"], item["label"], None)
            cross_domain = entry is not None
        binding = {"resolution": how}
        if cross_domain:
            binding["crossDomain"] = True
        if entry is not None:
            binding.update({"key": entry["key"], "providerId": entry["providerId"],
                            "path": entry.get("path"), "permission": entry.get("permission"),
                            "freshness": entry.get("freshness", "PULL"),
                            "generator": bool(entry.get("generator"))})
            if entry.get("action"):
                binding["action"] = entry["action"]
            item["valueType"] = entry["valueType"]
            item["binding"] = binding
            item["content"] = _content_from_entry(entry)
        else:
            item["binding"] = {"resolution": "MISS"}
            item["valueType"] = "STRING" if item["valueType"] in ("UNKNOWN",) else item["valueType"]
            item["content"] = {"text": item["label"] or item["semanticKey"], "unbound": True}
        report.append({"id": item["id"], "q": item["semanticKey"], "resolution": how,
                       "key": entry["key"] if entry else None,
                       "provider": entry["providerId"] if entry else None})
    return spec, report


def _content_from_entry(entry):
    sample, value_type, unit = entry.get("sample"), entry["valueType"], entry.get("unit", "")
    if value_type == "PERCENTAGE":
        return {"value": sample, "min": 0, "max": 100, "unit": unit or "%", "showValue": True,
                "binding": entry.get("path")}
    if value_type == "NUMBER":
        return {"value": sample, "unit": unit, "binding": entry.get("path")}
    if value_type == "BOOLEAN":
        return {"checked": bool(sample), "disabled": False, "binding": entry.get("path")}
    if value_type == "ENUM":
        return {"text": str(sample), "state": "SUCCESS", "binding": entry.get("path")}
    if value_type == "LIST":
        items = sample if isinstance(sample, list) else []
        return {"items": [dict(item) for item in items], "binding": entry.get("path")}
    if value_type == "DURATION":
        return {"value": sample, "unit": "", "binding": entry.get("path")}
    return {"text": str(sample), "binding": entry.get("path")}
