Run a full audit of the infra codebase across three dimensions in parallel.

Usage: `/audit [best-practices|security|all]` (default: all)

Launch **3 parallel Explore subagents** simultaneously:

---

**Subagent 1 — Pulumi Best Practices audit:**
Scan all `.py` files in `infra/` and `__main__.py`. Apply `pulumi-best-practices` and `pulumi-component` skills. Report:
- Resources created inside `apply()` (forbidden)
- Missing `ResourceOptions(parent=self)` in ComponentResources
- Missing `register_outputs()` calls
- `.get()` calls on Outputs (forbidden)
- Missing type annotations on infra functions
- Naming violations (must follow `test-<env>-<purpose>`)
- Resources missing common tags

**Subagent 2 — Security audit:**
Scan all `.py` files in `infra/`, all `Pulumi.*.yaml` files, and `__main__.py`. Apply `senior-secops` skill. Report:
- Hardcoded secrets, tokens, passwords, or API keys
- Config values that should be secrets but aren't (`config.get()` vs `config.require_secret()`)
- Overly permissive IAM/RBAC policies
- Missing `additional_secret_outputs` on sensitive resource outputs
- Resources without deletion protection on stateful resources (DBs, storage)

**Subagent 3 — Code quality & structure audit:**
Scan all `.py` files. Report:
- Modules that are too large (>200 lines) and should be split
- Functions returning plain values instead of `pulumi.Output[T]`
- Missing `__init__.py` exports
- Dead code or unused imports
- Circular imports between infra modules

---

Once all 3 complete, aggregate into a single prioritised report:
- 🔴 Critical (security, broken dependency tracking)
- 🟡 Warning (best practice violations, missing tags)
- 🟢 Info (style, structure improvements)

Do not fix anything automatically — present findings and ask the user which to address first.
