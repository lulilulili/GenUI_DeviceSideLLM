"""将人审通过的 unsupported 桶条目固化进 frozen_set_v1.jsonl。

评审记录（2026-09-11，评审人：Claude 初审，用户终审后请把本文件头部的
FINAL_SIGNED 改为 True 并升 frozen-set 版本）：
- 来源：intern_distilled_draft.jsonl 的 246 条自然语言候选；
- 排除：带"先给我结果/不要添加工具结果"指令样板的 288 变体全部排除；
- 入选 58 条：純域外 44 + 误路由假绑陷阱 14；另含 2 条邻域 tricky（见 notes）；
- 每条 notes 标注拒绝理由与假绑风险词，供错误分析用。

用法：python tools/curate_unsupported_bucket.py
输出：evals/frozen/frozen_set_v1.jsonl（追加/重建 unsupported 桶部分，
      文件含实习生衍生措辞，已在 .gitignore 中，不入个人仓库）
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "evals" / "frozen" / "intern_distilled_draft.jsonl"
OUT = ROOT / "evals" / "frozen" / "frozen_set_v1.jsonl"

FINAL_SIGNED = False  # 用户逐条终审签字后改 True

# intern-id -> (类别, notes)
SELECTED = {
    # —— 出行/位置（注册表完全无此域）
    "intern-001": ("出行", "景点推荐：无 POI 能力"),
    "intern-004": ("出行", "网约车状态：无出行能力；风险词=距离/车牌"),
    "intern-005": ("出行", "叫车入口：无出行动作"),
    "intern-011": ("出行", "公交到站：无公交能力"),
    "intern-012": ("出行", "航班状态：无航旅能力；多字段仍须整体拒绝"),
    "intern-018": ("出行", "火车时刻查询"),
    "intern-021": ("出行", "驾车通勤+路况：无导航能力"),
    "intern-022": ("出行", "快递物流：无物流能力"),
    # —— 预订/订单确认
    "intern-003": ("订单", "餐厅订位状态；风险词=详情入口(易被当 BUTTON)"),
    "intern-020": ("订单", "车票订单：无订单能力"),
    "intern-026": ("订单", "酒店入住+房卡入口"),
    # —— 住房/租车/电商
    "intern-008": ("电商", "找公寓：曾被误路由 SMART_HOME(两'卫'非卫浴设备)"),
    "intern-027": ("电商", "找住处"),
    "intern-031": ("电商", "三款续航对比结论：无商品对比能力"),
    "intern-034": ("电商", "商品详情页"),
    # —— 健康（注册表无健康域）
    "intern-039": ("健康", "生理期记录"),
    "intern-041": ("健康", "血压/心率/血糖/体重汇总"),
    "intern-043": ("健康", "喝水进度：PERCENTAGE 诱惑但无能力"),
    "intern-044": ("健康", "服药清单：LIST 诱惑但无能力"),
    "intern-048": ("健康", "摄入热量分餐"),
    "intern-052": ("健康", "专注状态：无专注能力"),
    # —— 金融
    "intern-053": ("金融", "付款码+鉴权状态"),
    "intern-059": ("金融", "汇率查询"),
    "intern-061": ("金融", "转账进度"),
    "intern-062": ("金融", "账户余额"),
    "intern-063": ("金融", "预算余额：进度条诱惑"),
    # —— 媒体
    "intern-066": ("媒体", "播放状态+暂停入口：'暂停'动作词诱惑但无媒体能力"),
    "intern-067": ("媒体", "听歌识曲记录"),
    "intern-070": ("媒体", "球赛比分"),
    "intern-076": ("媒体", "找科幻片"),
    "intern-077": ("媒体", "电影场次"),
    "intern-080": ("媒体", "RSS 未读"),
    # —— 社交/通信
    "intern-085": ("社交", "联系人快捷入口"),
    "intern-087": ("社交", "团队消息未读/@"),
    "intern-088": ("社交", "他人主页数据"),
    # —— 系统工具（设备邻域，注册表未覆盖）
    "intern-046": ("系统邻域", "应用时长占比：DEVICE 邻域但无 app-usage 能力"),
    "intern-090": ("系统邻域", "录屏启动：实习生 G07 同款枚举缺口"),
    "intern-091": ("系统邻域", "全局搜索入口"),
    "intern-100": ("系统邻域", "手电筒/计算器等四工具"),
    "intern-103": ("系统邻域", "存储空间：battery 之外的设备指标，假绑高危"),
    "intern-106": ("系统邻域", "当前时间日期：DATETIME 形态存在但无时钟能力"),
    "intern-116": ("系统邻域", "置顶笔记"),
    # —— 误路由假绑陷阱（曾被规则路由带偏，考'不乱绑'的一级素材）
    "intern-010": ("假绑陷阱", "'摘要'一词曾误路由 CONTENT；实为巴士查询"),
    "intern-014": ("假绑陷阱", "机票摘要+订单入口：'摘要'诱导 CONTENT"),
    "intern-033": ("假绑陷阱", "商品摘要：'摘要'诱导 CONTENT"),
    "intern-045": ("假绑陷阱", "'耳机'诱导 DEVICE；实为听力安全评估"),
    "intern-057": ("假绑陷阱", "'耳机'诱导 DEVICE；实为订单支付"),
    "intern-071": ("假绑陷阱", "相册照片说明；曾误路由 SMART_HOME"),
    "intern-079": ("假绑陷阱", "新闻摘要：'摘要'诱导 CONTENT"),
    "intern-084": ("假绑陷阱", "孩子位置：曾误路由 WEATHER；实为家人定位"),
    "intern-086": ("假绑陷阱", "发送位置：曾误路由 WEATHER"),
    "intern-102": ("假绑陷阱", "MatePad 在线+位置：设备词诱导 DEVICE/WEATHER"),
    "intern-110": ("假绑陷阱", "'提醒'诱导 TASK；实为剪贴板隐私预览"),
    "intern-113": ("假绑陷阱", "清理管家：曾误路由 SMART_HOME"),
    "intern-140": ("假绑陷阱", "邮件摘要：'摘要'诱导 CONTENT"),
    "intern-142": ("假绑陷阱", "阳台温湿度光照：'温度湿度'诱导 WEATHER，实为家居传感器面板"),
    # —— 邻域 tricky（刻意保留的边界题）
    "intern-083": ("邻域tricky", "穿衣/防晒/洗车建议：天气邻域但注册表无建议类字段"),
    "intern-128": ("邻域tricky", "查空闲时段：日历邻域但注册表仅有 next_event"),
}


def main() -> int:
    drafts = {json.loads(line)["id"]: json.loads(line)
              for line in DRAFT.read_text(encoding="utf-8").splitlines() if line}
    missing = [key for key in SELECTED if key not in drafts]
    assert not missing, "草稿缺少条目: %s" % missing
    entries = []
    for index, (intern_id, (category, note)) in enumerate(SELECTED.items(), 1):
        draft = drafts[intern_id]
        assert "先给我结果" not in draft["prompt"], intern_id
        entries.append({
            "id": "uns-%03d" % index,
            "bucket": "unsupported",
            "prompt": draft["prompt"],
            "expected": {"reject": True, "domain": None, "morphemes": [], "max_actions": 0},
            "notes": "[%s] %s" % (category, note),
            "provenance": draft["provenance"].get("origin"),
        })
    existing = []
    if OUT.exists():
        existing = [json.loads(line) for line in OUT.read_text(encoding="utf-8").splitlines()
                    if line and json.loads(line)["bucket"] != "unsupported"]
    with OUT.open("w", encoding="utf-8") as handle:
        for entry in existing + entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    from collections import Counter
    print("unsupported 桶写入 %d 条（其他桶保留 %d 条）" % (len(entries), len(existing)))
    print("类别分布:", dict(Counter(v[0] for v in SELECTED.values())))
    print("终审状态:", "已签字" if FINAL_SIGNED else "待用户终审（FINAL_SIGNED=False）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
