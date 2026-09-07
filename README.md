# 家庭自由度规划师 / Family Freedom Planner

**v1.2.0 · Execution-Controlled + Integrity-Checked Agent Skill**


**别焦虑，把不可控的未来，变成可判断的条件。**

这是一个可分发的 Agent Skill，用于家庭重大决策：

- 买房、卖房、租房、置换；
- 学区与孩子教育；
- 一方脱产；
- 35—45岁职业转型；
- 高收入安全窗口下降；
- 按揭、抵押融资、提前还贷；
- 城市迁移和降低工作强度。

它不替你预测未来，而是把未来拆成条件、现金流、Deadline 和备选方案。

## 最简单的使用方法

把本仓库地址复制给你的 Agent，再把下面这句话发给它：

```text
请安装或加载这个 GitHub 仓库里的 family-freedom-planner Agent Skill。
Skill 路径是 skills/family-freedom-planner。

如果你的环境支持 Agent Skills，请把它安装到你的 Skills 目录；
如果不支持自动安装，就直接阅读 SKILL.md，并按需读取 references/ 和运行 scripts/。

安装/加载后，先使用它的首次问诊先根据我的一句自然语言问题自动选择相关模块，并自动预填已经知道的信息；不要让我自己研究模块，也不要让我填复杂表格。
```

更完整的复制话术见 [`INSTALL_PROMPT.md`](INSTALL_PROMPT.md)。

## 仓库结构

```text
.
├── README.md
├── INSTALL_PROMPT.md
├── AGENTS.md
├── LICENSE
└── skills/
    └── family-freedom-planner/
        ├── SKILL.md
        ├── references/
        ├── scripts/
        ├── assets/
        ├── examples/
        ├── evals/
        └── tests/
```

`SKILL.md` 保持为薄入口；详细知识按需放在 `references/`。

## 给支持 Agent Skills 的客户端

技能目录：

```text
skills/family-freedom-planner
```

符合 Agent Skills 的基本结构：

- `SKILL.md`：必需；
- `scripts/`：确定性计算；
- `references/`：按需知识；
- `assets/`：schema；
- `examples/`：示例；
- `evals/` / `tests/`：回归测试。

## 本地测试

```bash
python -m unittest discover -s skills/family-freedom-planner/tests -p 'test_*.py'
```

## 为什么不是 API-first

这套项目首先是一份**可移植、可版本控制、可被 Agent 读懂和执行的能力包**。

对个人用户，最自然的入口通常是：

```text
GitHub Repo → 给自己的 Agent → Agent 安装/读取 Skill → 开始使用
```

API 可以以后作为企业集成选项，而不是使用本项目的前提。

## License

当前开发包默认使用 Apache-2.0，便于公开分发与二次集成。正式发布前可按项目商业策略调整。


## v0.7.1：自适应首次问诊

首次问诊不再假设所有用户都有同样的问题。

使用方式：

```text
基础主干
+
住房 / 教育 / 职业 / 脱产 / 融资 / 父母 / 迁移 / 投资
中选择 1—3 个模块
```

例如：

- 换房：基础 + 住房
- 学区换房：基础 + 住房 + 教育
- 40岁职业转型：基础 + 职业
- 买房后离职：基础 + 住房 + 职业
- 配偶脱产 + 房贷：基础 + 脱产 + 融资

Agent 应根据用户已经说出的内容自动推荐模块，而不是把全部模块都抛给用户。


## v0.8：一句话开始

用户现在可以只说：

```text
我38岁，两个孩子，想换房，但担心40岁以后工作不稳。
```

Agent 自动识别：

```text
住房 + 职业
```

如果孩子入学会直接影响换房，再自动加入：

```text
教育
```

随后生成只包含相关缺失项的个性化模板。

原则：

> 用户负责说问题，Agent 负责决定该问什么。


## v0.9：不是每次都重新问诊

第一次：

```text
一句话 → 个性化首次问诊 → 第一版家庭状态
```

以后：

```text
“这次变了什么？”
→ 更新 family-context.json
→ 只重算受影响结论
```

例如用户半年后只说：

```text
旧房现在大概只能卖335万了，
但是我们把目标房预算从500万降到了430万，
金融资产现在有125万。
```

Agent 不再重新询问年龄、孩子和全部收入支出，而是直接说明：

- 哪几个数字变了；
- 哪些自由度被改善/恶化；
- 哪条旧建议需要撤销或更新。

### 跨 Agent 携带

用户可以把自己的 `family-context.json` 放进个人 Agent workspace 或私有 GitHub 仓库。

换 Agent 时：

```text
先读取我的 family-context.json，
再使用 family-freedom-planner 分析这次变化。
```

这样家庭规划上下文可以跟着用户走，而不是跟着某一个 App 走。


## v1.0 Reliability

这个版本不再以“功能更多”为目标，而以“面对不同家庭不套错模板”为目标。

当前 benchmark：

- 38 个案例
- 30 个标准场景
- 5 个 counterfactual
- 3 个 invariance
- 覆盖 10+ 风险类型

运行：

```bash
python skills/family-freedom-planner/scripts/validate_benchmark.py \
  skills/family-freedom-planner/evals/benchmark_cases.json
```

详细评估规则见：

```text
skills/family-freedom-planner/references/reliability-evals.md
skills/family-freedom-planner/evals/RUBRIC.md
```


## v1.1 Execution Control

v1.1 增加 Control Plane。

```text
LLM
 ↓
workflow_orchestrator.py
 ↓
合法下一步
 ↓
工具 / 计算 / 外部事实
 ↓
Validator
 ↓
Recommendation Gate
 ↓
Final Answer
```

### 查看合法下一步

```bash
python skills/family-freedom-planner/scripts/workflow_orchestrator.py \
  next run.json
```

### 非法跳步

会直接返回 ERROR，而不是继续执行。

### Recommendation Gate

只有：

```text
PASS
或
CONDITIONAL_PASS
```

才允许 FINALIZE。

详细说明：

`skills/family-freedom-planner/references/execution-control.md`


## v1.2 Result Integrity

v1.1 防止“跳步骤”。

v1.2 再加一层：

```text
Step Output
↓
Independent Cross-check
↓
Source / Freshness Check
↓
Semantic Sanity Check
↓
Integrity Gate
↓
Recommendation Gate
```

例如：

- 置换价差公式不一致 → FAIL
- 终局房净值被错误计入可迁移资产 → FAIL
- “无法续贷”情景却仍然填写可续额度 → FAIL
- 教育 HIGH 情景低于 MID → FAIL
- 外部政策未验证 → CONDITIONAL_PASS
- 上游输入修正 → 下游结果 STALE 并定向重跑
