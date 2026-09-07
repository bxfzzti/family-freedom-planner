# Contributing

欢迎提交：

- 新的匿名家庭案例；
- 新的 counterfactual / invariance eval；
- 计算 bug；
- 本地化参考；
- 更好的首次问诊体验；
- Agent 兼容性修复。

## 新案例要求

不能包含真实可识别家庭信息。

每个 eval case 至少包含：

- prompt
- expected_modules
- must
- must_not
- risk_tags
- difficulty

## 修改核心行为前

请运行：

```bash
python -m unittest discover -s skills/family-freedom-planner/tests -p 'test_*.py'
python skills/family-freedom-planner/scripts/validate_benchmark.py \
  skills/family-freedom-planner/evals/benchmark_cases.json
```

任何修改不得破坏：

- zero-friction intake
- progressive intake
- replacement spread
- refinance failure test
- Context Capsule
- Delta Replan
- no-prediction principle
