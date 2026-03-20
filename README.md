# p2bid-infra

Infrastructure-as-Code for the **p2bid** project, written in [Pulumi](https://www.pulumi.com/) (Python).

> Want to understand *why* each command, skill, and subagent pattern is set up this way? See [CLAUDE-SETUP.md](CLAUDE-SETUP.md).
> Migrating from existing infrastructure? See [MIGRATION-PLAN.md](MIGRATION-PLAN.md).

---

## Getting Started

**With Claude Code (recommended):** open the repo and run `/setup` — it checks tools, installs deps, authenticates Pulumi, and verifies cloud credentials.

**Manually:**

```bash
# 1. Install: Python 3.12+, uv (recommended) or Poetry, Pulumi CLI, cloud CLI (gcloud/aws/az)
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
curl -fsSL https://get.pulumi.com | sh             # Pulumi

# 2. Install dependencies
uv sync          # preferred
# poetry install   # fallback

# 3. Authenticate
pulumi login

# 4. Select stack and verify
pulumi stack select staging
pulumi preview --diff
```

---

## Project Structure

```
p2bid-infra/
├── Pulumi.yaml / Pulumi.staging.yaml / Pulumi.prod.yaml
├── __main__.py              # Thin entrypoint — delegates to infra/
├── pyproject.toml           # Python deps (Poetry)
├── infra/
│   ├── networking.py        # VPC, subnets, SGs
│   ├── compute.py           # EC2 / ECS / K8s
│   ├── database.py          # RDS, ElastiCache
│   ├── storage.py           # S3, EFS
│   └── components/          # Reusable ComponentResources
└── tests/
    ├── unit/                # Fast mocked tests
    └── integration/         # Automation API (deploys real infra)
```

**Stacks:** `staging` (pre-prod) and `prod` (requires explicit confirmation).

---

## Claude Code Commands

Local commands in [.claude/commands/](.claude/commands/). Type `/` in Claude Code to see them.

| Command | Description |
|---------|-------------|
| `/setup` | Bootstrap freshly cloned repo |
| `/preview <stack>` | `pulumi preview --diff` with readable summary |
| `/deploy <stack>` | `pulumi up` with preview gate; prod requires confirmation |
| `/audit` | Full codebase audit via 3 parallel subagents (best-practices, security, quality) |
| `/lint` | ruff + mypy in parallel |
| `/test [unit\|integration\|all]` | pytest; unit runs in parallel per module |
| `/commit` | IaC-aware Conventional Commits |
| `/new-component <Name>` | Scaffold a typed `ComponentResource` |
| `/new-stack <name>` | Create stack, copy config from staging |
| `/help` | Show all commands |

---

## Claude Code Skills

Skills are loaded automatically — no manual invocation needed.

### Installed in this repo ([.claude/skills/](.claude/skills/))

**Pulumi** — from [pulumi/agent-skills](https://github.com/pulumi/agent-skills):

| Skill | Auto-activates when… |
|-------|----------------------|
| `pulumi-best-practices` | writing or reviewing any `infra/*.py` |
| `pulumi-component` | working in `infra/components/` |
| `pulumi-esc` | touching secrets, stack configs, or OIDC setup |
| `pulumi-automation-api` | writing CI/CD or `pulumi.automation` code |

**DevOps & Security** — from [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) and [lgbarn/devops-skills](https://github.com/lgbarn/devops-skills):

| Skill | Auto-activates when… |
|-------|----------------------|
| `senior-devops` | discussing CI/CD pipelines or environment isolation |
| `senior-secops` | touching IAM, RBAC, secrets, or policy-as-code |
| `devops-verification-before-completion` | before claiming any task is done or ready to merge |
| `devops-systematic-debugging` | encountering bugs or unexpected `pulumi preview` output |
| `devops-requesting-code-review` | completing a feature or before merging |
| `devops-finishing-branch` | implementation is complete and ready to integrate |

### Built-in (global, no install needed)

| Skill | Invoke | Use for |
|-------|--------|---------|
| `simplify` | `/simplify` | Review infra code for over-engineering — run before `/commit` |
| `loop` | `/loop <interval> <cmd>` | Poll stack state during long deploys. E.g. `/loop 2m /preview staging` |
| `update-config` | `/update-config` | Add hooks or permissions without editing JSON manually |

---

## MCP Servers

Configured in [.mcp.json](.mcp.json) — available automatically in Claude Code.

| Server | Use |
|--------|-----|
| **context7** | Fetch up-to-date Pulumi provider docs |
| **playwright** | Verify deployed endpoints post-deploy |

---

## One-time Global Setup (per developer machine)

The repo ships with project-level config (`.claude/`), but each developer must add one hook
to their **global** `~/.claude/settings.json` so Claude always knows the current date:

```json
// ~/.claude/settings.json  — add inside "hooks": {}
"UserPromptSubmit": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "echo \"{\\\"additionalSystemPrompt\\\": \\\"Current date: $(date +%Y-%m-%d). Day of week: $(date +%A).\\\"}\"",
        "timeout": 5
      }
    ]
  }
]
```

Without this hook Claude uses its training cutoff date (August 2025) instead of today's date.

---

## Secrets

- Never commit plaintext secrets
- Per-stack secrets: `pulumi config set --secret <key> <value>`
- Shared/dynamic secrets: [Pulumi ESC](https://www.pulumi.com/docs/esc/)
