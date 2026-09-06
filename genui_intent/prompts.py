import json
from typing import Dict


SYSTEM_PROMPT = """你是GenUI意图解析器。把用户原话转成RawIntentSpec v1.0，只输出一个JSON对象。
模型只表达语义，不选UI组件/模板，不生成Action ID、设备ID或实时数据。
规则：
1. tasks拆分独立动作；taskId依次为task_1...；依赖写dependsOn。
2. 动态key只能从给定候选选；无匹配用null及UNKNOWN/缺失项，禁止编造。
3. 用户原始对象名放entityMention。相对量保留RELATIVE+direction+degree，不换算数字。
4. 未明确要求载体/尺寸：surfaceType=AUTO, requestedSize=null。
5. 每个字段都必须输出；无值用null或[]。不输出解释/Markdown/额外字段。
6. 查看对象状态用GET，不是SEARCH；智能设备的entityType=DEVICE，天气信息的entityType=INFORMATION。
7. 仅当用户提供或任务必需时才输出parameter；无参数查询parameters=[]。仅有明确上下文才输出context；否则contexts=[]。
固定枚举：
intentType=QUERY|CONTROL|CREATE|EDIT|DELETE|NAVIGATE|COMMUNICATE|RECOMMEND|MONITOR|AUTOMATE|UNKNOWN
goalType=OBTAIN_INFORMATION|CHANGE_STATE|COMPLETE_TASK|CREATE_CONTENT|MAKE_DECISION|TRACK_PROGRESS|OBTAIN_EMOTIONAL_SUPPORT|REDUCE_EFFORT|OTHER|UNKNOWN
entityType=DEVICE|INFORMATION|CONTENT|PERSON|EVENT|TASK|MEDIA|LOCATION|SERVICE|SETTING|MESSAGE|REMINDER|AUTOMATION|OTHER|UNKNOWN
operationType=GET|SET|INCREASE|DECREASE|TOGGLE|START|STOP|OPEN|CLOSE|CREATE|UPDATE|DELETE|SEARCH|SELECT|COMPARE|SHARE|SEND|SCHEDULE|CANCEL|CONFIRM|OTHER|UNKNOWN
valueType=STRING|NUMBER|BOOLEAN|ENUM|DATE|TIME|DATETIME|DURATION|LOCATION|REFERENCE|NONE|UNKNOWN
expressionType=EXACT|RELATIVE|MINIMUM|MAXIMUM|RANGE|DEFAULT|PREFERENCE|UNSPECIFIED|UNKNOWN
referenceType=EXPLICIT|PRONOUN|PREVIOUS|CURRENT|SELF|UNSPECIFIED|UNKNOWN
contextType=LOCATION|TIME|EVENT|ACTIVITY|USER|DEVICE|APPLICATION|CONVERSATION|OTHER
temporalType=NOW|ABSOLUTE|RELATIVE|RANGE|RECURRING|IMMINENT|UNSPECIFIED|UNKNOWN
valueSource=USER|CONTEXT|DEFAULT|INFERRED
surfaceType=AUTO|CARD|PAGE|FORM|DIALOG|NOTIFICATION|WIDGET|OVERLAY
interactionMode=VIEW|CONTROL|EDIT|SELECT|CONFIRM|AUTO; density=AUTO|COMPACT|NORMAL|DETAILED
status=RESOLVED|NEEDS_CONTEXT|NEEDS_CLARIFICATION|UNSUPPORTED; certainty=HIGH|MEDIUM|LOW
missingFields=DOMAIN|ENTITY|OPERATION|PROPERTY|VALUE|TIME|LOCATION|RECIPIENT|CONTENT|CONDITION"""


SKELETON = {
    "version": "1.0", "intentType": "...", "domain": "...", "goalType": "...",
    "tasks": [{
        "taskId": "task_1",
        "entity": {"entityType": "...", "entityCategoryKey": None, "entityMention": None, "referenceType": "..."},
        "operation": {"operationType": "...", "propertyKey": None},
        "parameters": [{"parameterKey": "...", "value": None, "valueType": "...", "expressionType": "...", "direction": None, "degree": None, "unit": None, "valueSource": "..."}],
        "contexts": [{"contextType": "...", "value": None, "temporalType": "...", "valueSource": "..."}],
        "dependsOn": [],
    }],
    "presentation": {"surfaceType": "AUTO", "interactionMode": "AUTO", "density": "AUTO", "requestedSize": None},
    "resolution": {"status": "RESOLVED", "certainty": "HIGH", "missingFields": []},
}


def build_user_prompt(text: str, domain: str, registry: Dict[str, object]) -> str:
    compact_registry = json.dumps(registry, ensure_ascii=False, separators=(",", ":"))
    skeleton = json.dumps(SKELETON, ensure_ascii=False, separators=(",", ":"))
    return f"domain固定为{domain}\n候选={compact_registry}\n结构={skeleton}\n用户原话={json.dumps(text, ensure_ascii=False)}"


def build_repair_prompt(original: str, invalid_output: str, errors, domain: str, registry: Dict[str, object]) -> str:
    return (
        "修正以下JSON，只输出修正后的完整JSON。不得改变用户语义。\n"
        f"domain固定为{domain}\n"
        f"候选={json.dumps(registry, ensure_ascii=False, separators=(',', ':'))}\n"
        f"用户原话={json.dumps(original, ensure_ascii=False)}\n"
        f"错误={json.dumps(errors[:8], ensure_ascii=False)}\n"
        f"原输出={invalid_output}"
    )
