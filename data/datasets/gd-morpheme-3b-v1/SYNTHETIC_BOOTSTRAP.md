# ⚠ 定位声明：synthetic_bootstrap（L0 工程回归数据）

本目录数据由固定句式模板确定性生成（"帮我看看{X}/做一张{X}卡片"等），
详见 docs/数据三层计划与双机交接.md（claude 分支）：

- **仅用于**：训练管线冒烟与工程回归；
- **禁止**：单独作为正式 SFT 数据并对外宣称模型能力；
- **禁止**：以本目录 dev/test 分数汇报"模型准确率"（同分布模板数据）。

另注：tools/build_3b_dataset.py 内置的骨架枚举（101 个）与主线
tools/gen_training_data.py（125 个）并行重复；**主线枚举器为唯一事实源**，
本脚本仅随 L0 数据保留存档。

正式训练集（L1）：claude 分支 data/factory/sft_train_v1.jsonl。
正式评测（L2）：evals/frozen/（人工签字条目）。
