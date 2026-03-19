Run the test suite for the infra codebase.

Usage: `/test [unit|integration|all]` (default: unit)

Steps:
1. Parse the argument to determine scope.

**Unit tests** (fast, no cloud calls):
```
python -m pytest tests/unit/ -v --tb=short
```

**Integration tests** (deploys real infra — confirm before running):
- Warn: "Integration tests will deploy real cloud resources and may incur costs."
- Ask for explicit confirmation before proceeding.
```
python -m pytest tests/integration/ -v --tb=short -s
```

**All**:
- Run unit first, then ask before running integration.

2. Report: tests passed / failed / skipped, and show any failures with full tracebacks.
3. On failure: suggest whether the issue is in infra logic (unit) or cloud config (integration).
