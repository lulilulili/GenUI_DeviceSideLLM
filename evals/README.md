# 端侧模型评测

`intent_cases.jsonl` 使用“部分语义断言”，只检查决定后续系统行为的关键字段，不比较整段 JSON 文本，也不限制开放文本的措辞。

## 建议运行顺序

先确认服务和模型：

```powershell
ollama list
ollama run qwen2.5:3b "你好"
```

先跑 5 条冒烟测试：

```powershell
python evals/run_ollama_eval.py --limit 5
```

按领域或难度运行：

```powershell
python evals/run_ollama_eval.py --tag smart_home
python evals/run_ollama_eval.py --tag adversarial
python evals/run_ollama_eval.py --tag multi_task
```

运行完整基线：

```powershell
python evals/run_ollama_eval.py --model qwen2.5:3b --output evals/results/qwen2.5-3b-baseline.jsonl
```

单条复现：

```powershell
python evals/run_ollama_eval.py --case-id sh_relative_01
```

只重跑上一轮失败项：

```powershell
python evals/run_ollama_eval.py --rerun-failures evals/results/full-pass-1.jsonl
```

控制台报告包含：整例全对率、关键字段得分、Pipeline 失败率、P50/P95 延迟及分领域得分。JSONL 结果保留每项断言、完整模型结果和错误，适合后续比较 Prompt 或模型版本。

## 数据覆盖

- 五个首发领域及各自实体、属性、操作；
- 精确值、相对值、最大/最小、偏好表达；
- 时间、地点、活动和事件上下文；
- 多任务、依赖和指代；
- 省略、歧义、需要上下文和缺失参数；
- 明确 UI 载体与尺寸；
- Prompt 注入、要求编造数据等对抗输入；
- 口语、错别字、中英混合和冗长表达。

首轮重点不是追求高分，而是定位失败来自路由、生成、Schema、动态候选还是协议本身。修改 Prompt 后应保留旧结果文件，再用同一模型参数重跑进行对照。
