# p2bid-infra — Claude Code Instructions

## Project Overview
Infrastructure-as-Code repository using **Pulumi (Python)** for the p2bid project.

## General Rules
- Never add `Co-Authored-By: Claude` or any AI authorship trailer to git commits.
- Before committing any infrastructure code changes, run `/simplify` to review for reuse, quality, and efficiency.

## Skills — Automatic Activation

Apply the following skills automatically based on context, without waiting for the user to ask:

- **`pulumi-best-practices`** — whenever writing, editing, or reviewing any `.py` file inside `infra/`.
- **`pulumi-component`** — whenever creating or modifying any file inside `infra/components/`.
- **`pulumi-esc`** — whenever working with `Pulumi.*.yaml` stack configs, secrets, credentials, or OIDC setup.
- **`pulumi-automation-api`** — whenever writing deployment scripts, CI/CD pipelines, or any code that imports `pulumi.automation`.

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
- Run `pulumi preview --diff` before every `pulumi up`
- Use `pulumi refresh` when state may be stale

## Code Quality
- Protect stateful resources: `ResourceOptions(protect=True)` for databases and storage
- Never use `--replace` or `--target` without explicit user confirmation
- Use `import_` in `ResourceOptions` to adopt existing resources without recreation
