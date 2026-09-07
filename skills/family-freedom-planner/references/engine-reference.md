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

## 原则

- 相同输入应得到确定性结果；
- 模型假设必须由Agent在用户可见层说明；
- 计算脚本不负责判断家庭偏好；
- 外部政策与价格不写死在脚本。
