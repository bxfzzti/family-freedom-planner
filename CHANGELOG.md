# Changelog

## v1.2.0 — Result Integrity

- 新增 Result Envelope、provenance、cross-check。
- 新增 Source Consistency、Freshness、Semantic Sanity。
- 新增 QUARANTINED / STALE / Rollback。
- 新增 Dependency Graph 与 Integrity Gate。
- Recommendation Gate 现在必须在 Integrity Gate 之后。


## v1.1.0 — Execution Control

- 新增 runtime 状态机与 workflow.yaml。
- 新增前置条件、applicability、step validators。
- 新增 Execution Ledger 与 Recommendation Gate。
- Gate 支持 PASS / CONDITIONAL_PASS / BLOCKED。
- 非法跳步、非法skip、关键步骤漏检均 fail closed。
- 新增 execution-control tests。


## v1.0.0 — Reliability & Public Release

- 建立 38 个真实家庭风格 benchmark cases。
- 新增 30 个标准场景、5 个 counterfactual、3 个 invariance。
- 新增 Reliability Eval Rubric 与覆盖矩阵。
- 新增 benchmark validator 和 release gate。
- 新增 RELEASE、CONTRIBUTING、PRIVACY、VERSION。
- 正式把项目定位为 GitHub-first Agent Skill，而非 API-first 产品。


## v0.9 — Portable Context & Delta Replan Edition

- 新增 Family Context Capsule：家庭状态可携带、可版本化。
- 第二次及之后默认使用 Delta Intake，不再重新问诊。
- 新增变化影响传播：明确新信息改变了哪些旧结论。
- 新增 Decision Journal 与 revisit_if 机制。
- 新增跨 Agent 使用模式：family-context.json 跟着用户走。
- 新增 state_diff.py、context schema、示例和测试。


## v0.8 — Intent-to-Intake Edition

- 用户只需一句自然语言描述，不再自己选择模块。
- Agent 自动识别最多3个相关主题。
- 自动预填对话里已经知道的家庭信息。
- 首次补充信息限制为6—10个短字段。
- 新增 P0/P1/P2 缺失字段优先级。
- 新增 progressive intake：第一版诊断后再展开次要主题。
- 新增 intake_router.py、路由测试和个性化问诊示例。


## v0.7.1 — Adaptive Intake Patch

- 首次问诊从固定家庭模板改为「基础主干 + 可选模块」。
- 新增住房、首次购房、教育、职业、脱产、融资、父母、迁移、投资模块。
- Agent 根据用户意图只推荐 1—3 个相关模块。
- 未提及变量视为 UNKNOWN，不再默认 NO。
- 增加模块化问诊 evals。


## v0.7 — GitHub Distribution Edition

- 重构为 GitHub-first 分发。
- 将 8万+ 字单文件拆为薄 `SKILL.md` + 按需 `references/`。
- 增加 `INSTALL_PROMPT.md`：用户复制一段话给自己的 Agent 即可安装/加载。
- 增加 `AGENTS.md`：仓库级 Agent 说明。
- 增加标准库 Reference Engine CLI。
- 增加 JSON Schema、示例、evals 和 unittest。
- 保留 v0.6 的“复制替换数字”低摩擦首次问诊。
- 采用 progressive disclosure，避免一次加载全部上下文。
