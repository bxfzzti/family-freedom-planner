# 安装与首次使用

将下面整段复制给能访问 GitHub 的 Agent。不同客户端的安装位置和生效方式不同，以实际安装结果为准。

```text
请安装这个仓库中的 family-freedom-planner Skill：
https://github.com/bxfzzti/family-freedom-planner
目录：skills/family-freedom-planner

如果支持持久安装，请使用当前客户端的安装机制安装整个 Skill 目录。
若不能安装但能读取仓库，请读取 SKILL.md，并按需读取其 references 或运行 scripts。
请明确告诉我：是已持久安装还是仅本轮读取；脚本能否运行；当前事实能否联网核实。
如果可以执行Python，请在安装后的技能目录运行 python scripts/check_installation.py，并报告结果。
不要把仅本轮读取说成已安装，不要在未验证时声称以后会自动调用。

下面是虚构的启动测试，不是我的家庭资料：
“我30岁，两个孩子，想换房，但担心35岁后工作不稳。”
请按 Skill 回答第一轮；保留已知信息，说明待验证矛盾，最多问三个关键项。
```

## 安装验收

技能自检只验证分发文件与本地计算，不证明客户端已自动发现它。若用户希望验证新会话自动调用，还需在新会话实际触发；不要把自检 PASS 当成自动调用已验证。无法运行Python时，保留“脚本未验证”状态，仍可按指令做问诊。

- 已安装：报告实际安装位置，以及客户端是否需要刷新或新开会话；只陈述已验证的状态。
- 仅本轮读取：可以继续本轮使用，新会话可能需要再次提供入口。
- 脚本不可运行：明确计算未由脚本验证，避免给出伪精确购买上限。
- 无法访问仓库：不要凭名称假装加载；需由用户提供完整技能包或可访问内容。
- 首轮不重复问年龄和孩子数量，不把35岁当成确定失业期限，不直接劝买卖，不发长表。
- 启动测试中的家庭信息不得保存为用户事实；测试完成后从用户真实问题开始。

## 已有规划

```text
请加载 family-freedom-planner，读取我提供的 family-context.json。
只提取这次变化并重算受影响结果，不重新首次问诊。
保留其中的事实/估计/假设标签。先说明旧结论如何受影响。
```

家庭资料默认留在用户指定的私人位置，不随 Skill 提交到公开仓库。

## v1.4 旧上下文升级

旧的 `schema_version: 0.9` 文件先运行：

```bash
python scripts/migrate_context.py family-context.json
```

迁移结果会保留原数值，并把无法确定的税前税后、支出口径和金融资产组成列为待确认。确认后再运行：

```bash
python scripts/validate_family_state.py family-context-v1.4.json --calculation-ready
```

未通过 calculation-ready 时继续问诊，不得把未知值改成0后强行计算。v1.3及更早的 run.json 不能继续执行，需要从确认后的家庭状态重新初始化。
