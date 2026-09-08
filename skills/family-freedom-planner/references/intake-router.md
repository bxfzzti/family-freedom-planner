# Intake Router Rules

目标：从用户自然语言中选择最少但足够的问诊主题。

## 触发词仅作弱信号

不要只靠关键词；要结合语义。

### HOUSING_EXISTING
换房、卖房、房子跌了、学区房、改善、先卖后买、租两年、现有房贷

### HOUSING_FIRST_BUY
首套、第一次买房、一直租房、首付、可以买多贵

### EDUCATION
学区、孩子上学、幼儿园、小学、教育预算、国际学校、留学

### CAREER
大厂、裁员、离职、退休、自由职业、副业、降低工作强度；年龄本身不是职业风险信号

### SPOUSE_BREAK
全职带娃、不上班、辞职照顾孩子、脱产

### FINANCING
按揭、抵押贷、经营贷、续贷、提前还贷、利率、月供

### PARENT_CARE
父母养老、赡养、护理、医疗

### RELOCATION
回县城、回老家、换城市、国外、移居

### INVESTING
股票、基金、理财、投资亏损、资产配置

## 组合规则

### 换房 + 学区
HOUSING_EXISTING + EDUCATION

### 换房 + 职业风险
HOUSING_EXISTING + CAREER

### 学区 + 职业风险
EDUCATION + CAREER

### 买房 + 配偶脱产
HOUSING_EXISTING/HOUSING_FIRST_BUY + SPOUSE_BREAK

### 买房 + 抵押融资
HOUSING_EXISTING/HOUSING_FIRST_BUY + FINANCING

### 回小城市 + 离开高薪
RELOCATION + CAREER

### 综合问题
GENERAL + 最相关的两个领域

## 选择上限

首次最多 3 个领域。

如果 4 个以上都相关，优先：

1. 不可逆性最高；
2. Deadline 最近；
3. 现金影响最大。
