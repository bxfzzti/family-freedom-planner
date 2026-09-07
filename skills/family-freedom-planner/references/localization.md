# 外部事实与地区本地化

如果当前事实会显著改变推荐，且环境可联网/连接数据源，应获取最新信息。

## 必查类型

- 当前房贷/融资利率；
- 贷款产品现行条件；
- 房地产税费与交易规则；
- 学区/入学规则；
- 学位锁定/户籍/持有时间要求；
- 公办/民办/国际学校收费；
- 目标区域真实成交价与租金；
- 最新住房政策。

## 来源优先级

1. 政府、教育局、住建、统计等官方来源；
2. 银行/金融机构官方资料；
3. 学校官方资料；
4. 可靠成交数据；
5. 高质量媒体/研究；
6. 用户提供的中介/银行报价。

## 房价类型

区分：

- USER_EXPECTED_PRICE
- LISTING_PRICE
- RECENT_TRANSACTION_PRICE
- APPRAISAL_PRICE
- MODEL_SCENARIO_PRICE

挂牌价不是成交价。

只有用户估值时，使用 ±5% / ±10% 敏感性分析。

## 外部事实记录

重要事实应记录：

- value / range
- as_of
- source
- confidence
- affected_calculations
- refresh trigger

不要用全国平均值冒充用户所在地区的现实。
