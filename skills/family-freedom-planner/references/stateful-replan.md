# Stateful Replan：家庭状态持续更新

## v1.4 统一上下文

当前 `family-context.json` 是一个信封：顶层保存目标、假设、待确认问题和决策记录；`family_state` 使用 assets/family-state.schema.json 的统一结构。金额固定为人民币元，收入和支出固定为年度，收入明确 AFTER_TAX/BEFORE_TAX/UNKNOWN，年支出明确是否已包含债务还款。

每个已知关键金额在 `family_state.source_tags` 中按字段路径记录 source_type、as_of 和 confidence。上下文可包含未知值；交给计算引擎前必须通过：

```bash
python scripts/validate_family_state.py family-context.json --calculation-ready
```

旧0.9文件先迁移：

```bash
python scripts/migrate_context.py family-context-old.json
```

迁移不会把“现金+金融资产”当成现金，也不会猜税前税后。它写入 `unallocated_financial_assets`、`tax_basis=UNKNOWN` 和待确认问题，状态可继续问诊但不能直接测算。示例见 examples/family-context-v1.4-migrated.json。

下面的0.9结构仅用于说明旧格式和迁移来源，不是新建文件模板。

## 只说变化，不等于删除其他资料

两个完整上下文快照可用 state_diff.py 的默认 snapshot 模式比较。用户仅说“现金变成80万”时，用 --mode update 比较局部更新；未提及的收入、负债和目标必须保留。

```bash
python scripts/state_diff.py old-context.json partial-update.json --mode update
```

update 中的 null 表示该字段变为未知，不代表0或删除。数组为整组替换，不支持用半个孩子列表更新某一个孩子；需要先恢复完整列表。确实要删除字段时使用明确的完整新快照，并保留变更记录。空对象不清空已有组。

脚本只输出差异，不自动保存家庭资料；由 Agent 按用户授权的位置保存更新后的状态。贷款余额变化按债务处理，关键时间点变化按 Deadline 处理。原始事实与假设标签一起更新，不把只改金额当成已确认来源。

v0.9 解决的问题：

> 用户第二次、第三次来时，不应该重新做整套问诊。

规划是一个持续变化的家庭状态，不是一份一次性报告。

---

# 1. Family Context Capsule

每次完整分析后，可生成一份轻量的“家庭上下文胶囊”。

它只保存规划需要的信息，不保存身份证号、银行账号、详细地址、孩子姓名等敏感标识。

推荐文件：

```text
family-context.json
```

结构示例：

```json
{
  "schema_version": "0.9",
  "as_of": "2026-09",
  "household": {
    "adult_ages": [38, 36],
    "children_ages": [3, 1]
  },
  "income": {
    "stable_household_income_annual": 630000,
    "high_risk_income_annual": 500000,
    "high_income_deadline": "2030"
  },
  "expenses": {
    "annual_household_spend": 180000
  },
  "assets": {
    "cash_and_financial_assets": 1000000
  },
  "housing": {
    "primary_home_value": 3500000,
    "primary_home_debt": 1000000
  },
  "goals": [
    "解决孩子教育",
    "评估换房",
    "降低对高薪岗位依赖"
  ],
  "assumptions": [],
  "open_questions": [],
  "decision_journal": []
}
```

---

# 2. 第二次对话默认使用 Delta Intake

如果已经有 Context Capsule 或对话中已有完整家庭状态：

不要重新发送首次问诊。

先问/识别：

> “这次和上次相比，什么变了？”

用户可以直接说：

- “房子现在只能卖330万了。”
- “我老婆确定明年辞职。”
- “副业现在一年能做到10万。”
- “目标房预算从500万降到430万。”
- “贷款方案确认做不了了。”

Agent 应：

1. 提取变化；
2. 更新状态；
3. 找受影响的指标；
4. 重算；
5. 明确指出旧结论哪里变化。

---

# 3. Delta 类型

- `INCOME_CHANGE`
- `EXPENSE_CHANGE`
- `ASSET_CHANGE`
- `HOUSING_PRICE_CHANGE`
- `DEBT_CHANGE`
- `CAREER_CHANGE`
- `EDUCATION_CHANGE`
- `FINANCING_CHANGE`
- `PREFERENCE_CHANGE`
- `DEADLINE_CHANGE`
- `NEW_GOAL`
- `GOAL_REMOVED`

---

# 4. 影响传播

不要所有内容全部重算后只丢一个新报告。

需要告诉用户：

> 哪条变化 → 影响哪些指标 → 哪个旧结论需要修改。

例如：

```text
变化：
目标房预算从500万降到430万。

直接影响：
- 首付需求下降
- 买后金融资产提高
- 普通按揭余额下降

进一步影响：
- 流动性自由度上升
- 住房自由度上升
- 2030职业降档可行性提高

旧结论变化：
“必须依赖低息抵押融资” → “普通按揭也可能进入可接受区间”
```

---

# 5. 变化阈值

即使用户没有主动要求完整重算，发生以下情况应提醒重新规划：

- 稳定家庭收入变化 ≥10%
- 家庭支出变化 ≥10%
- 金融资产变化 ≥15%
- 旧房或目标房参考价变化 ≥5%
- 贷款利率变化 ≥1个百分点
- 续贷额度或期限变化
- 一方确定脱产/复工
- 教育路线发生重大变化
- 高收入安全窗口提前/延后 ≥1年
- 出现新的重大 Deadline

---

# 6. Decision Journal

每个重大决定记录：

```json
{
  "date": "2026-09",
  "decision": "暂不购买500万终局房",
  "status": "ACTIVE",
  "why": [
    "职业Deadline与入学Deadline重叠",
    "普通按揭下买后流动性不足"
  ],
  "assumptions": [
    "当前高薪可维持到2030",
    "两年内仍会解决学区"
  ],
  "revisit_if": [
    "目标房预算降至430万以内",
    "副业稳定达到15万/年",
    "低息合规融资确认可执行"
  ]
}
```

后续重算时：

- 若 `revisit_if` 被触发，主动提示旧决定应该复盘；
- 不把旧决定当永久真理。

---

# 7. 跨 Agent 携带

Family Context Capsule 是可移植的。

用户可以把：

```text
family-context.json
```

放在自己的：

- GitHub 私有仓库；
- Agent workspace；
- 本地文件夹；
- 支持文件记忆的个人 Agent 环境。

换一个 Agent 时，只需要告诉它：

> “先读取我的 family-context.json，再使用 family-freedom-planner。”

这样无需依赖某个中心化 API 或账号数据库。

---

# 8. 隐私原则

Context Capsule 默认不要包含：

- 姓名；
- 身份证号；
- 银行卡号；
- 精确住址；
- 公司内部机密；
- 孩子姓名；
- 医疗诊断细节。

只保存“决策所需的结构化事实”。

如公开 GitHub 仓库：

> 不应提交真实家庭 Context Capsule。

公开仓库只放匿名 examples。

---

# 9. Context Capsule 与 Agent Memory

如果 Agent 自身已经有可靠记忆能力：

- Capsule 仍可作为显式 source of truth；
- Agent Memory 用于便利；
- Capsule 用于可审计、可迁移、可版本控制。

若二者冲突：

1. 用户当前明确输入
2. 最新 Capsule
3. Agent Memory
4. 历史报告

---

# 10. Replan 输出

发生重要 Delta 后，优先输出：

### 这次变了什么
1—3条。

### 哪些数字受影响
表格或简表。

### 旧结论哪里需要改
明确撤销/上调/下调。

### 新安全线
如适用。

### 现在最值得做的下一步
最多3条。

不需要每次都重发完整家庭报告。
