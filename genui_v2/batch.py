"""Training dataset helpers used by the workbench batch screener."""
import json


def parse_indices(text, total, limit=100):
    """Parse 1-based indexes such as ``1,3,8-10`` in stable order."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("请输入序号，例如 1,3,5-10")
    values = []
    seen = set()
    for token in text.replace("，", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            parts = token.split("-")
            if len(parts) != 2 or not all(part.strip().isdigit() for part in parts):
                raise ValueError("序号范围格式错误：" + token)
            begin, end = (int(part.strip()) for part in parts)
            if begin > end:
                begin, end = end, begin
            candidates = range(begin, end + 1)
        elif token.isdigit():
            candidates = (int(token),)
        else:
            raise ValueError("序号格式错误：" + token)
        for index in candidates:
            if not 1 <= index <= total:
                raise ValueError(f"序号超出范围：{index}（数据集共 {total} 条）")
            if index not in seen:
                seen.add(index)
                values.append(index)
                if len(values) > limit:
                    raise ValueError(f"单次最多筛查 {limit} 条")
    return values


def load_jsonl(path):
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"数据集第 {line_number} 行不是合法 JSON：{exc}") from exc
    return rows


def assistant_json(row):
    messages = row.get("messages")
    if not isinstance(messages, list):
        raise TypeError("样本缺少 messages")
    for message in reversed(messages):
        if message.get("role") == "assistant":
            value = json.loads(message.get("content", ""))
            if not isinstance(value, dict):
                raise ValueError("assistant 输出必须是 JSON object")
            return value
    raise ValueError("样本缺少 assistant JSON")


def prompt_from_row(row):
    messages = row.get("messages")
    if not isinstance(messages, list):
        raise TypeError("样本缺少 messages")
    for message in messages:
        if message.get("role") == "user":
            return str(message.get("content", ""))
    raise ValueError("样本缺少 user prompt")


def request_from_row(row):
    """Get the natural-language request from a production training prompt."""
    prompt = prompt_from_row(row)
    for marker in ("USER REQUEST:", "用户="):
        if marker in prompt:
            return prompt.rsplit(marker, 1)[1].strip().splitlines()[0].strip()
    return prompt.strip()


def domain_from_row(row):
    prompt = prompt_from_row(row)
    marker = "领域="
    if marker in prompt:
        return prompt.split(marker, 1)[1].splitlines()[0].strip() or None
    return None
