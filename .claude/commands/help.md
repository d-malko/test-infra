Display all available slash commands for this repository.

Print the following exactly:

---

## p2bid-infra — Available Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `/help` | `/help` | Show this help message |
| `/setup` | `/setup` | Bootstrap a freshly cloned repo — checks tools, installs deps, logs into Pulumi, selects a stack |
| `/commit` | `/commit` | Commit staged changes with IaC-aware Conventional Commits |
| `/preview` | `/preview <stack>` | Run `pulumi preview --diff` and summarise planned changes. Warns on deletes/replacements. Stacks: `staging`, `prod` |
| `/deploy` | `/deploy <stack>` | Run `pulumi up`. Previews first. Requires typed confirmation for `prod`. Stacks: `staging`, `prod` |
| `/new-component` | `/new-component <Name> [description]` | Scaffold a typed ComponentResource in `infra/components/`, fetches Pulumi docs via Context7 |
| `/new-stack` | `/new-stack <name>` | Create a new stack, copy config from `staging`, set mandatory vars |
| `/audit` | `/audit [best-practices\|security\|all]` | Full codebase audit via 3 parallel subagents: Pulumi best practices, security, and code quality. Default: all |
| `/lint` | `/lint` | Run ruff (lint + format) and mypy --strict in parallel subagents. Offers auto-fix for ruff |
| `/test` | `/test [unit\|integration\|all]` | Run pytest. Integration tests deploy real infra — prompts before running. Default: `unit` |

### Built-in skills (global, no .md file needed)

| Skill | Usage | Description |
|-------|-------|-------------|
| `/simplify` | `/simplify` | Review staged infra code for over-engineering. Run before `/commit` when `.py` files are staged |
| `/loop` | `/loop <interval> <command>` | Repeat a command on an interval. E.g. `/loop 2m /preview staging` |
| `/update-config` | `/update-config` | Configure Claude Code hooks or permissions |

### Tips
- `/preview` before every `/deploy`
- Stack argument is required for `/preview` and `/deploy` — no default assumed
- `/deploy prod` requires explicit confirmation
- Run `/simplify` before `/commit` when Python files are staged
- `/test integration` will incur real cloud costs — use sparingly

---
