# v1.0 Release Notes

## 定位

**家庭自由度规划师** 是一个 GitHub-first、Agent-native 的家庭重大决策 Skill。

核心承诺：

> 不替你预测未来，帮你准备不同的未来。

## v1.0 新增

- 38 个 benchmark cases；
- 30 个标准家庭场景；
- 5 个 counterfactual cases；
- 3 个 invariance cases；
- 覆盖首次购房、换房、教育、职业、脱产、融资、父母养老、迁移、投资等；
- 覆盖高净资产低流动性、负债重、收入波动、单亲、无孩、两孩、国际教育等边界场景；
- 新增 6 维 Eval Rubric；
- 新增 benchmark validator；
- 新增 Release Gate；
- 保留 v0.8 Intent-to-Intake 与 v0.9 Portable Context。

## v1.0 不承诺

- 不预测房价；
- 不预测职业寿命；
- 不给确定性投资收益；
- 不替代律师、税务师、银行正式审批或教育局政策确认；
- 不替夫妻做价值判断。

## 核心架构

```text
Public Skill
+
Private Family Context
+
Deterministic Reference Engine
+
External Current Facts
+
Benchmark / Evals
```

## 建议发布方式

1. GitHub Public Repo
2. README 第一屏放 Copy-to-Agent Prompt
3. Skill 路径固定：
   `skills/family-freedom-planner`
4. Release tag：
   `v1.0.0`
5. 后续修改遵循 Semantic Versioning
