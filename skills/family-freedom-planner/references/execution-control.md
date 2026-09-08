# Execution Control & Recommendation Gate

## v1.3 运行兼容性

运行记录绑定工作流版本与内容 hash。旧版本 run.json 需使用已确认的原始家庭输入重新初始化，不沿用旧步骤的 COMPLETE 或 PASS。

STRESS_TEST 的每个情景须提供 income_annual、spending_annual、annual_net_cashflow 与 assumptions；只有 NORMAL/STRESS/SEVERE 空对象不算完成。单位为元/年，现金流必须等于收入减支出。OPTIONS_VALIDATE 需覆盖每个方案，不能用空列表声称全部通过。

仓库演示可直接运行 scripts/demo_controlled_run.py，不写文件，使用虚构数据。它实际计算并执行完整性门禁；政策未联网验证，因此最终保持 CONDITIONAL_PASS。

v1.1 将“应该按顺序分析”升级为运行时强制执行。

## 核心原则

> LLM 负责理解与生成候选结果；Control Plane 决定下一步是否允许执行。

不要让模型自己决定：
“信息差不多了，我直接给建议。”

---

# 1. 状态机

核心顺序：

```text
INTAKE_ROUTE
→ STATE_BUILD
→ INPUT_VALIDATE
→ DEADLINE_IDENTIFY
→ BASELINE_CALCULATE
→ Relevant Domain Steps
→ EXTERNAL_FACT_CHECK (if material)
→ STRESS_TEST
→ OPTIONS_BUILD
→ OPTIONS_VALIDATE
→ RECOMMENDATION_GATE
→ FINALIZE
```

不相关的 Domain Step 可以 `SKIPPED`，但必须由 applicability 规则判定，而不是模型任意跳过。

---

# 2. Step Contract

每个步骤都有：

- `requires`
- `applicability`
- `required_output_keys`
- `validators`
- `system_managed`

定义在：

- `workflow.yaml`：人类阅读
- `assets/workflow.compiled.json`：运行时读取

二者来自同一 spec。

---

# 3. Fail Closed

如果：

- 前置步骤未完成；
- 输出缺必需字段；
- Validator 失败；
- 仍有关键 P0 缺失；
- 适用 Domain 被跳过；
- 外部事实未验证且结论没有条件化；
- Options 有 critical error；

则 Recommendation Gate 不得 PASS。

系统宁可：

> “当前不能稳定排序。”

也不要带错数据继续。

---

# 4. Recommendation Gate

只有以下条件满足才允许 FINALIZE：

- 所有必需步骤 COMPLETE 或合法 SKIPPED；
- `INPUT_VALIDATE.conflicts` 为空；
- `OPTIONS_VALIDATE.all_options_validated = true`；
- `OPTIONS_VALIDATE.critical_errors` 为空；
- 不存在 unresolved P0；
- 外部事实如未验证，最终结论必须 conditionalized。

Gate 状态：

## PASS
可以给正常推荐。

## CONDITIONAL_PASS
可以给条件化建议，但必须明确：
- 哪些事实尚未验证；
- 执行前必须确认什么；
- 不得把条件写成事实。

## BLOCKED
不允许给明确推荐。
只能：
- 补关键输入；
- 修复冲突；
- 完成漏掉步骤。

---

# 5. Execution Ledger

每个 run 保留：

- step status
- timestamp/order
- input/output
- validator result
- skip reason
- gate reasons

它是审计轨迹，不是隐藏推理链。

可用于回答：

> “你这次到底执行了哪些步骤？”

---

# 6. 工具调用规则

确定性财务计算：
优先 `family_freedom_engine.py`。

外部当前事实：
由联网/连接工具获取。

LLM：
负责语义理解、情景构造、解释和价值权衡。

不要让 LLM 用心算替代已经存在的确定性工具。

---

# 7. Runtime CLI

初始化：

```bash
python scripts/workflow_orchestrator.py init \
  examples/execution_run_input.json \
  /tmp/run.json
```

查看当前允许步骤：

```bash
python scripts/workflow_orchestrator.py next /tmp/run.json
```

完成步骤：

```bash
python scripts/workflow_orchestrator.py complete \
  /tmp/run.json \
  STATE_BUILD \
  examples/execution_step_outputs/state_build.json
```

运行 Recommendation Gate：

```bash
python scripts/workflow_orchestrator.py gate /tmp/run.json
```

最终完成：

```bash
python scripts/workflow_orchestrator.py finalize \
  /tmp/run.json \
  examples/final_output_conditional.json
```

---

# 8. 强保证与不能保证的边界

可以强保证：

- 不允许非法状态跳转；
- 适用步骤不能随意跳过；
- 缺字段不能标记完成；
- 特定逻辑 Validator 不通过不能继续；
- Gate 未通过不能 FINALIZE。

不能数学上100%保证：

- LLM 对用户语义永远理解正确；
- 外部数据源永远正确；
- 所有现实风险都已建模。

因此还需要：
- Evals；
- Counterfactual；
- Invariance；
- External fact provenance；
- 用户纠错与 Delta Replan。
