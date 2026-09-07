# Result Integrity, Cross-Validation & Rollback

v1.2 解决的问题：

> 流程虽然正确，但某一步结果本身可能错。

例如：

- LLM 把 450 万解析成 550 万；
- 基础现金流计算和 Reference Engine 不一致；
- 外部房价来源互相冲突；
- 学区政策来源过旧；
- 一个方案的买后流动资产为负，但模型仍然给出“可接受”；
- 新结果明显违反旧状态，却没有触发重新确认。

v1.2 的原则：

> **每个重要结果都必须有“来源、交叉检查、异常处理、回滚策略”。**

---

# 1. Result Envelope

所有关键 Step 输出都应包在 Result Envelope 中：

```json
{
  "data": {},
  "provenance": [],
  "cross_checks": [],
  "integrity": {
    "status": "PASS|WARN|FAIL",
    "confidence": "HIGH|MEDIUM|LOW",
    "issues": []
  }
}
```

## provenance

至少记录：

- `source_type`
- `source_id`
- `as_of`
- `confidence`
- `fields`

允许的 source_type：

- USER_EXACT
- USER_ESTIMATE
- EXTERNAL_PRIMARY
- EXTERNAL_SECONDARY
- MODEL_ASSUMPTION
- DERIVED_REFERENCE_ENGINE
- DERIVED_SECONDARY_CHECK

---

# 2. 双重计算

关键确定性计算至少具备两种检查方式之一：

## A. 主计算 + 独立公式复算

例如房贷月供：

- 主：Reference Engine
- 副：独立公式复算

## B. 恒等式/不变量

例如：

`net_worth = total_assets - total_debt`

`post_purchase_liquid_assets = pre_liquid_assets - cash_outlay`

`replacement_spread = target_home_price - old_home_price`

如果违反不变量：

`integrity.status = FAIL`

不得继续向 Recommendation Gate 传播。

---

# 3. 数值容差

绝对金额：

- 小额：允许极小舍入误差；
- 大额：默认相对误差 ≤ 0.5%；
- 关键债务本金/资产余额：如用户给精确值，要求精确一致。

比例：

- 默认相对误差 ≤ 1%。

超过容差：

- `WARN`：轻微、可能来自舍入或估计；
- `FAIL`：方向性或结构性错误。

---

# 4. Source Consistency

如果同一事实有多个来源：

优先级：

1. 用户最新明确输入；
2. 官方/第一方当前来源；
3. 用户估计；
4. 第二方当前来源；
5. 模型假设。

但“优先级”不代表自动忽略冲突。

例如：

- 用户说房子能卖350万；
- 三个最近成交参考集中在320—330万；

应标记：

`SOURCE_CONFLICT`

并采用：

- 用户估计：情景上界；
- 外部成交：当前基准；
- 推荐做敏感性分析。

---

# 5. Freshness

外部事实必须有 `as_of`。

典型 freshness：

- 学区/入学政策：每次重大决策前重新确认；
- 当前贷款产品：执行前重新确认；
- 房价/租金：买卖执行期应使用近期数据；
- 税费政策：执行前重新确认。

过期事实不自动删除，而是：

`status = STALE`

如果结果依赖该事实：

Recommendation Gate 至少降为 `CONDITIONAL_PASS`。

---

# 6. State Consistency

新解析出的家庭状态必须与旧 Context Capsule 比较。

如果出现大幅变化但用户未明确说明：

例如：

- 金融资产 100 万 → 10 万；
- 房价 350 万 → 550 万；
- 家庭收入 63 万 → 630 万；

触发：

`POSSIBLE_PARSE_ERROR`

先确认/回滚，不直接覆盖 source of truth。

---

# 7. Semantic Sanity Checks

不仅验证结构，还验证“结果合理性”。

例如：

## 住房
- 买后流动资产不得高于买前流动资产（除非同时有资产出售净流入）；
- 买房总现金需求不得为负；
- 若旧房和目标房都已给出，置换价差必须可计算；
- 若终局房标记不可出售，不能把其净值计入职业转型可动用资产。

## 融资
- 续贷额度下降时 refinance gap 不得下降；
- 无法续贷情景下已确认续贷额必须为 0；
- 合规状态未确认时，不能把该融资写成“确定可执行”。

## 职业
- 主收入下降后，家庭稳定收入不能上升，除非有新收入来源；
- 副业从未验证变为稳定12个月后，职业自由度可改善，但仍需压力情景。

## 教育
- HIGH 情景支出不得低于 MID；
- MID 不得低于 BASE。

---

# 8. Quarantine

Integrity FAIL 的结果不进入后续模型。

状态：

`QUARANTINED`

例如：

```json
{
  "step": "HOUSING_ANALYSIS",
  "status": "QUARANTINED",
  "reason": "replacement_spread formula mismatch",
  "last_good_state": "BASELINE_CALCULATE"
}
```

后续处理：

1. 修复输入；
2. 重跑当前 Step；
3. 通过后再继续。

---

# 9. Rollback

运行时保存每个 COMPLETE Step 后的 snapshot。

如果后续发现上游输入错误：

例如：

> 目标房其实是450万，不是550万。

系统应：

1. 更新 STATE_BUILD；
2. 标记受影响的下游步骤 `STALE`；
3. 回滚到最近合法节点；
4. 重新执行：
   - Housing
   - Stress
   - Options
   - Gate

无需重跑与房价无关的父母养老分析。

---

# 10. Dependency Graph

每个 derived result 应知道依赖：

```text
target_home_price
→ replacement_spread
→ post_purchase_liquid_assets
→ housing_freedom
→ stress_test
→ option_rank
→ recommendation
```

字段变化后，通过 dependency graph 只 invalidates 相关节点。

---

# 11. Confidence

不要只有“模型很自信”。

Result confidence 来自：

- 输入质量；
- 来源新鲜度；
- 是否有独立复算；
- 是否存在来源冲突；
- 是否依赖未来假设。

参考：

### HIGH
用户精确输入 + 确定性计算 + 交叉验证通过。

### MEDIUM
存在用户估计或合理区间，但方向稳定。

### LOW
高度依赖未来政策、市场、职业或未验证融资。

Gate 不把 LOW 自动阻塞，但必须让最终文案条件化。

---

# 12. Integrity Gate

在 Recommendation Gate 前增加：

`INTEGRITY_GATE`

必须确认：

- 无 FAIL；
- 无 QUARANTINED 关键 Step；
- 所有关键确定性数字 cross-check 通过；
- 关键外部事实 freshness 可接受或已条件化；
- 无未解决 source conflict；
- 无 possible parse error。

状态：

- PASS
- CONDITIONAL_PASS
- BLOCKED

Recommendation Gate 只能在 Integrity Gate 之后运行。

---

# 13. Auditability

Execution Ledger 继续保留“做了什么”。

Integrity Ledger 额外保留：

- 哪些值被交叉验证；
- 哪些值冲突；
- 哪些值被回滚；
- 哪些来源被判定过期；
- 哪些结果被隔离。

这不是隐藏推理链，而是结构化审计记录。

---

# 14. 目标

v1.1：

> 不允许 Agent 乱走流程。

v1.2：

> 即使按流程走，错误结果也尽量不能穿透到最终建议。
