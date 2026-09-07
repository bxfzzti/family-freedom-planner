# v1.2 Result Integrity Edition

v1.1：保证流程不乱走。  
v1.2：保证错误结果尽量不能穿透到最终建议。

## 新增

- Result Envelope
- Provenance
- 双重计算 / 恒等式 Cross-check
- Source Consistency
- Freshness
- Semantic Sanity Checks
- QUARANTINED 状态
- Rollback / STALE
- Dependency Graph
- Integrity Gate
- Integrity Ledger
- Parse-error anomaly detection

## Gate 顺序

```text
Workflow Validators
→ Integrity Gate
→ Recommendation Gate
→ Finalize
```

任何关键结果 integrity FAIL：

```text
QUARANTINED
→ BLOCKED
→ 修复
→ 重跑
```

而不是继续生成推荐。
