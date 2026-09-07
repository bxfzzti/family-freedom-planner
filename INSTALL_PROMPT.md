# Copy-to-Agent 安装话术

把仓库 URL 中的占位符换成真实 GitHub 地址即可。

## 通用版：推荐

```text
请安装或加载这个 GitHub 仓库里的 Agent Skill：

https://github.com/OWNER/family-freedom-planner

Skill 路径：
skills/family-freedom-planner

Skill 名称：
family-freedom-planner

如果你的环境原生支持 Agent Skills，请把这个 Skill 安装到你的 Skills 目录并在以后相关任务中自动使用。

如果你的环境不能自动安装 Skill，请直接读取：
skills/family-freedom-planner/SKILL.md

然后只在任务需要时继续读取它引用的 references/、examples/，或运行 scripts/family_freedom_engine.py；不要一次性加载所有文件。

以后当我讨论家庭资产、买房卖房、房产置换、孩子教育、一方脱产、职业转型、降低工作强度、提前还贷、抵押融资或家庭长期规划时，优先使用这个 Skill。

现在先按这个 Skill 的“自然语言首次问诊”开始：先理解我一句话描述的问题，自动选择最多 3 个相关模块并预填已知信息，只让我补真正缺失的关键项。不要让我研究模块或填复杂表格。
```

## 极简版

```text
安装/加载这个 Agent Skill：
https://github.com/OWNER/family-freedom-planner
路径 skills/family-freedom-planner

以后我的家庭住房、教育、职业和资产重大决策优先用它。
现在按 SKILL.md 的首次问诊开始。
```

## 已经支持 GitHub Skill Installer 的 Agent

```text
请从 GitHub 安装 OWNER/family-freedom-planner 仓库中
skills/family-freedom-planner 路径的 Skill。
安装后使用 family-freedom-planner 开始首次问诊。
```

## Agent 不支持 Skills，但能读 GitHub

```text
把这个 GitHub 仓库当成一个可执行的专家工作流。
先读 skills/family-freedom-planner/SKILL.md。
严格遵守它的触发条件和核心原则；
只在需要时读取 references/ 和 examples/；
确定性计算优先运行 scripts/family_freedom_engine.py。
```


## 已有家庭规划数据时

```text
请先加载 family-freedom-planner。

如果我提供了 family-context.json，
把它视为当前家庭规划的显式 source of truth。

不要重新首次问诊。
先识别我这次提供的新信息和旧状态相比发生了什么变化，
只重算受影响的指标和建议。
```
