# GitHub 发布检查清单

## 发布前

- [ ] 确定 GitHub 仓库名，推荐 `family-freedom-planner`
- [ ] 把 `INSTALL_PROMPT.md` 中的 `OWNER` 替换成真实 GitHub 用户名/组织名
- [ ] 决定正式开源许可证；当前包里的 Apache-2.0 是开发阶段默认建议，不应在未确认商业策略前视为最终法律选择
- [ ] 运行本地测试：

```bash
python -m unittest discover -s skills/family-freedom-planner/tests -p 'test_*.py'
```

- [ ] 如已安装 Agent Skills reference validator，再运行：

```bash
skills-ref validate skills/family-freedom-planner
```

## 发布后验证

用一个全新 Agent 会话，把 `INSTALL_PROMPT.md` 的“通用版”原样发给 Agent，验证：

1. Agent 能找到 `skills/family-freedom-planner/SKILL.md`；
2. 不会一次加载全部 references；
3. 首次交互使用“复制一段话、替换数字”的问诊；
4. 用户写“不知道”时仍能先给第一版诊断；
5. 房产问题会读取 `housing.md`；
6. 融资问题会读取 `financing.md`；
7. 确定性数学可以运行 reference engine；
8. 不支持 Skills 的 Agent 至少能按 README 的 fallback 直接读取执行。

## GitHub 首页最重要的 CTA

不要让用户先看技术架构。

首页第一屏应让人看到：

> 把这个仓库地址和下面一句话发给你的 AI，就可以开始。

然后直接给 Copy-to-Agent Prompt。
