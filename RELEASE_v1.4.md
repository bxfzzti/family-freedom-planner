# v1.4.0 统一家庭状态与全步骤自动复算

## 统一家庭状态

`assets/family-state.schema.json` 成为上下文、计算和工作流的共同数据结构。金额固定为人民币元，收入与支出固定为年度；收入声明 AFTER_TAX、BEFORE_TAX 或 UNKNOWN，支出声明是否已含债务还款。现金、低风险资产、波动资产、其他流动资产和未拆分金融资产分别记录。

每个已知关键金额在 `source_tags` 按字段路径记录来源、日期和置信度。确定性计算只接受校验通过且 calculation-ready 的状态：税前或未知收入、未拆分金融资产、未知债务余额、原始贷款本金、未知支出口径都会阻止计算。

`input.schema.json` 成为工作流输入信封；`family-context.schema.json` 保存统一family_state及目标、假设、待确认问题和决策记录。旧 `known_context` 输入被拒绝，避免两套状态并存。

## 旧上下文迁移

`migrate_context.py` 将0.9 Capsule迁移至1.4。旧字段“现金+金融资产”进入 `unallocated_financial_assets`，收入税收口径设为UNKNOWN，支出是否含债务还款保持未知，并生成三个明确待确认问题。迁移结果可以继续问诊，但不能直接计算。

虚构迁移示例：`examples/family-context-v1.4-migrated.json`。

## 全步骤自动复算

INTEGRITY_GATE现在基于实际步骤输出自动运行，不要求调用者先提交一份PASS报告：

- BASELINE_CALCULATE：从标准family_state重新运行引擎，逐项核对结果，并复算净资产和年结余恒等式。
- HOUSING_ANALYSIS：逐option_id复算买后流动资产和置换价差。
- FINANCING_ANALYSIS：逐option_id复算全额摊还按揭月供或续贷缺口。
- EDUCATION_ANALYSIS：检查BASE/MID/HIGH费用单调性。
- CAREER_ANALYSIS：核对当前收入、减少收入、新收入与转型后收入。
- STRESS_TEST：核对年度现金流；提供option_runs时重新运行decision_cashflow并比较完整结果。
- OPTIONS_VALIDATE：核对方案ID、逐方案校验和压力测试覆盖。

STRESS_TEST与OPTIONS_VALIDATE加入关键完整性门禁。外部证据与运行时结果按最弱状态合并；运行时FAIL直接隔离，外部PASS不能将其升级。

## 验证

- 148项unittest通过。
- benchmark_cases.json的38例结构与覆盖检查通过；仍不等同38次模型回答。
- Skill结构、自检、完整虚构演示、标准状态计算和旧上下文迁移通过。
- 全部示例为虚构数据；没有提交真实家庭资料。

## 兼容边界

工作流版本为1.4.0，旧run.json必须从已确认输入重新初始化。0.9上下文可以迁移；迁移不会猜测缺失口径。JSON Schema用于分发契约，Python标准库校验器负责实际计算入口。其他客户端的自动触发和完整规划仍需分别验证。

## 发布回读

v1.4代码提交 `5f005ec7d71154ab29353228e5d875d6aacafd62` 已推送。GitHub CI成功；从该远端提交全新隔离安装后，148项测试、自检、完整演示、标准状态验证和旧上下文迁移全部通过。

本机默认安装也已更新到同一提交，关键文件哈希与仓库完全一致，148项测试和自检通过。原v1.3.3安装保存在 `/Users/xxqq/.codex/skill-backups/family-freedom-planner-6957f03`，需要时可恢复。
