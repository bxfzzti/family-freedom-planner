# 实际对话评估

三个不同层次必须分别报告：

1. unittest：确定性脚本与控制逻辑。
2. validate_benchmark.py：案例数量、字段、覆盖要求；没有运行 Agent。
3. 本评估：真实回答的逐项语义审阅；仍受被测模型、版本和审阅质量限制。

## 采集

使用 dialogue_cases.json。每个案例开一个干净对话，给被测 Agent 读取当前 SKILL.md 的能力，但不把 criteria 或参考答案给它。逐条发送 user_turns，收集实际回答，不修改回答来满足规则。记录模型、Skill commit、日期和运行来源。不要在普通 CI 中自动调用付费模型。

recordings.json 格式：

```json
{
  "run": {
    "model": "实际被测模型名",
    "skill_revision": "实际commit或工作树内容标识",
    "recorded_at": "实际运行时间",
    "origin": "agent_run"
  },
  "cases": [
    {"id": "housing_career_first_turn", "turns": [
      {"user": "与案例完全相同的原始输入", "assistant": "未经改写的实际回答"}
    ]}
  ]
}
```

同一作者亲自演练而非独立运行时，origin 必须为 self_review，并在报告中称“自审”；不得称为跨模型或独立通过。以上是格式说明，不是可提交的测试结果。

## 审阅

审阅者逐项判读所有轮次，在 reviews.json 为每个 case 保存 reviewer、case_sha256、transcript_sha256 和 checks。摘要 hash 使用 evaluate_dialogues.py 的 digest()，绑定完整 case 对象和完整 turns 数组。

每个 checks 项以案例 criterion ID 为键，包含 verdict（PASS/FAIL）、turn（从0开始的回答索引）、evidence（回答中的原文片段）、reason（为什么满足或违反该标准）。禁止仅凭关键词或模型自称“我遵守了”通过；对“没有重复问”等否定标准仍需读完整回答，并引用相关段落解释。

## 汇总

在 Skill 根目录：

```bash
python scripts/evaluate_dialogues.py evals/dialogue_cases.json recordings.json reviews.json
```

PASS 返回0；任何有证据失败返回1；缺数据、未审阅、hash过期或输入错误返回2。部分通过不会伪装成全部通过。脚本核查证据和审阅完整性，不独立判断语义或认证审阅者身份。

案例或回答更改后旧审阅自动失效；新增规则需要新增案例并重新评估。测试记录只用虚构家庭信息。
