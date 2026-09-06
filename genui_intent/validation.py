from typing import Dict, List, Set

from .registries import REGISTRIES


ENUMS: Dict[str, Set[str]] = {
    "intentType": set("QUERY CONTROL CREATE EDIT DELETE NAVIGATE COMMUNICATE RECOMMEND MONITOR AUTOMATE UNKNOWN".split()),
    "goalType": set("OBTAIN_INFORMATION CHANGE_STATE COMPLETE_TASK CREATE_CONTENT MAKE_DECISION TRACK_PROGRESS OBTAIN_EMOTIONAL_SUPPORT REDUCE_EFFORT OTHER UNKNOWN".split()),
    "entityType": set("DEVICE INFORMATION CONTENT PERSON EVENT TASK MEDIA LOCATION SERVICE SETTING MESSAGE REMINDER AUTOMATION OTHER UNKNOWN".split()),
    "operationType": set("GET SET INCREASE DECREASE TOGGLE START STOP OPEN CLOSE CREATE UPDATE DELETE SEARCH SELECT COMPARE SHARE SEND SCHEDULE CANCEL CONFIRM OTHER UNKNOWN".split()),
    "referenceType": set("EXPLICIT PRONOUN PREVIOUS CURRENT SELF UNSPECIFIED UNKNOWN".split()),
    "valueType": set("STRING NUMBER BOOLEAN ENUM DATE TIME DATETIME DURATION LOCATION REFERENCE NONE UNKNOWN".split()),
    "expressionType": set("EXACT RELATIVE MINIMUM MAXIMUM RANGE DEFAULT PREFERENCE UNSPECIFIED UNKNOWN".split()),
    "direction": {"INCREASE", "DECREASE"},
    "degree": {"SLIGHT", "NORMAL", "LARGE", "UNKNOWN"},
    "valueSource": {"USER", "CONTEXT", "DEFAULT", "INFERRED"},
    "contextType": set("LOCATION TIME EVENT ACTIVITY USER DEVICE APPLICATION CONVERSATION OTHER".split()),
    "temporalType": set("NOW ABSOLUTE RELATIVE RANGE RECURRING IMMINENT UNSPECIFIED UNKNOWN".split()),
    "surfaceType": set("AUTO CARD PAGE FORM DIALOG NOTIFICATION WIDGET OVERLAY".split()),
    "interactionMode": {"VIEW", "CONTROL", "EDIT", "SELECT", "CONFIRM", "AUTO"},
    "density": {"AUTO", "COMPACT", "NORMAL", "DETAILED"},
    "status": {"RESOLVED", "NEEDS_CONTEXT", "NEEDS_CLARIFICATION", "UNSUPPORTED"},
    "certainty": {"HIGH", "MEDIUM", "LOW"},
    "missingField": set("DOMAIN ENTITY OPERATION PROPERTY VALUE TIME LOCATION RECIPIENT CONTENT CONDITION".split()),
}

ROOT_KEYS = {"version", "intentType", "domain", "goalType", "tasks", "presentation", "resolution"}
TASK_KEYS = {"taskId", "entity", "operation", "parameters", "contexts", "dependsOn"}
ENTITY_KEYS = {"entityType", "entityCategoryKey", "entityMention", "referenceType"}
OP_KEYS = {"operationType", "propertyKey"}
PARAM_KEYS = {"parameterKey", "value", "valueType", "expressionType", "direction", "degree", "unit", "valueSource"}
CONTEXT_KEYS = {"contextType", "value", "temporalType", "valueSource"}


def _keys(value, expected, path, errors):
    if not isinstance(value, dict):
        errors.append(path + " 必须是对象")
        return False
    missing, extra = expected - set(value), set(value) - expected
    if missing:
        errors.append(path + " 缺字段: " + ",".join(sorted(missing)))
    if extra:
        errors.append(path + " 有额外字段: " + ",".join(sorted(extra)))
    return not missing


def _enum(value, name, path, errors, nullable=False):
    if nullable and value is None:
        return
    if value not in ENUMS[name]:
        errors.append(f"{path} 非法枚举: {value}")


def validate(spec: object, expected_domain: str = "") -> List[str]:
    errors: List[str] = []
    if not _keys(spec, ROOT_KEYS, "$", errors):
        return errors
    if spec.get("version") != "1.0":
        errors.append("$.version 必须为1.0")
    _enum(spec.get("intentType"), "intentType", "$.intentType", errors)
    _enum(spec.get("goalType"), "goalType", "$.goalType", errors)
    domain = spec.get("domain")
    if domain not in REGISTRIES:
        errors.append("$.domain 不在启用领域")
    if expected_domain and domain != expected_domain:
        errors.append(f"$.domain 应为 {expected_domain}")
    tasks = spec.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        errors.append("$.tasks 必须是非空数组")
        return errors
    task_ids, registry = set(), REGISTRIES.get(domain, {})
    for index, task in enumerate(tasks):
        path = f"$.tasks[{index}]"
        if not _keys(task, TASK_KEYS, path, errors):
            continue
        task_id = task.get("taskId")
        if task_id != f"task_{index + 1}" or task_id in task_ids:
            errors.append(path + ".taskId 必须连续且唯一")
        task_ids.add(task_id)
        entity = task.get("entity")
        if _keys(entity, ENTITY_KEYS, path + ".entity", errors):
            _enum(entity.get("entityType"), "entityType", path + ".entity.entityType", errors)
            category = entity.get("entityCategoryKey")
            if category is not None and category not in registry.get("entities", []):
                errors.append(path + ".entity.entityCategoryKey 不在领域候选")
            _enum(entity.get("referenceType"), "referenceType", path + ".entity.referenceType", errors)
        operation = task.get("operation")
        if _keys(operation, OP_KEYS, path + ".operation", errors):
            _enum(operation.get("operationType"), "operationType", path + ".operation.operationType", errors)
            category = entity.get("entityCategoryKey") if isinstance(entity, dict) else None
            prop = operation.get("propertyKey")
            allowed_props = registry.get("properties", {}).get(category, [])
            if prop is not None and prop not in allowed_props:
                errors.append(path + ".operation.propertyKey 不在实体候选")
        parameters = task.get("parameters")
        if not isinstance(parameters, list):
            errors.append(path + ".parameters 必须是数组")
        else:
            for pi, param in enumerate(parameters):
                pp = f"{path}.parameters[{pi}]"
                if not _keys(param, PARAM_KEYS, pp, errors):
                    continue
                if param.get("parameterKey") not in registry.get("parameters", []):
                    errors.append(pp + ".parameterKey 不在领域候选")
                for field in ("valueType", "expressionType", "valueSource"):
                    _enum(param.get(field), field, pp + "." + field, errors)
                _enum(param.get("direction"), "direction", pp + ".direction", errors, True)
                _enum(param.get("degree"), "degree", pp + ".degree", errors, True)
        contexts = task.get("contexts")
        if not isinstance(contexts, list):
            errors.append(path + ".contexts 必须是数组")
        else:
            for ci, context in enumerate(contexts):
                cp = f"{path}.contexts[{ci}]"
                if _keys(context, CONTEXT_KEYS, cp, errors):
                    for field in ("contextType", "temporalType", "valueSource"):
                        _enum(context.get(field), field, cp + "." + field, errors)
        if not isinstance(task.get("dependsOn"), list):
            errors.append(path + ".dependsOn 必须是数组")
    for task in tasks:
        for dependency in task.get("dependsOn", []):
            if dependency not in task_ids:
                errors.append("dependsOn 引用了不存在的任务: " + str(dependency))
    presentation = spec.get("presentation")
    if _keys(presentation, {"surfaceType", "interactionMode", "density", "requestedSize"}, "$.presentation", errors):
        for field in ("surfaceType", "interactionMode", "density"):
            _enum(presentation.get(field), field, "$.presentation." + field, errors)
    resolution = spec.get("resolution")
    if _keys(resolution, {"status", "certainty", "missingFields"}, "$.resolution", errors):
        _enum(resolution.get("status"), "status", "$.resolution.status", errors)
        _enum(resolution.get("certainty"), "certainty", "$.resolution.certainty", errors)
        missing = resolution.get("missingFields")
        if not isinstance(missing, list):
            errors.append("$.resolution.missingFields 必须是数组")
        else:
            for value in missing:
                _enum(value, "missingField", "$.resolution.missingFields", errors)
    return errors

