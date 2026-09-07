# AGENTS.md

This repository contains a portable Agent Skill.

If asked to use, install, review, or test the Family Freedom Planner:

1. Read `skills/family-freedom-planner/SKILL.md`.
2. Do not preload every reference file.
3. Load only the referenced domain files required by the user's task.
4. Use `scripts/family_freedom_engine.py` for deterministic arithmetic when useful.
5. Run tests before modifying the skill:
   `python -m unittest discover -s skills/family-freedom-planner/tests -p 'test_*.py'`
6. Preserve the zero-friction intake: users should not be forced to fill a long form.
7. Keep the main `SKILL.md` thin; move detailed domain rules into `references/`.
8. Do not turn market scenarios into predictions.


## v1.1 Mandatory execution control

For material family decisions, if code execution is available:

1. Initialize a run with `workflow_orchestrator.py`.
2. Ask the orchestrator for legal next steps.
3. Do not mark steps complete without passing validators.
4. Do not manually skip an applicable domain step.
5. Run `RECOMMENDATION_GATE`.
6. Do not produce a definitive recommendation if the gate is BLOCKED.
7. For CONDITIONAL_PASS, make all unresolved external-fact constraints explicit.

The orchestrator is the control plane, not optional documentation.


## v1.2 Mandatory integrity control

For material decisions:

1. Do not treat a completed step as trustworthy until integrity checks pass.
2. Record provenance for critical inputs and external facts.
3. Use deterministic cross-checks for critical arithmetic.
4. If integrity status is FAIL, quarantine the result and do not continue.
5. Run `INTEGRITY_GATE` before `RECOMMENDATION_GATE`.
6. If an upstream input changes, invalidate and recompute affected downstream results.
