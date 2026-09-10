# 冻结测试集（frozen set）

这是整个训练流程的"考卷"。规矩只有三条，都来自实习生 A2UI 工作里被验证过的教训：

1. **考卷永不进课本**：这里的任何条目（含其改写变体）绝不允许出现在训练数据里。
   实习生的数据里 train/test 目标答案哈希交集 196 条，导致离线分数带记忆水分——
   用 `tools/check_leakage.py` 在每次组装训练集后自动检查。
2. **考的是纯自然语言端到端**：实习生结构化输入下可渲染率 84.4%，换成纯自然
   语言页面实测严格通过只有 2/20。所以本集的 `prompt` 一律是用户会说的原话，
   不允许喂任何结构化上下文。
3. **写好后冻结**：条目一旦定稿只许追加新条目（升版本），不许修改旧条目——
   否则前后两次评测分数不可比。

## 文件

- `frozen_set_template.jsonl` — 条目格式模板，16 条示例（每桶 2 条），
  `"status": "sample"` 表示仅演示格式，正式集要人工重写并把 status 去掉。
- 正式集命名 `frozen_set_v1.jsonl`，由人工编写 + 大模型扩写后**逐条人审**产生。

## 八个分桶（每桶 40~60 条，总量 300~500）

| bucket | 考什么 | 例子 |
|---|---|---|
| `single_domain_explicit` | 单域、字段点名 | "显示手机电量和 Wi-Fi 开关" |
| `domain_only` | 只提领域不提字段（考默认字段选择） | "来个天气卡片" |
| `paraphrase_longtail` | 近义词/口语/错别字/长句 | "手机还剩多少格电啊" |
| `negation_correction` | 否定与纠正 | "不要湿度，就看温度" |
| `cross_domain` | 跨域混合 | "天气和今天的日程放一起" |
| `unsupported` | 注册表覆盖不了的请求（考不乱绑） | "显示我的股票收益" |
| `multi_action` | 多个操作请求（考 ACTION 上限与取舍） | "开灯开空调开窗帘" |
| `out_of_field` | 领域内但字段超纲 | "显示电池温度" |

## 条目格式

```json
{
  "id": "wx-001",
  "bucket": "single_domain_explicit",
  "prompt": "用户会说的原话",
  "expected": {
    "reject": false,
    "domain": "WEATHER",
    "morphemes": [
      {"keys": ["weather.temperature"], "role": "PRIMARY"},
      {"keys": ["weather.humidity"], "role": "SECONDARY", "optional": true}
    ],
    "max_actions": 0
  },
  "notes": "给人审者看的说明"
}
```

- `expected.morphemes[].keys`：可接受的注册表键列表（同义键都列上，命中任一算对）。
  **必须是 `genui_v2/capability.py` 里真实存在的键**——评测脚本会校验。
- `optional: true`：模型给了算对（计精确率），不给不扣分（不计召回）。
- `role`：期望的信息角色；只对命中的键检查。
- `reject: true`（unsupported 桶）：期望管线**不产生任何 EXACT/ALIAS 绑定**
  （安全底线是"不绑错"，而不是"模型说不"）。此时 `morphemes` 留空。
- `max_actions`：期望的 ACTION 角色数上限，用于测"动作幻觉"
  （实习生数据：无操作样本上 3B 幻觉率 32.9% vs 遗漏率 0.2%，小模型天然爱加按钮）。

## 运行

```bash
python evals/run_frozen_eval.py --dataset evals/frozen/frozen_set_template.jsonl --provider mock
python evals/run_frozen_eval.py --dataset evals/frozen/frozen_set_v1.jsonl --model qwen2.5:3b
```
