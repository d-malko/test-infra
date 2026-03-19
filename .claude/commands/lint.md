Run all linters and type checkers for the infra codebase.

Use **parallel subagents** to run checks simultaneously — do not wait for one to finish before starting another.

Launch 2 subagents in parallel:

**Subagent 1 — ruff (lint + format):**
```
ruff check .
ruff format --check .
```

**Subagent 2 — mypy (type checking):**
```
mypy infra/ __main__.py --strict
```

Once both complete:
1. Show results grouped by tool — failures first.
2. If ruff failed, offer to auto-fix: `ruff check --fix .` and `ruff format .` (safe rewrites only).
3. mypy errors must be fixed manually — explain each one concisely with the affected file and line.
4. If both pass, confirm clean.
