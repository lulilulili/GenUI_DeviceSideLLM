# GD 端侧 3B 数据集说明

## 目标

GD 是单轮流程，端侧模型只输出语素草稿：`{t, m:[{l,q,f,r}]}`。模板、组件、能力绑定、信息预算、布局和渲染均由确定性代码完成。因此 GD 的训练标签不是 HTML、A2UI 或 templateId，而是注册表允许的语素草稿。

## 产物

运行 `tools/build_3b_dataset.bat` 后，默认生成 `data/datasets/gd-morpheme-3b-v1/`：

- `gd_train.jsonl`、`gd_dev.jsonl`、`gd_test.jsonl`：单轮语素 SFT messages。
- `gd_all.audit.jsonl`：骨架、中文表达、领域和契约信息，不应喂给模型。
- `gd_dataset_card.json`：数量、切分和限制。

当前生成 3,636 条单轮样本，来自 101 个注册表合法骨架；train/dev/test 按骨架稳定哈希切分，保证同一骨架不会跨 split。每条答案都只含 `t` 和 `m`，不含 `templateId`、组件类型、CSS、动态数据或真实 Action。

## 实习生数据的使用边界

实习生 V4 数据的协议是最终 Frame，和 GD 的 MorphemeDraft 不同。本版不把它直接混入 GD SFT，避免把最终模板选择协议污染到语素协议。它可以继续作为单独的自然语言评测和难例来源；后续若要吸收，必须先人工改标为 GD 语素答案，再按 seed 或 scenario 做泄漏隔离。

## 训练建议

只对 assistant 消息计算 loss。训练前先抽查每个骨架的表达是否自然，再用 `genui_v2.protocol.validate_draft` 和完整确定性管线做标签校验。正式评测应同时报告语素 key、角色、格式、绑定成功率和最终模板命中率；模板命中率属于确定性布局资产，不应单独归因于模型训练。
