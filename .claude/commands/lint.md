Run all linters and type checkers for the infra codebase.

Steps:
1. Activate the virtual environment if not already active.
2. Run in order — report failures but continue through all steps:
   ```
   ruff check .
   ruff format --check .
   mypy infra/ __main__.py --strict
   ```
3. If any step fails, show the errors grouped by tool.
4. Offer to auto-fix: `ruff check --fix .` and `ruff format .` (safe rewrites only).
5. mypy errors must be fixed manually — explain each one concisely.
