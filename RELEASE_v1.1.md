# v1.1 Execution Control Edition

v1.0 解决“方法是否可靠”。

v1.1 解决：

> **方法会不会被 Agent 按正确顺序执行。**

## 新增

- `workflow.yaml`：人类可读状态机
- `assets/workflow.compiled.json`：运行时状态机
- `scripts/workflow_orchestrator.py`
- Step Contracts
- Applicability / explicit auto-skip
- Step Validators
- Execution Ledger
- Recommendation Gate
- PASS / CONDITIONAL_PASS / BLOCKED
- Fail-closed 行为
- 非法跳步测试
- 适用步骤非法 skip 测试
- 住房置换漏目标房测试
- 融资漏续贷失败测试
- 压力测试缺 SEVERE 测试
- Gate / Finalize 测试

## 能保证什么

在 Agent **通过本 Orchestrator 执行**的前提下：

- 不能跳过未满足的前置步骤；
- 不能任意跳过适用步骤；
- 缺关键输出字段无法 COMPLETE；
- 特定 Validator 失败无法继续；
- Recommendation Gate 未通过不能 FINALIZE。

## 不能保证什么

如果 Agent 完全绕开 orchestrator、直接自由回答，则运行时保证不生效。

因此集成方应把：

> `workflow_orchestrator.py`

作为控制平面，而不是可选参考。
