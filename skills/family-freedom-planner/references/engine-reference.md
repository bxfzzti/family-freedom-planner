# Reference Engine

`scripts/family_freedom_engine.py` 是标准库实现的确定性计算参考。

它不预测市场，不替代政策查询。

## 命令

### 按揭月供

```bash
python scripts/family_freedom_engine.py mortgage \
  --principal 1000000 \
  --annual-rate 0.03 \
  --years 30
```

### 家庭 Baseline

```bash
python scripts/family_freedom_engine.py baseline examples/sample_household.json
```

### 卖房租住等待

```bash
python scripts/family_freedom_engine.py sell-rent examples/sell_rent_case.json
```

### 再融资缺口

```bash
python scripts/family_freedom_engine.py refinance examples/refinance_case.json
```

输出均为 JSON。

金额单位默认“元”，利率使用小数，例如3% = `0.03`。

## 输入口径与缺失值

baseline 接受 examples/sample_household.json 的计算结构，不直接接受 family-context.json。
后者是跨会话摘要：Agent 必须确认口径、区分资产组成，再映射到计算结构；不能把“现金+金融资产”全部填进现金。

- income.stable_annual 为已确认的税后年收入对象；明确无收入时使用空对象。
- expenses.annual_total 为含债务实际还款的年总支出，不能再次扣同一房贷。
- assets.cash、low_risk_investments、investments、other_liquid 需明确数值；明确无该类资产填0，未知不填0。
- assets.real_estate、debts.items 需明确列表；明确无房或无负债用 []。
- high_risk_annual 是已计入收入中可能失效的部分，不能再加一遍；未知时依赖度返回 null。
- annual_mandatory 未知时暂用年总支出作为保守覆盖口径，并通过 mandatory_spending_basis 标出。
- 是否出售房产未确认时，房产锁定率返回 null；不默认房子可卖。
- other_non_liquid 缺省为0，若确有其他非流动资产但估值未知，应先补齐或明确只算已知资产范围。

缺失核心项、错误结构、负金额、布尔值或非有限数字会拒绝计算。命令行返回 JSON ERROR 和退出码2，不能把它包装成成功测算。

runway_months 是零收入下必要支出覆盖月数，不是失业情景的净缺口覆盖期，更不是“安全退休年限”。需要剩余收入、应急底线和一次性支出共同参与的压力覆盖，请用 decision_cashflow.py。

卖房租住、再融资示例中的数值均为明确输入：未知的税费、搬家费或可续额度不得默认为0，允许另设标注清楚的假设情景。卖房租住采用简化利息比较，不处理逐月本金摊还。

## 决策后的现金缓冲

```bash
python scripts/decision_cashflow.py examples/decision_cashflow_case.json
```

输入行动前可动用低风险资产、行动时净流入/支出、保留底线、模拟月数，以及三种情景的税后收入和包含房贷的总支出。changes 从指定月份开始替换年收入或年支出；one_off_expenses 计入当月，不能与 upfront_outflow 或年支出重复计数。无变动/一次性费用时明确给空列表。

输出首次跌破储备线与首次现金缺口月份、区间最低现金和期末现金。第0个月表示行动当时已出现缺口；null 表示本次模拟期限内未触线，不代表无限安全。保留底线不预先从账户扣除，防止被重复扣减。

示例里的20万元储备与三种收入路径都是虚构假设，不是推荐标准或未来预测。引擎不计投资回报，按月收支净额模拟，无法代表月内支付顺序；近期交易或贷款到期须另查实际付款时间。

## 使用原则

- 相同输入应得到确定性结果；
- 模型假设必须由Agent在用户可见层说明；
- 计算脚本不负责判断家庭偏好；
- 外部政策与价格不写死在脚本。
