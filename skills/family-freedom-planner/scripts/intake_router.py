#!/usr/bin/env python3
"""Lightweight intake topic router.

This is a helper, not a substitute for semantic judgment.
It emits topic suggestions from Chinese text using transparent keyword rules.
"""

import argparse
import json
import re

RULES = {
    "HOUSING_EXISTING": [
        "换房", "卖房", "改善房", "学区房", "房价", "先卖后买", "租两年",
        "现有房", "已有房", "房贷", "置换"
    ],
    "HOUSING_FIRST_BUY": [
        "首套", "第一次买房", "首次购房", "一直租房", "首付", "还没买房", "没有房"
    ],
    "EDUCATION": [
        "学区", "上学", "小学", "幼儿园", "初中", "高中", "教育", "国际学校", "留学"
    ],
    "CAREER": [
        "大厂", "离职", "退休", "40岁", "35岁", "工作不稳", "裁员",
        "职业转型", "副业", "降低工作强度", "自由职业"
    ],
    "SPOUSE_BREAK": [
        "全职带娃", "不上班", "辞职带娃", "脱产", "在家带孩子"
    ],
    "FINANCING": [
        "抵押贷", "经营贷", "续贷", "提前还贷", "利率", "月供", "按揭", "贷款"
    ],
    "PARENT_CARE": [
        "父母养老", "赡养", "父母医疗", "照顾父母", "护理"
    ],
    "RELOCATION": [
        "回县城", "回老家", "换城市", "移居", "出国", "国外生活", "小城市"
    ],
    "INVESTING": [
        "股票", "基金", "理财", "投资亏损", "资产配置", "投资新手"
    ],
}

PRIORITY = [
    "HOUSING_EXISTING", "HOUSING_FIRST_BUY", "EDUCATION", "CAREER",
    "SPOUSE_BREAK", "FINANCING", "RELOCATION", "PARENT_CARE", "INVESTING"
]


def route(text: str, max_topics: int = 3):
    scores = {}
    matched = {}
    for topic, words in RULES.items():
        hits = [w for w in words if w in text]
        if hits:
            scores[topic] = len(hits)
            matched[topic] = hits

    # Avoid treating ordinary "贷款" as a separate first-round topic when housing
    # is already selected unless financing is explicit.
    if "FINANCING" in scores and any(t in scores for t in ("HOUSING_EXISTING", "HOUSING_FIRST_BUY")):
        explicit = any(w in text for w in ["抵押贷", "经营贷", "续贷", "提前还贷", "利率", "月供"])
        if not explicit:
            scores["FINANCING"] = max(0, scores["FINANCING"] - 1)
            if scores["FINANCING"] == 0:
                scores.pop("FINANCING", None)

    ordered = sorted(
        scores,
        key=lambda t: (-scores[t], PRIORITY.index(t) if t in PRIORITY else 999)
    )
    selected = ordered[:max_topics]
    if not selected:
        selected = ["GENERAL"]

    return {
        "selected_topics": selected,
        "deferred_topics": ordered[max_topics:],
        "matched_terms": {k: matched[k] for k in selected if k in matched},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--max-topics", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(route(args.text, args.max_topics), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
