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

### Tips
- `/preview` before every `/deploy`
- Stack argument is required for `/preview` and `/deploy` — no default assumed
- `/deploy prod` requires explicit confirmation
- `/new-component` fetches live Pulumi docs via Context7 MCP automatically
- `/test integration` will incur real cloud costs — use sparingly

---
