Run the test suite for the infra codebase.

Usage: `/test [unit|integration|all]` (default: unit)

---

**Unit tests** (fast, no cloud calls):

Use an **Explore subagent** to discover all test modules under `tests/unit/`, then run them in **parallel subagents** — one per module — and aggregate results.

```
python -m pytest tests/unit/<module>/ -v --tb=short
```

Aggregate: total passed / failed / skipped across all modules. Show full tracebacks for any failures.

---

**Integration tests** (deploys real infra):

- Warn: "Integration tests will deploy real cloud resources and may incur costs."
- Ask for explicit confirmation before proceeding.
- Run sequentially (not parallel — stacks share cloud state):

```
python -m pytest tests/integration/ -v --tb=short -s
```

---

**All**:
- Run unit (parallel) first.
- Show unit results.
- Then ask before running integration.

---

On failure: use `devops-systematic-debugging` skill to trace root cause — never guess.
