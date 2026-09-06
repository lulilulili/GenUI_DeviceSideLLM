from typing import Dict, List


REGISTRIES: Dict[str, Dict[str, object]] = {
    "SMART_HOME": {
        "guidance": "灯/空调/窗帘均为DEVICE。查看状态=GET；开关=SET power+target_state；调数值=SET/INCREASE/DECREASE对应属性。",
        "entities": ["light", "air_conditioner", "curtain", "switch", "thermostat"],
        "properties": {
            "light": ["power", "brightness", "color_temperature"],
            "air_conditioner": ["power", "temperature", "mode", "fan_speed"],
            "curtain": ["position"], "switch": ["power"],
            "thermostat": ["temperature", "mode"],
        },
        "parameters": ["target_value", "target_state", "mode"],
    },
    "WEATHER": {
        "guidance": "天气均为INFORMATION且只查询GET。下雨概率=precipitation/probability；多日天气=forecast/daily_forecast。不得生成天气数值。",
        "entities": ["weather", "forecast", "air_quality", "precipitation"],
        "properties": {
            "weather": ["condition", "temperature", "humidity"],
            "forecast": ["daily_forecast", "hourly_forecast"],
            "air_quality": ["aqi"], "precipitation": ["probability"],
        },
        "parameters": ["location", "date_range"],
    },
    "DEVICE": {
        "guidance": "手机硬件均为DEVICE。查看=GET；开关设置=SET；屏幕明暗=display/brightness；剩余电量=battery/level。",
        "entities": ["phone", "battery", "network", "bluetooth", "headphones", "display"],
        "properties": {
            "phone": ["status"], "battery": ["level", "charging"],
            "network": ["connectivity", "wifi"], "bluetooth": ["power", "connection"],
            "headphones": ["battery", "connection"], "display": ["brightness"],
        },
        "parameters": ["target_value", "target_state"],
    },
    "CONTENT": {
        "guidance": "生成文案=CONTENT+CREATE/content。鼓励=encouragement_message；祝福=greeting；总结=summary；创意=idea。不要生成最终文案。",
        "entities": ["encouragement_message", "copy", "summary", "greeting", "idea"],
        "properties": {key: ["content"] for key in ["encouragement_message", "copy", "summary", "greeting", "idea"]},
        "parameters": ["topic", "tone", "recipient", "length", "source_text"],
        "parameterEnums": {
            "tone": ["NEUTRAL", "ENCOURAGING", "FRIENDLY", "FORMAL", "URGENT", "CALM", "CELEBRATORY", "SYMPATHETIC", "HUMOROUS", "OTHER", "UNKNOWN"],
            "recipient": ["SELF", "CONTACT", "GROUP", "PUBLIC", "OTHER", "UNKNOWN"],
        },
    },
    "TASK": {
        "guidance": "待办=task，提醒=reminder，计时器=timer，进度=goal。创建用CREATE，周期安排可用SCHEDULE，查询用GET。",
        "entities": ["task", "reminder", "timer", "goal", "task_list"],
        "properties": {
            "task": ["title", "status", "due_time"], "reminder": ["content", "trigger_time"],
            "timer": ["duration", "status"], "goal": ["progress", "target"],
            "task_list": ["items"],
        },
        "parameters": ["content", "time", "duration", "priority", "target_value"],
    },
}

DOMAINS: List[str] = list(REGISTRIES)
