# GenUI 端侧项目讨论交接

## 1. 项目目标

项目希望使用能力约等于 Qwen2.5 3B 的端侧小模型，根据用户的一句话提示生成手机上的生成式 UI。首个落地形态是 2×1、2×2、3×3 等桌面服务卡片，但意图识别协议需要保持 UI 形态无关，以便未来扩展到页面、表单、弹窗、通知、Widget、Overlay 和自动化配置界面。

原始材料：

- `语素字段设计规范.pptx`：现有语素拆解、组件、角色、优先级及模板映射构想。
- `桌面服务卡片.pdf`：桌面服务卡片视觉与尺寸参考。

## 2. 已达成的核心判断

现有总体方向“提示词 → 语素 → 模板槽位 → DSL/HTML”具备可行性，但对于 3B 模型，应重新划分模型与代码职责：

```text
小模型：理解用户任务，输出受约束的业务意图
代码：实体解析、能力验证、参数补全、动作绑定
内容模块：生成实际文案或其他内容
UI 编排器：选择载体、模板、组件、布局和降级方式
渲染器：生成最终原生 UI / DSL / HTML
```

不建议让 3B 模型直接决定 `Button`、`Slider`、模板、CSS、HTML、系统 Action ID 或动态数据绑定。PPT 中的实测已经出现外层数组错误、动态数据编造、组件选择错误、Action 格式不合法、字段名异常等问题，说明继续堆叠 Prompt 无法从根本上解决稳定性。

## 3. 意图抽象结论

原先的“对象、行为、度量、环境”适合作为基础，但建议扩展为：

```text
Goal
└── Tasks
    ├── Entity
    ├── Operation
    ├── Parameters
    ├── Context
    ├── Constraints
    └── Dependencies

+ PresentationRequest
+ Ambiguity / Resolution
```

对应关系：

| 原始概念 | 推荐概念 | 说明 |
|---|---|---|
| 对象 | `entity` | 操作、查询或生成所针对的对象。 |
| 行为 | `operation` | 查询、设置、创建、搜索等通用行为。 |
| 度量 | `parameters` | 扩展为数值、状态、范围、文本、相对变化、偏好等通用参数。 |
| 环境 | `context` | 时间、地点、用户、设备、应用、活动和事件等上下文。 |
| — | `goal` | 用户最终希望实现的目的。 |
| — | `constraints` | 范围、阈值、排序、排除条件等。 |
| — | `dependencies` | 多任务之间的顺序或条件关系。 |
| — | `presentation` | 用户明确提出的 UI 载体要求；未指定时为 `AUTO`。 |
| — | `resolution` | 缺失、不确定、需要上下文或不支持等状态。 |

## 4. 推荐的阶段边界

端侧模型只输出精简的 `RawIntentSpec`。后续代码再将其规范化成完整内部 `IntentSpec`。

```text
用户提示词
→ 输入预处理
→ 领域初步路由
→ 注入当前领域枚举、动态候选和少量示例
→ 端侧模型生成 RawIntentSpec
→ JSON / Schema / 枚举 / 动态候选校验
→ 已校验 RawIntentSpec
→ 后续实体解析、能力校验、内容生成和 UI 编排
```

具体协议、枚举、字段注释、流程图和示例见：

- `端侧模型意图输出协议.md`

## 5. 枚举与开放字段的边界

不是所有输出都应枚举化。已确定采用三类字段组合：

| 类型 | 策略 | 示例 |
|---|---|---|
| 强约束语义 | 固定枚举 | `intentType`、`operationType`、`expressionType`、`resolution.status` |
| 领域语义 | 运行时动态注册表候选 | `entityCategoryKey`、`propertyKey`、`parameterKey` |
| 用户内容 | 开放字符串 | 设备原始名称、联系人名称、提醒内容、搜索词 |

关键规则：

1. 所有影响代码分支、能力调用和 UI 类型选择的字段都必须受约束。
2. 枚举必须按语义区分 `OTHER`、`UNKNOWN`、`UNSPECIFIED`。
3. 不建立包含几百项的全局实体或属性枚举；领域路由后只注入当前领域候选。
4. 用户未明确指定 UI 形态时，`surfaceType=AUTO`。
5. 不确定时必须输出缺失或 `UNKNOWN`，不能编造设备、数值或时间。

## 6. 代表性示例结论

用户提示：

```text
我马上要考试了，请帮我加油打气。
```

该请求应识别为内容生成和情感支持，而不是直接输出卡片组件：

```text
intentType = CREATE
domain = CONTENT
goalType = OBTAIN_EMOTIONAL_SUPPORT
entityCategoryKey = encouragement_message
operationType = CREATE
topic = exam
tone = ENCOURAGING
recipient = SELF
temporalType = IMMINENT
surfaceType = AUTO
```

正确阶段拆分：

```text
IntentSpec：用户需要考试场景下的鼓励内容
ContentResult：内容模块生成实际鼓励文案
RenderSpec：UI 编排器决定卡片、页面或其他展示方式
```

## 7. 卡片实现建议

PDF 中的卡片具有明显领域特征，不适合只用完全通用的组件装箱算法。建议使用“领域模板族 + 尺寸变体”：

- `single_action`
- `status_summary`
- `device_control`
- `media_control`
- `progress_goal`
- `list_summary`
- `contact_action`
- `information`

每个模板提供 2×1、2×2、3×3 变体，并定义语义降级策略。例如天气卡片从 3×3 到 2×1，应按“完整预报 → 今日摘要 → 当前温度和状态”降级，而不是简单按组件优先级删除。

## 8. Prompt Token 评估

当前完整协议文档约为：

- 26,314 个字符；
- 5,238 个中文字符；
- 20,043 个 ASCII 字符；
- 约 11,000～16,000 tokens（具体取决于 Qwen tokenizer）。

完整文档不适合直接作为 3B 模型系统提示词。推荐生产预算：

| 输入组成 | 推荐 Token 数 |
|---|---:|
| 固定系统规则 | 500～900 |
| 精简输出 Schema | 500～900 |
| 当前领域枚举和动态候选 | 300～800 |
| 2～3 个相关 Few-shot | 500～1,200 |
| 用户提示词和必要上下文 | 100～500 |
| 总输入 | 约 1,900～4,300 |

理想目标：

```text
固定系统提示词：1,000～1,800 tokens
单次总输入：2,000～3,500 tokens
模型输出：100～300 tokens，复杂多任务不超过约 600 tokens
```

## 9. 推荐实施顺序

1. 冻结 `RawIntentSpec v1.0` 和 JSON Schema。
2. 第一版只启用 `SMART_HOME`、`WEATHER`、`DEVICE`、`CONTENT`、`TASK` 五个领域。
3. 为每个领域建立独立的实体、属性、参数和枚举值注册表。
4. 生成生产版精简系统提示词，配合 JSON Schema 或 Grammar constrained decoding。
5. 建立 500～1,000 条测试集，覆盖单意图、多意图、省略表达、相对表达、歧义和不支持请求。
6. 实现实体解析、能力注册表和动作白名单。
7. 实现模板族和不同尺寸的语义降级。
8. 在目标设备上测量准确率、P50/P95 延迟、峰值内存、功耗和温升。

## 10. 建议下一步继续讨论的事项

建议在新项目中按以下顺序展开：

1. 审核并精简 `RawIntentSpec`，决定哪些字段必须由模型输出、哪些由代码补齐。
2. 输出可直接用于 Qwen2.5 3B 的生产版 System Prompt。
3. 输出对应 JSON Schema / Grammar。
4. 定义首批五个领域的动态注册表。
5. 构建 Few-shot 示例和自动化评测数据集。
6. 再设计 `IntentSpec → CardModel` 的映射协议。

