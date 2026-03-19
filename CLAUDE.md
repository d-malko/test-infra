# p2bid-infra — Claude Code Instructions

## Project Overview
Infrastructure-as-Code repository using **Pulumi (Python)** for the p2bid project.

## General Rules
- Never add `Co-Authored-By: Claude` or any AI authorship trailer to git commits.
- Before committing any infrastructure code changes, run `/simplify` to review for reuse, quality, and efficiency.

## Skills — Automatic Activation

Apply the following skills automatically based on context, without waiting for the user to ask:

### Pulumi skills
- **`pulumi-best-practices`** — whenever writing, editing, or reviewing any `.py` file inside `infra/`.
- **`pulumi-component`** — whenever creating or modifying any file inside `infra/components/`.
- **`pulumi-esc`** — whenever working with `Pulumi.*.yaml` stack configs, secrets, credentials, or OIDC setup.
- **`pulumi-automation-api`** — whenever writing deployment scripts, CI/CD pipelines, or any code that imports `pulumi.automation`.

### DevOps & Security skills
- **`senior-devops`** — whenever discussing CI/CD pipelines, stack deployments, PR workflows, or environment isolation.
- **`senior-secops`** — whenever touching secrets, IAM, RBAC, policy-as-code, or any security-sensitive resource.
- **`devops-verification-before-completion`** — always apply before claiming any task is done, fixed, or ready to merge. Run verification commands first, assert after.
- **`devops-systematic-debugging`** — whenever encountering a bug, unexpected `pulumi preview` output, or test failure. Never guess — trace root cause first.
- **`devops-requesting-code-review`** — whenever completing a feature or before merging a branch.
- **`devops-finishing-branch`** — whenever implementation is complete and it's time to decide on merge, PR, or cleanup.

## MCP Servers
- **context7** — Use for up-to-date Pulumi/cloud provider docs. Always resolve library IDs before querying.
- **playwright** — Use for verifying deployed endpoints, scraping cloud console pages, or browser-based validation.

---

## Stack & Project Structure

```
p2bid-infra/
├── Pulumi.yaml              # Project metadata (runtime: python)
├── Pulumi.staging.yaml      # Staging stack config
├── Pulumi.prod.yaml         # Prod stack config
├── __main__.py              # Stack entrypoint (keep thin — delegates to infra/)
├── pyproject.toml           # Dependencies (use Poetry)
├── requirements.txt         # Generated lockfile (poetry export)
├── infra/
│   ├── __init__.py
│   ├── networking.py        # VPC, subnets, SGs
│   ├── compute.py           # EC2/ECS/K8s
│   ├── database.py          # RDS/ElastiCache
│   ├── storage.py           # S3, EFS
│   └── components/          # Reusable ComponentResources
│       ├── __init__.py
│       └── web_service.py
└── tests/
    ├── unit/                # Mocked unit tests
    └── integration/         # Automation API tests
```

## Python Standards
- Python **3.12+** with full type hints everywhere
- Use **Poetry** for dependency management (`pyproject.toml`, not setup.py)
- All infra functions return `pulumi.Output[T]` — annotate correctly
- Virtual env: always `venv/` (gitignored)

---

## Naming & Tagging Conventions

```python
# Resource names: p2bid-<env>-<purpose>
name = f"p2bid-{env}-api-db"

# Always tag every resource
common_tags = {
    "Project": "p2bid",
    "Environment": env,
    "ManagedBy": "pulumi",
    "Repository": "p2bid-infra",
}
```

## Stacks
- Two stacks only: `staging` and `prod`
- Never default to `prod` — always require explicit confirmation

## Code Quality
- Never use `--replace` or `--target` without explicit user confirmation

## Subagents

Always use subagents for tasks that involve reading or analysing multiple files. This repo will grow — design for scale now.

**Use an Explore subagent when:**
- Auditing or reviewing infra code across multiple modules (e.g. "check all files in `infra/` against pulumi-best-practices")
- Searching for patterns across the codebase (e.g. hardcoded secrets, missing tags, wrong naming)
- Answering questions about the overall architecture or code structure

**Use parallel subagents when:**
- Running independent checks simultaneously (e.g. lint + security audit + best-practices review at the same time)
- Analysing multiple infra modules that don't depend on each other
- Running unit tests per module in parallel

**Do NOT use subagents when:**
- Reading 1–3 specific known files
- Making targeted edits to existing files
- The result of one step is needed as input for the next
