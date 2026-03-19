# p2bid-infra

Infrastructure-as-Code for the **p2bid** project, written in [Pulumi](https://www.pulumi.com/) (Python).

---

## Getting Started

### Using Claude Code (recommended)

Open the repo in Claude Code and run:

```
/setup
```

That's it — `/setup` checks all required tools, installs dependencies, authenticates with Pulumi, selects a stack, and verifies cloud credentials.

---

### Manual setup

**1. Install required tools**

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) or `pyenv install 3.12` |
| Poetry | any | `curl -sSL https://install.python-poetry.org \| python3 -` |
| Pulumi CLI | any | `curl -fsSL https://get.pulumi.com \| sh` |
| Cloud CLI | — | `aws configure` / `gcloud auth` / `az login` |

**2. Install Python dependencies**

```bash
poetry install
poetry shell
```

**3. Authenticate with Pulumi**

```bash
pulumi login
```

**4. Select a stack and verify**

```bash
pulumi stack select staging   # or prod
pulumi preview --diff
```

---

## Project Structure

```
p2bid-infra/
├── Pulumi.yaml              # Project metadata
├── Pulumi.staging.yaml      # Staging stack config
├── Pulumi.prod.yaml         # Prod stack config
├── __main__.py              # Stack entrypoint (thin — delegates to infra/)
├── pyproject.toml           # Python dependencies (Poetry)
├── infra/
│   ├── __init__.py
│   ├── networking.py        # VPC, subnets, security groups
│   ├── compute.py           # EC2 / ECS / Kubernetes
│   ├── database.py          # RDS, ElastiCache
│   ├── storage.py           # S3, EFS
│   └── components/          # Reusable ComponentResources
│       └── *.py
└── tests/
    ├── unit/                # Fast mocked tests (pulumi.runtime.test)
    └── integration/         # Automation API tests (deploy real infra)
```

---

## Stacks

| Stack | Purpose |
|-------|---------|
| `staging` | Pre-production validation |
| `prod` | Production — requires explicit confirmation before deploy |

---

## Claude Code Slash Commands

This repo ships local Claude Code commands in [.claude/commands/](.claude/commands/).

| Command | Description |
|---------|-------------|
| `/setup` | Bootstrap a freshly cloned repo — checks required tools, installs Python deps, logs into Pulumi, selects a stack, and verifies cloud credentials |
| `/commit` | Commit staged changes with IaC-aware [Conventional Commits](https://www.conventionalcommits.org/) (`feat(infra):`, `fix(infra):`, etc.) |
| `/preview <stack>` | Run `pulumi preview --diff` for a stack and summarise planned changes. Warns explicitly on deletes and replacements. Stacks: `staging`, `prod`. |
| `/deploy <stack>` | Run `pulumi up` for a stack. Runs preview first. Requires explicit typed confirmation for `prod`. Stacks: `staging`, `prod`. |
| `/new-component <Name>` | Scaffold a typed `ComponentResource` in `infra/components/`, fetching current Pulumi docs via Context7 MCP. |
| `/new-stack <name>` | Create a new Pulumi stack, copy config from `staging` as baseline, and set mandatory vars. |
| `/lint` | Run `ruff` (lint + format check) and `mypy --strict` over the codebase. Offers auto-fix for ruff. |
| `/test [unit\|integration\|all]` | Run pytest. Unit tests are fast and mocked. Integration tests deploy real cloud resources — prompts for confirmation first. |

---

## Claude Code Built-in Skills

These are global Claude Code skills — available automatically, no installation needed.

| Skill | How to invoke | When to use |
|-------|--------------|-------------|
| `simplify` | `/simplify` | After writing or changing Python infra code — reviews for reuse, quality, and efficiency. Run before `/commit`. |
| `loop` | `/loop <interval> <command>` | Monitor a long-running deploy or poll stack outputs repeatedly. E.g. `/loop 2m /preview staging` |
| `update-config` | `/update-config` | Configure Claude Code hooks, permissions, or env vars for this project |

> Skills are part of Claude Code itself and cannot be bundled into the repository.

---

## MCP Servers

Project-local MCP config in [.mcp.json](.mcp.json):

| Server | Use |
|--------|-----|
| **context7** | Fetch up-to-date Pulumi provider docs when writing or reviewing resource code |
| **playwright** | Verify deployed endpoints, run browser-based acceptance tests post-deploy |

---

## Secrets

- Never commit plaintext secrets
- Set per-stack secrets: `pulumi config set --secret <key> <value>`
- Secrets are encrypted at rest in stack state files
- For shared/dynamic secrets use [Pulumi ESC](https://www.pulumi.com/docs/esc/)

---

## Testing

```bash
# Unit tests (fast, no cloud calls)
pytest tests/unit/ -v

# Integration tests (deploys real infra — costs money)
pytest tests/integration/ -v -s
```
