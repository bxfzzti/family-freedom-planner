<div align="center">
<img src="site/icon.svg" width="72" alt="买房小账本">

# 买房小账本

**算清首付、月供，和买房后的生活。**

免费开源的买房决策工具。打开网页就能算商业贷、公积金和组合贷，比较不同首付，看看收入变化后还能留下多少现金。

[打开计算器](https://bxfzzti.github.io/family-freedom-planner/) · [配套 AI Skill](#让-ai-帮你做深入分析) · [安装说明](INSTALL_PROMPT.md)

无需登录 · 浏览器本地计算 · Apache-2.0
</div>

![买房小账本网页](site/preview.jpg)

## 可以算什么

| 你关心的问题 | 小账本提供什么 |
| --- | --- |
| 每月要还多少？ | 商业贷款、公积金贷款、组合贷；等额本息与等额本金 |
| 首付多付10万值不值？ | 并列比较首月还款、买后现金和全期利息 |
| 装修完手里还剩多少钱？ | 从现金扣除首付、全部交易税费、装修与家具家电 |
| 收入下降之后呢？ | 正常、自定收入降幅、零收入三种情景的36个月现金变化 |
| 怎么和家人一起商量？ | 下载包含输入条件、结果及假设的文本摘要 |

首付、利率、现金底线由你填写。工具呈现取舍，不根据统一月供比例替你判断“可以买”。

## 打开就能用

访问 **[买房小账本](https://bxfzzti.github.io/family-freedom-planner/)**，将虚构示例替换成自己的数字。

1. 填房价、首付、已经到账且可动用的现金，以及交易和装修费用。
2. 填银行确认的贷款利率、期限、公积金额度，选择还款方式。
3. 填买房后的税后月收入和其他月支出，比较首付与收入变化。

金额字段用**万元**，利率用**年利率百分数**。其他月支出不含本次新房贷，仍需包含其他债务还款。准备提取但未到账的公积金不直接算作现金。

网站适配手机浏览器；目前是网页工具，**尚未发布微信小程序**。

## 数字怎么算

- 等额本息使用标准月度摊还公式；等额本金逐月按剩余本金计息。组合贷分别计算后相加。
- 买后现金 = 已到账可用现金 − 首付 − 全部交易税费 − 装修家具家电。
- 未来现金逐月加入收入、扣除其他支出与实际月供；贷款到期后停止扣款。
- 网页假定利率固定、其他收支固定、投资收益为0；不模拟调息、提前还款、额外大额支出和月内支付顺序。
- 利率、额度、首付比例及税费须按实际审批和当地规则确认。示例利率不代表当前政策；现金不足会显示资金缺口。

网页是独立的条件测算器，不声称执行了配套 Skill 的完整家庭规划校验。想进一步考虑置换时序、孩子上学和职业变化，可以使用下面的 Skill。

## 让 AI 帮你做深入分析

复杂问题可以交给配套的家庭重大决策 Skill，例如：

> 想换一套离公司近的房子，但担心以后收入下降。首付应该多付一点，还是多留一点现金？

复制给支持读取仓库和执行脚本的 Agent：

```text
请安装或加载“买房小账本”配套的 family-freedom-planner Skill：
https://github.com/bxfzzti/family-freedom-planner
技能路径：skills/family-freedom-planner

请完整读取 SKILL.md，说明是否持久安装、是否可以执行脚本。
复用我提供的已知信息，每轮最多补充三个关键项。
帮我比较首付、买后现金、收入变化与生活目标，不直接套统一比例。
```

[完整安装与验收说明](INSTALL_PROMPT.md)。本轮读取不等于已安装；外部 AI 平台可能自行收费。

项目原名 Family Freedom Planner / 家庭重大决策规划助手。现在对外以“买房小账本”聚焦买房场景；仓库 URL、Skill 标识和安装目录继续保留，已有用户无需迁移。底层仍支持教育、职业、债务和养老等关联分析。

## 隐私与开放

网页没有账户、付费档位、广告、分析追踪、数据上传或自动持久化。刷新页面恢复虚构示例，主动下载的摘要由你保管。托管服务可能保留普通访问日志，家庭金额不发送到服务端。

源代码、网页计算器和 Skill 均以 [Apache-2.0](LICENSE) 开放。家庭上下文和规划文件保持私有，详见 [PRIVACY.md](PRIVACY.md)。

## 开发与验证

纯静态网站，无需安装前端依赖：

```bash
python3 -m http.server 8765 --directory site
# 打开 http://localhost:8765
node --test site/tests/*.test.mjs
```

配套 Python Skill 使用标准库：

```bash
python3 -m unittest discover -s skills/family-freedom-planner/tests -p 'test_*.py'
python3 skills/family-freedom-planner/scripts/check_installation.py
python3 skills/family-freedom-planner/scripts/demo_controlled_run.py
```

网页与 Skill 分别测试。Skill v1.5 的175项单元测试及10例实际对话证据见 [QA报告](QA_REPORT.json) 和 [发布验收](docs/release-verification-v1.5.md)；38个benchmark检查覆盖结构，不代表38次模型实测。网页计算测试见 [site/tests](site/tests)。

```text
site/                             网页、独立计算模块及测试
skills/family-freedom-planner/    Python Skill、脚本、参考资料、示例和评测
.github/workflows/               Python校验和网页发布
docs/                           设计与版本验收记录
```

视觉表达参考 [Aerial 网站](https://aerial.qust.me/) 的简洁产品介绍方式。本项目页面、图标和计算器独立实现，不复用其图片或产品代码。
