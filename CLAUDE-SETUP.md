# Claude Code Setup — Deep Dive

This document explains the reasoning behind every tool, skill, command, and subagent pattern configured in this repo. Read it if you want to understand *why* things are set up the way they are.

For day-to-day usage see [README.md](README.md) and [CLAUDE.md](CLAUDE.md).

---

## Slash Commands

### `/setup`
New teammates shouldn't have to read docs to get started. `/setup` automates the full bootstrap: tool check with install instructions, `poetry install`, `pulumi login`, stack selection, and a live `pulumi preview` as credential verification. One command, ready to work.

### `/preview <stack>`
`pulumi preview` output is dense. This command parses it into a human-readable summary and — critically — runs an Explore subagent in parallel to correlate planned changes with recently modified files. By the time the preview finishes, you already know *why* each change is happening.

Deletes and replacements are flagged explicitly and require confirmation. Replacements are especially dangerous — they destroy and recreate resources, causing downtime.

### `/deploy <stack>`
Always runs preview first so there are no surprises. Production requires typing explicit confirmation — not just pressing Enter. This friction is intentional: a wrong `pulumi up` in prod is hard to undo.

### `/audit`
The most powerful command in the repo. Launches 3 parallel subagents simultaneously:
- **Best practices** — catches Pulumi-specific traps (resources in `apply()`, missing `register_outputs()`, broken Output composition)
- **Security** — finds hardcoded secrets, over-permissive IAM, missing secret outputs
- **Code quality** — flags oversized modules, missing type annotations, dead code

Running these in parallel means a full audit takes the same time as the slowest check, not the sum of all three.

### `/lint`
ruff and mypy have no dependency on each other, so they run in parallel subagents. Faster feedback, same result.

### `/test`
Unit tests per module are independent — they run in parallel subagents. Integration tests are sequential because they share cloud state and can't safely run concurrently.

### `/commit`
Enforces [Conventional Commits](https://www.conventionalcommits.org/) with IaC-specific types (`feat(infra):`, `fix(infra):`, `refactor(infra):`). Suggests `/simplify` first if Python files are staged — keeps infra code lean before it hits git history. No `Co-Authored-By` trailers.

### `/new-component`
Scaffolds a typed `ComponentResource` with the correct structure from the start: proper type URN (`p2bid:infra:<Name>`), typed `Args` class, `ResourceOptions(parent=self)` on all children, `register_outputs()`. Fetches live Pulumi docs via Context7 so the generated code matches the current API.

### `/new-stack`
Copies config from `staging` as baseline so new stacks start with sensible defaults rather than empty config. Reminds about secrets — `pulumi config set --secret` — before the user commits anything.

---

## Skills

Skills are loaded from `.claude/skills/` and applied automatically based on context defined in `CLAUDE.md`. No manual invocation needed.

### Why skills instead of just CLAUDE.md instructions?

CLAUDE.md is a project-level config file. Skills are deep, maintained knowledge bases — some are 800+ lines with code examples, edge cases, and anti-patterns. Keeping all of that in CLAUDE.md would make it unreadable. Skills let us separate *when* (CLAUDE.md) from *what* (SKILL.md).

### Pulumi Skills (from [pulumi/agent-skills](https://github.com/pulumi/agent-skills))

**`pulumi-best-practices`**
Pulumi has traps that aren't obvious from the docs. The two most common: creating resources inside `apply()` (they won't appear in `pulumi preview`, making changes unpredictable) and calling `.get()` on Outputs (breaks the dependency graph). This skill makes Claude aware of these and ~10 other correctness rules so generated code is production-safe, not just syntactically valid.

**`pulumi-component`**
`ComponentResource` has strict rules that are easy to get wrong:
- Wrong type string format → resource graph breaks
- Missing `register_outputs()` → outputs invisible to stack references
- Missing `ResourceOptions(parent=self)` → destroy ordering breaks

This skill encodes the exact patterns for correct, distributable components.

**`pulumi-esc`**
Hardcoded secrets and per-stack config duplication are the most common IaC security mistakes. Pulumi ESC solves both with centralised secrets, OIDC-based short-lived credentials, and layered environment composition. The skill covers correct ESC YAML syntax, OIDC setup for GCP/AWS/Azure, and integration with external stores (Secrets Manager, Vault, 1Password).

**`pulumi-automation-api`**
The Automation API is the right tool for CI/CD orchestration and multi-stack deployments, but it has non-obvious patterns around workspace lifecycle and error handling. This skill ensures Claude generates correct, production-ready Automation API code rather than guessing at the API surface.

### DevOps & Security Skills

**`senior-devops`** ([source](https://github.com/alirezarezvani/claude-skills))
Direct `pulumi up` to prod by a developer is an antipattern — changes should go through CI/CD with PR approval and isolated credentials. This skill enforces that discipline in every deployment discussion.

**`senior-secops`** ([source](https://github.com/alirezarezvani/claude-skills))
Pulumi gives you the full power of Python — including all its security pitfalls. Hardcoded API keys, overly broad IAM roles, and missing policy-as-code are endemic in IaC projects. This skill runs a security lens over every sensitive resource.

**`devops-verification-before-completion`** ([source](https://github.com/lgbarn/devops-skills))
Prevents "it should work" claims without evidence. Before any task is declared done, verification commands must run and their output must be checked. Infrastructure is unforgiving — a wrong assumption in prod means downtime.

**`devops-systematic-debugging`** ([source](https://github.com/lgbarn/devops-skills))
Random fixes waste time and create new bugs. This skill enforces root-cause tracing before proposing any solution: reproduce, isolate, identify cause, then fix. Especially important for Pulumi where a wrong guess can trigger an accidental resource replacement.

**`devops-requesting-code-review`** ([source](https://github.com/lgbarn/devops-skills))
Dispatches a code-reviewer subagent to catch issues before they reach production. Runs automatically when completing features or before merging.

**`devops-finishing-branch`** ([source](https://github.com/lgbarn/devops-skills))
Provides structured options for completing work: merge, PR, or discard. Ensures branches don't linger and work is properly integrated.

### Built-in Skills

**`simplify`**
Infrastructure code tends to accumulate abstractions. A component that wraps a single resource, a helper that's called once, a base class with one subclass — these add cognitive load without value. `/simplify` catches over-engineering before it enters the codebase.

**`loop`**
Useful during long deploys: `/loop 2m /preview staging` polls the stack every 2 minutes without blocking. Also handy for watching outputs during a multi-stack rollout.

**`update-config`**
Modifies Claude Code settings without hand-editing JSON. Use it to add project-specific hooks or permissions.

---

## Subagents

### The rule

Use subagents for any task involving reading or analysing multiple files. This codebase will grow — design for scale now.

### When to use

| Situation | Pattern |
|-----------|---------|
| Auditing all files in `infra/` | Explore subagent scans, reports back |
| Running independent checks (lint + security) | Parallel subagents simultaneously |
| Unit tests per module | Parallel subagents, one per module |
| Finding patterns across codebase | Explore subagent with broad search |

### When NOT to use

| Situation | Reason |
|-----------|--------|
| Reading 1–3 known files | Direct Read tool is faster |
| Making targeted edits | No parallelism benefit |
| Sequential steps (step B needs result of step A) | Subagents can't share intermediate state |
| Integration tests | Share cloud state — must be sequential |

### Why parallel for `/audit`?

A best-practices scan, a security scan, and a quality scan are completely independent. Running them sequentially means waiting 3× as long. Parallel subagents give the same result in the time of the slowest check.

---

## MCP Servers

**context7** — Pulumi's API surface changes. Provider resources get new arguments, deprecations happen, defaults change. Context7 fetches the current docs for whatever library version is installed, so Claude isn't guessing based on training data that may be months old.

**playwright** — After a deploy, verifying that endpoints actually respond correctly requires a real browser or HTTP client. Playwright handles both: it can hit an API endpoint, render a page, and assert on the result. Useful for post-deploy smoke tests without writing a separate test script.
