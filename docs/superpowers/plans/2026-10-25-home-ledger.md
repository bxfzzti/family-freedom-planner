# 买房小账本 Implementation Plan

Goal: 将用户确认的买房工具方向落地为免费公开网站和清晰的GitHub入口。用户提出新名“买房小账本”，采用为产品品牌。

Architecture: site/独立静态HTML/CSS/ES modules；纯本地算术，无服务器、追踪、账户和数据持久化。原Python Skill保持兼容；网页不声称运行完整规划门禁。使用GitHub Pages公开同仓库网站。

Tech stack: browser JavaScript, Node built-in test runner, existing Python unittest, GitHub Pages.

## Design

浅灰底、黑色大标题、蓝色操作按钮、大留白和细边框；参考Aerial的产品叙事，不复用其图像或代码。首屏主题“买房之前，把账算明白。” 下方即工作计算器，桌面双栏、手机单栏。提供商业贷/公积金/组合贷，等额本息/等额本金；列月供、利息、剩余现金、收入下降后的现金变化。首付候选并列比较，不自动判定最优。字段单位、假设及费用范围明确，示例均虚构。

## Tasks

- [ ] site/calculator.mjs: 按月摊还、组合贷款与初始资金、收支压力情景。校验有限非负数、整月期限及资金闭合。负现金显示缺口。
- [ ] site/tests/calculator.test.mjs: 用零利率、已知月供、还本恒等式、组合贷、无效数和短期限验证；与Python按揭函数交叉比较。
- [ ] site/index.html, styles.css, app.mjs: 响应式页面；可编辑字段、结果、首付比较、情景曲线、下载测算摘要、恢复虚构示例。
- [ ] README.md: 产品名称、网页入口、截图、用途、算法边界、Agent安装、开发与测试。保留Apache-2.0和原安装路径。
- [ ] .github/workflows/pages.yml: 检查后上传静态站，部署Pages；仓库About说明同步买房方向。
- [ ] 浏览器验收桌面/手机、表单修改与错误处理，Python及网页计算测试；发布后核对在线内容。
