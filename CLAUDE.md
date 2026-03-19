# p2bid-infra — Claude Code Instructions

## Project Overview
Infrastructure-as-Code repository using **Pulumi (Python)** for the p2bid project.

## General Rules
- Never add `Co-Authored-By: Claude` or any AI authorship trailer to git commits.
- Before committing any infrastructure code changes, run `/simplify` to review for reuse, quality, and efficiency.

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
- Use **Poetry** for dependency management
- Use **pyproject.toml** (not setup.py or setup.cfg)
- All infra functions return `pulumi.Output[T]` — annotate correctly
- Virtual env: always `venv/` (gitignored)

---

## Pulumi Core Patterns

### Configuration
```python
import pulumi

config = pulumi.Config()
env = config.require("environment")                      # Required string
instance_count = config.get_int("instance_count") or 2  # Optional with default
api_key = config.require_secret("api_key")              # Secret — never logged
```

### Inputs & Outputs (critical — never bypass)
```python
# CORRECT: pass Output directly — Pulumi tracks dependency automatically
db = aws.rds.Instance("db", password=password.result)

# WRONG: never call .get() to extract values — breaks dependency graph
db = aws.rds.Instance("db", password=password.result.get())  # DON'T

# Combine multiple outputs
conn = pulumi.Output.all(host=db.hostname, port=db.port).apply(
    lambda o: f"postgresql://{o['host']}:{o['port']}"
)

# String interpolation
url = pulumi.Output.concat("https://", server.hostname)
url = pulumi.Output.format("https://{host}/api", host=server.hostname)
```

### Component Resources (reusable abstractions)
```python
import pulumi
from pulumi import ComponentResource, ResourceOptions, Input, Output

class WebServiceArgs:
    def __init__(self, image: Input[str], port: Input[int], replicas: Input[int] = 2):
        self.image = image
        self.port = port
        self.replicas = replicas

class WebService(ComponentResource):
    url: Output[str]

    def __init__(self, name: str, args: WebServiceArgs, opts: ResourceOptions = None):
        super().__init__("p2bid:infra:WebService", name, None, opts)

        # All child resources use opts=ResourceOptions(parent=self)
        deployment = k8s.apps.v1.Deployment(
            f"{name}-deployment",
            spec=...,
            opts=ResourceOptions(parent=self),
        )
        self.url = deployment.status.apply(lambda s: s.load_balancer_ingress[0].hostname)
        self.register_outputs({"url": self.url})
```

Type registration: `"<org>:<module>:<Type>"` — e.g., `"p2bid:infra:WebService"`.

### Stack Outputs & Cross-Stack References
```python
# Export from stack
pulumi.export("vpc_id", vpc.id)
pulumi.export("db_endpoint", db.endpoint)

# Reference from another stack
ref = pulumi.StackReference("myorg/p2bid-networking/prod")
vpc_id = ref.get_output("vpc_id")
```

---

## Secrets & Configuration

- **Never** hardcode secrets or commit plaintext secrets
- Use `pulumi config set --secret <key> <value>` for per-stack secrets
- For enterprise/shared secrets use **Pulumi ESC** (Environments, Secrets, Config)
- Mark sensitive resource outputs: `ResourceOptions(additional_secret_outputs=["password", "connection_string"])`
- Integrate with AWS Secrets Manager / HashiCorp Vault for dynamic credentials

---

## Testing Strategy

### Unit Tests (fast, mocked — run in CI on every PR)
```python
# tests/unit/test_networking.py
import pytest
import pulumi
from unittest.mock import patch

class TestVpcCreation:
    @pulumi.runtime.test
    def test_vpc_has_dns_enabled(self):
        from infra.networking import create_vpc
        vpc = create_vpc("test", cidr="10.0.0.0/16")
        def check(args):
            enable_dns, = args
            assert enable_dns is True
        return pulumi.Output.all(vpc.enable_dns_hostnames).apply(check)
```

### Integration Tests (Automation API — run in CI on merge to main)
```python
# tests/integration/test_stack.py
import pytest
from pulumi.automation import LocalWorkspace, ConfigValue

@pytest.fixture(scope="session")
def stack():
    ws = LocalWorkspace(project_name="p2bid-infra", stack_name="ci-test")
    ws.set_config("environment", ConfigValue("test"))
    ws.up(on_output=print)
    yield ws
    ws.destroy(on_output=print)

def test_endpoint_reachable(stack):
    outputs = stack.outputs()
    assert outputs["endpoint"].value.startswith("https://")
```

---

## CI/CD Patterns

- **Preview** on every PR: `pulumi preview` (never `pulumi up` on PRs)
- **Deploy** on merge to `main`: `pulumi up --yes`
- Use **Review Stacks** (`Pulumi.pr.yaml`) for ephemeral PR environments
- Use **Automation API** for complex orchestration (serial deploys, cross-stack ordering)
- Manual approval gate before prod deployments
- Always separate staging and prod stacks; prod requires explicit confirmation

---

## Naming & Tagging Conventions

```python
# Resource names: <component>-<env>-<purpose>
name = f"p2bid-{env}-api-db"

# Always tag every resource
common_tags = {
    "Project": "p2bid",
    "Environment": env,
    "ManagedBy": "pulumi",
    "Repository": "p2bid-infra",
}
```

---

## Code Quality

- Run `pulumi preview` before every `pulumi up` and review the diff
- Use `pulumi refresh` before updates when state may be stale
- Never use `--replace` or `--target` without explicit user confirmation
- Protect critical resources: `ResourceOptions(protect=True)` for databases, stateful storage
- Set `delete_before_replace=True` only when absolutely required
- Use `import_` in `ResourceOptions` to adopt existing resources without recreation

---

## Context7 Usage
When writing or researching Pulumi resources, always:
1. Call `mcp__claude_ai_Context7__resolve-library-id` with e.g. `"pulumi aws"` or `"pulumi kubernetes"`
2. Then call `mcp__claude_ai_Context7__query-docs` with the resolved ID for current API docs

## Playwright Usage
Use Playwright MCP to:
- Verify deployed endpoints are healthy
- Validate cloud console state visually
- Automate browser-based acceptance tests post-deploy
