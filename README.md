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

## Claude Code Skills

### Project Skills (installed in this repo)

Official Pulumi skills from [pulumi/agent-skills](https://github.com/pulumi/agent-skills), located in [.claude/skills/](.claude/skills/). Committed to the repo — no extra installation needed after cloning.

---

#### `pulumi-best-practices`
**Why use it:** Pulumi has subtle correctness traps that aren't obvious — creating resources inside `apply()` breaks previews, bypassing Output composition breaks dependency tracking, and renaming resources without aliases causes accidental deletions. This skill makes Claude aware of all these pitfalls so generated code is production-safe, not just syntactically correct.

**When to invoke:** When writing new resources, reviewing existing infra code, debugging unexpected replacements or deletions, or refactoring module structure.

```
"Review this file using pulumi-best-practices"
"Write an S3 bucket with versioning — follow pulumi-best-practices"
```

---

#### `pulumi-component`
**Why use it:** `ComponentResource` has strict rules: wrong type strings break the resource graph, missing `register_outputs()` hides outputs from stack references, and improper `ResourceOptions(parent=self)` breaks destroy ordering. This skill encodes the exact patterns needed to build reusable, distributable components correctly.

**When to invoke:** When creating a new component in `infra/components/`, designing a component interface, or packaging components for reuse across projects.

```
"Scaffold a new RDS component using pulumi-component"
"Review my WebService component using pulumi-component"
```

---

#### `pulumi-esc`
**Why use it:** Hardcoded secrets and per-stack config duplication are the most common IaC security mistakes. Pulumi ESC solves both — centralized secrets, OIDC-based short-lived credentials, and layered environment composition. This skill teaches Claude how ESC works so it can generate correct ESC configs, set up OIDC for AWS/GCP/Azure, and integrate with external secret stores (Secrets Manager, Vault, 1Password).

**When to invoke:** When setting up secrets for a new stack, configuring cloud credentials for CI/CD, or migrating from hardcoded config values.

```
"Set up OIDC for AWS using pulumi-esc"
"Create an ESC environment for staging secrets using pulumi-esc"
```

---

#### `pulumi-automation-api`
**Why use it:** The Automation API lets you orchestrate Pulumi programmatically — deploy stacks in order, build self-service portals, or run infrastructure operations from CI/CD without the CLI. It's powerful but has non-obvious patterns around workspace lifecycle, stack initialization, and error handling. This skill ensures Claude generates correct, production-ready Automation API code.

**When to invoke:** When writing CI/CD deploy scripts, building multi-stack orchestration, or embedding Pulumi operations into a Python application.

```
"Write a deployment script for staging → prod rollout using pulumi-automation-api"
"Build a stack health check script using pulumi-automation-api"
```

---

### Built-in Skills

Global Claude Code skills — available automatically in any project, no installation needed.

| Skill | Invoke | Why use it |
|-------|--------|------------|
| `simplify` | `/simplify` | Catches over-engineered infra code — premature abstractions, duplicated resource blocks, unnecessary wrappers. Run before `/commit` to keep code lean. |
| `loop` | `/loop <interval> <command>` | Useful during long deploys to poll stack state or outputs automatically. E.g. `/loop 2m /preview staging` |
| `update-config` | `/update-config` | Add Claude Code hooks or permissions specific to this project without editing JSON manually |

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
