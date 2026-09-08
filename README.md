# GenUI 端侧 Morpheme 工作台

## v2（推荐入口）

`genui_v2/` 是按"模型只出语义、代码拥有一切 UI 决策"重构后的完整管线：
单次 LLM 调用产出 4 字段语素草稿 → 确定性组件推导 → 声明式能力注册表绑定（替代 mock 数据）
→ PDF 原型评分匹配 / 层级式自由布局 → 设计令牌保真渲染（HTML/A2UI/DSL）。
方案与成本分析见 `docs/V2-全端侧方案设计.md`。

```powershell
# v2 工作台（全链路可观测 + 卡片预览）
python -m genui_v2.workbench   # http://127.0.0.1:8766

# v2 测试
python -m unittest tests.test_v2_pipeline -v
```

旧版 `genui_intent/`（v1，双协议 + 规则后处理）完整保留用于对比，以下为 v1 原说明。

---

当前已增加完整的 Demo 生成链路：

```text
用户 Prompt → Qwen 生成精简 MorphemeDraft → 确定性补齐 → Mock 数据
→ 纯代码模板匹配/槽位填充 → RenderSpec v0.2 → HTML/CSS 或 A2UI → 浏览器实时预览
```

启动可视化工作台：

```powershell
python -m genui_intent.workbench
```

打开 `http://127.0.0.1:8765/`，在“运行流程”中选择 `Morpheme GenUI`。网页会逐阶段显示输入、输出、耗时、Token，并在 RenderSpec 完成后生成可交互预览。原始意图解析流程仍可切换使用。

布局引擎说明与 PDF 模板参考位于 `http://127.0.0.1:8765/layout`。当前提供 18 个 2×1 / 2×2 / 3×3 范式、留白补位、自由布局兜底、4 套风格 token，以及可插拔渲染器。

当前默认使用 `genui_intent/compact.py` 中的精简模型协议，再由代码扩展为 RawIntentSpec。CPU 实测与限制见 `docs/CPU评测与优化结果.md`；现有 63 条为开发回归集，成绩包含规则后处理贡献。

把用户提示词转换为受约束的 `RawIntentSpec v1.0`。模型只负责语义理解；实体绑定、能力执行、内容生成和 UI 布局留给后续确定性模块。

## 快速开始

环境要求：Python 3.9+，运行时无第三方依赖。

```powershell
# 离线演示（不调用模型）
python -m genui_intent "我马上要考试了，请帮我加油打气" --provider mock --pretty

# Ollama
$env:GENUI_PROVIDER="ollama"
$env:GENUI_MODEL="qwen2.5:3b"
python -m genui_intent "把台灯调暗一点" --pretty

# llama.cpp / 其他 OpenAI-compatible 本地服务
$env:GENUI_PROVIDER="openai_compatible"
$env:GENUI_BASE_URL="http://127.0.0.1:8080/v1"
$env:GENUI_MODEL="qwen2.5-3b-instruct"
python -m genui_intent "今天会下雨吗" --pretty
```

程序 stdout 只输出最终 JSON，诊断信息写入 stderr，便于直接接入管道。默认流程：

```text
用户提示词 → 轻量规则路由 → 必要时模型路由 → 注入单领域候选
→ 端侧模型生成 JSON → 语法/结构/枚举/候选校验 → 一次定向纠错 → RawIntentSpec
```

配置可通过命令行覆盖：`--provider`、`--model`、`--base-url`、`--api-key`、`--timeout`。Ollama 默认地址为 `http://127.0.0.1:11434`；OpenAI-compatible 默认地址为 `http://127.0.0.1:8080/v1`。

## 工程结构

- `genui_intent/router.py`：低 token 领域路由。
- `genui_intent/prompts.py`：生产系统提示词与按领域动态注入。
- `genui_intent/registries.py`：首批五领域注册表。
- `genui_intent/providers.py`：端侧模型 HTTP 适配。
- `genui_intent/validation.py`：确定性校验和安全失败。
- `genui_intent/layout_engine.py`：PDF 范式、组件/槽位评分、全局分配与自由模式。
- `genui_intent/renderers.py`：RenderSpec 到 HTML/CSS、A2UI 的可插拔协议映射。
- `schemas/raw-intent.schema.json`：可交给支持 Structured Output/Grammar 的推理引擎。
- `docs/下一阶段与布局模板设计.md`：JSON 之后的执行链路及泛化布局模板方案。
- `evals/`：真实 Ollama 分层评测集、批量评分和结果留档工具。
- `tests/`：无需 pytest 的单元测试。

运行测试：

```powershell
python -m unittest discover -s tests -v
```

Ollama 安装完成后先跑 5 条冒烟测试，再跑完整集：

```powershell
python evals/run_ollama_eval.py --limit 5
python evals/run_ollama_eval.py --model qwen2.5:3b --output evals/results/qwen2.5-3b-baseline.jsonl
```

详细用法见 `evals/README.md`。

当前是意图层最小可运行基线。生产接入时建议再用 llama.cpp grammar、Ollama JSON Schema 或模型 SDK 的 structured output 在解码期约束输出；本工程的校验仍应保留，作为不可绕过的信任边界。
