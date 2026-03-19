# p2bid-infra

Infrastructure-as-Code for the **p2bid** project, written in [Pulumi](https://www.pulumi.com/) (Python).

---

## New here? Run `/setup`

If you just cloned this repo, open it in Claude Code and run `/setup` — it will check all required tools, install dependencies, authenticate with Pulumi, and verify your cloud credentials automatically.

---

## Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/) — dependency management
- [Pulumi CLI](https://www.pulumi.com/docs/install/) — `curl -fsSL https://get.pulumi.com | sh`
- Cloud provider CLI configured (e.g. `aws configure`)

## Getting Started

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Select a stack
pulumi stack select staging

# Preview changes
pulumi preview --diff

# Deploy
pulumi up
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
| `/preview [stack]` | Run `pulumi preview --diff` for a stack and summarise planned changes. Warns explicitly on deletes and replacements. Default stack: `dev`. |
| `/deploy [stack]` | Run `pulumi up` for a stack. Runs preview first. Requires explicit typed confirmation for `prod`. Default stack: `dev`. |
| `/new-component <Name>` | Scaffold a typed `ComponentResource` in `infra/components/`, fetching current Pulumi docs via Context7 MCP. |
| `/new-stack <name>` | Create a new Pulumi stack, copy config from `dev` as baseline, and set mandatory vars. |
| `/lint` | Run `ruff` (lint + format check) and `mypy --strict` over the codebase. Offers auto-fix for ruff. |
| `/test [unit\|integration\|all]` | Run pytest. Unit tests are fast and mocked. Integration tests deploy real cloud resources — prompts for confirmation first. |

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
