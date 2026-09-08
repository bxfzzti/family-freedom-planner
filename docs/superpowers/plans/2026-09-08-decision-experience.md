# Decision Experience Implementation Plan

**Goal:** 修复首次使用、事实口径和结果交付，提供可核验的对话评估。

**Architecture:** 沿用现有脚本与执行控制。问诊规则在 intent-to-intake.md 统一；输出规则在 output-contract.md 统一；安装与评估各自提供明确验收边界。

**Tech Stack:** Markdown、Python 标准库、unittest、GitHub Actions。

## Global Constraints

- 用户已批准按六项建议实施并继续改进；在本会话直接执行。
- 保留 family-freedom-planner 技术名称和已有工作流接口。
- 不把案例格式通过解释为 Agent 行为通过，不添加真实家庭数据。

## Task 1: 问诊与决策输出

- [x] 修改 SKILL.md、references/intent-to-intake.md、intake.md、output-contract.md、examples/personalized-intake-examples.md；统一三个独立信息项、保留原话口径与一页摘要。
- [x] 新建 references/decision-framing.md；明确目标、期限、代价和可逆试行进入方案比较。
- [x] 更新 INSTALL_PROMPT.md、README.md；真实 URL、能力确认、合成测试提示。
- [x] 搜索旧的长表指令和税后自动推断，排除相互矛盾。

## Task 2: 路由与评估工具

- [x] 为年龄误触发、首购学区房误路由、非法模块上限编写回归测试，运行确认失败，再修 intake_router.py。
- [x] 添加对话案例与 evaluate_dialogues.py：输入案例、实际 transcript 和逐项审阅结果；未知或未审阅返回 INCOMPLETE，失败返回 FAIL；完整证据方可 PASS。
- [x] 测试缺失回答、空审阅、伪通过、真实失败、重复记录、过期审阅和成功报告，接入单元测试。

## Task 3: 验收与下一轮

- [x] 运行全部 unittest 和 benchmark schema 校验，检视文档引用及 git diff。
- [x] 使用虚构数据完成10个独立上下文实际对话案例并逐项审阅；准确说明同一模型、非跨模型认证的边界。
- [x] 根据发现作针对性修复；记录结果、版本和限制。
- [x] v1.3.0 已推送并回读 commit 7fa5f19b6f3e1bb6b62d30e934c1896f501629a1，GitHub CI 成功。

## 后续小版本

- [x] 为局部状态更新添加 update 模式，避免未提及字段被误判删除；补充7项回归测试，总计108项通过。
- [x] v1.3.1 已发布：6c76ce9abf6d44ec7aca07fa0e00d07439b3d515。远端干净下载副本通过108项测试、38例结构校验与两个计算演示；对应GitHub CI成功。
- [x] 在隔离目录用 Skill Installer 安装已发布版本，验证下载后的技能可独立运行。
- [x] 完成一例完整规划前向试用，复现普通按揭误要求续贷测试的阻塞；修复后重新初始化并完成全部门禁。
- [x] 增加控制器基线自行复算、融资领域匹配与安装自检，总计120项测试通过。
- [x] 发布v1.3.2代码提交510cec58b3657a835bb0f08e1d88b38e416a8a7d；远端全新隔离安装通过120项测试、自检和完整演示，对应GitHub CI成功。
