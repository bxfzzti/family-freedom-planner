# 融资与债务

## 普通按揭

至少计算：

- 月供；
- 年度现金流；
- 高收入失效后覆盖率；
- 买后剩余流动资产。

等额本息可用：

`python scripts/family_freedom_engine.py mortgage --principal ... --annual-rate ... --years ...`

## 抵押贷 / 经营性抵押融资

不得只看当前低利率或低月供。

必须检查：

1. 名义债务余额；
2. 当前年度现金支出；
3. 期限；
4. 续贷频率；
5. 重新审批；
6. 资质要求；
7. 抵押物估值；
8. 利率重定价；
9. 用途与合规；
10. 无法续贷时如何处理本金。

## 四档压力测试

### A 正常续贷
利率、额度基本稳定。

### B 利率上升
例如 +1—2个百分点。

### C 额度下降
例如300万只能续200万，测试100万本金缺口。

### D 无法续贷
核心问题：

> 不出售长期自住房、不借紧急高息债，家庭能否处理到期本金？

如果不能，再融资安全度不得高。

## 再融资缺口

`安全可偿债资金 = 低风险资产 - 应急金底线 - 未来24个月确定资本支出`

`再融资缺口 = max(0, 到期本金 - 确认可续额度 - 安全可偿债资金)`

## 合规

不提供伪造经营用途、绕风控、虚假交易或违规改变贷款用途的方法。

无法确认合规时，标记 `REQUIRES_VERIFICATION`，并模拟普通按揭或自有资金备选。

## 普通长期按揭与续作融资分开处理

普通全额摊还、固定期限且明确无续贷/大额到期本金的按揭，续贷失败测试为“不适用”，不能伪报已测试。仍须核对本金、月供、利率与期限，测试收入下降和实际付款顺序。

向控制器提交 FINANCING_ANALYSIS 时，使用：

```json
{
  "nominal_principal_checked": true,
  "refinance_failure_tested": false,
  "refinance_required": false,
  "loan_structure": "FULLY_AMORTIZING_FIXED_TERM",
  "compliance_status": "REQUIRES_VERIFICATION",
  "results": {
    "balloon_payment": 0,
    "refinance_not_applicable_reason": "给定合同假设为全额摊还、无需续贷；真实合同执行前需核实"
  }
}
```

完整性检查可用 integrity_engine.validate("financing", data)，data 包含同样的 loan_structure/refinance_required，以及 principal、annual_rate、years、monthly_payment、balloon_payment=0。这会独立复算按揭月供，而不是把全部按揭本金假设为立即到期。

只要存在续作、授信重审或大额到期本金，仍须执行续贷失败测试。不清楚贷款结构时不能使用“不适用”；合同条件未核实保持条件化结论。

多方案时将每笔可比较贷款放入 `results.loans[]`，每项带对应 `option_id` 和完整月供/续贷复算输入。不能只检查最高或推荐方案；OPTIONS_VALIDATE会核对每个方案的融资与压力测试覆盖。
