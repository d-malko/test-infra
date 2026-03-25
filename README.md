# p2bid-infra

Infrastructure-as-Code for the **p2bid** project — [Pulumi](https://www.pulumi.com/) (Python) managing Flux GitOps bootstrap on a [Talos Linux](https://www.talos.dev/) Kubernetes cluster.

---

## Architecture Overview

```
GitHub (P2Bid/p2bid-infra)
        │
        ├── Pulumi (Python)          — bootstraps Flux controllers + GitRepository + Kustomization
        │     └── GCS backend        gs://p2bid-staging-xc69rp-infra-state
        │
        └── Flux GitOps              — reconciles everything else from flux/
              ├── infrastructure/controllers/   cert-manager, ESO, CNPG, Flagger, Cilium, …
              ├── infrastructure/configs/       ClusterSecretStore, cert issuers, gateway
              └── apps/                         GitLab, GitLab Runner, databases
```

**Cluster:** Single-node Talos Linux at `51.195.61.13:6443`
**Secrets:** GCP Secret Manager via External Secrets Operator (WIF — no SA keys)
**DNS/TLS:** Cloudflare + cert-manager (Let's Encrypt)
**Stacks:** `staging` (active) · `prod` (not yet provisioned)

---

## Repository Structure

```
p2bid-infra/
├── Pulumi.yaml
├── Pulumi.staging.yaml          # Stack config (git URL, SSH key secret, cluster path)
├── __main__.py                  # Thin entrypoint → infra/
├── pyproject.toml               # Python deps (uv/Poetry)
│
├── infra/
│   ├── flux.py                  # Reads stack config, instantiates FluxBootstrap
│   └── components/
│       └── flux_bootstrap.py    # ComponentResource: Flux controllers + GitRepository + Kustomization
│
├── flux/                        # Everything Flux reconciles
│   ├── clusters/staging/        # Root kustomizations (entry point for Flux)
│   ├── infrastructure/
│   │   ├── controllers/         # Helm releases: cert-manager, ESO, CNPG, Flagger, …
│   │   └── configs/             # ClusterSecretStore, cert issuers, gateway, …
│   └── apps/
│       ├── gitlab/              # GitLab CE HelmRelease
│       ├── gitlab-runner/       # GitLab Runner + ExternalSecrets
│       └── databases/           # CNPG PostgreSQL clusters
│
├── cloudflare/
│   └── oidc/                    # Static OIDC discovery + JWKS for GCP WIF
│       └── staging/
│           ├── .well-known/openid-configuration
│           └── openid/v1/jwks
│
└── .github/workflows/
    ├── pulumi-deploy.yml        # Deploy infra on push to main (infra/** changes)
    ├── pulumi-drift.yml         # Hourly drift detection via pulumi preview
    └── deploy-oidc-pages.yaml   # Deploy cloudflare/oidc/ to Cloudflare Pages
```

---

## Prerequisites

| Tool | Purpose |
|------|---------|
| Python 3.12+ | Runtime |
| [uv](https://astral.sh/uv) | Dependency management |
| [Pulumi CLI](https://www.pulumi.com/docs/install/) | IaC engine |
| [gcloud CLI](https://cloud.google.com/sdk/docs/install) | GCP auth + Secret Manager |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | Cluster access |
| [talosctl](https://www.talos.dev/latest/talos-guides/install/talosctl/) | Talos cluster management |

---

## Getting Started

```bash
# 1. Clone and install dependencies
git clone git@github.com:P2Bid/p2bid-infra.git
cd p2bid-infra
uv sync

# 2. Authenticate GCP (for Secret Manager and Pulumi GCS backend)
gcloud auth login
gcloud auth application-default login

# 3. Set Pulumi passphrase and backend
export PULUMI_CONFIG_PASSPHRASE="kube-2731-infra"
export PULUMI_BACKEND_URL="gs://p2bid-staging-xc69rp-infra-state"

# 4. Get kubeconfig from Talos
talosctl --talosconfig /path/to/talosconfig kubeconfig ~/.kube/config

# 5. Preview changes
pulumi preview --stack staging
```

With Claude Code, run `/setup` to automate steps 1–4.

---

## Deploying

```bash
# Preview
pulumi preview --stack staging

# Deploy (Flux controllers + GitRepository + Kustomization)
pulumi up --stack staging
```

Pulumi manages only the Flux bootstrap layer. All workloads (GitLab, CNPG, cert-manager, etc.) are reconciled by Flux automatically after bootstrap.

---

## Secrets Management

All runtime secrets live in **GCP Secret Manager** (`p2bid-staging-xc69rp` project) and are pulled into the cluster by **External Secrets Operator** using **Workload Identity Federation** — no service account keys anywhere.

### GCP secrets used

| Secret name | Contents |
|-------------|---------|
| `p2bid-staging-gitlab-db-password` | GitLab PostgreSQL password |
| `p2bid-staging-gitlab-runner-token` | GitLab Runner auth token (`glrt-…`) |
| `p2bid-staging-gitlab-runner-cache-s3` | MinIO credentials JSON `{accessKey, secretKey}` |
| `p2bid-staging-cloudflare-api-token` | Cloudflare DNS token (cert-manager DNS-01) |
| `p2bid-staging-cloudflare-pages-token` | Cloudflare Pages deploy token |

### Pulumi secrets (encrypted in Pulumi.staging.yaml)

| Config key | Contents |
|------------|---------|
| `p2bid-infra:git_ssh_key` | SSH private key for Flux → GitHub pull |

### Adding a new secret

```bash
# 1. Create in GCP Secret Manager
echo -n "my-value" | gcloud secrets create my-secret \
  --project=p2bid-staging-xc69rp --data-file=-

# 2. Add ExternalSecret manifest in flux/apps/<app>/external-secrets.yaml
# 3. Reference the K8s secret in the HelmRelease values
```

---

## GCP Workload Identity Federation

ESO authenticates to GCP without SA keys via two WIF pools:

| Pool | Provider | Used by |
|------|----------|---------|
| `talos-staging` | `talos` (OIDC issuer: `https://oidc.p2bid.global/staging`) | ESO in cluster |
| `github-actions` | `github` (attribute: `repository_owner == 'P2Bid'`) | GitHub Actions CI/CD |

The OIDC discovery document and JWKS for `talos-staging` are served from Cloudflare Pages at `https://oidc.p2bid.global/staging/` — deployed automatically via the `deploy-oidc-pages` GitHub Actions workflow whenever `cloudflare/oidc/` changes.

> **JWKS rotation:** if the Talos API server signing key rotates, update `cloudflare/oidc/staging/openid/v1/jwks` with the new key from:
> ```bash
> kubectl get --raw /openid/v1/jwks
> ```

---

## GitHub Actions

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| **Deploy Infrastructure** | Push to `main` (infra files) or `workflow_dispatch` | `pulumi up --stack staging` (or prod) |
| **Drift Detection** | Hourly cron + `workflow_dispatch` | `pulumi preview`; opens a GitHub issue if drift detected |
| **Deploy OIDC Pages** | Push to `main` (`cloudflare/oidc/**`) or `workflow_dispatch` | Deploys static OIDC files to Cloudflare Pages (`p2bid-oidc`) |

### Required GitHub Actions secrets

Set at `https://github.com/P2Bid/p2bid-infra/settings/secrets/actions`:

| Secret | Used by |
|--------|---------|
| `CLOUDFLARE_PAGES_TOKEN` | Deploy OIDC Pages workflow |
| `CLOUDFLARE_ACCOUNT_ID` | Deploy OIDC Pages workflow |
| `PULUMI_CONFIG_PASSPHRASE` | Deploy + Drift workflows |

GCP auth in CI uses Workload Identity Federation (no stored credentials).

---

## Flux Reconciliation Order

```
flux-system (root Kustomization)
└── infrastructure-controllers     cert-manager, ESO, CNPG, Flagger, Cilium config
    └── infrastructure-configs     ClusterSecretStore, cert issuers, gateway, WIF config
        └── apps                   GitLab, GitLab Runner, databases
```

Each layer depends on the previous being `Ready`. To check status:

```bash
kubectl get kustomization -n flux-system
kubectl get helmrelease -A
```

To force a re-sync:

```bash
kubectl annotate kustomization <name> -n flux-system \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" --overwrite
```

---

## Claude Code Commands

| Command | Description |
|---------|-------------|
| `/setup` | Bootstrap freshly cloned repo |
| `/preview <stack>` | `pulumi preview --diff` with summary |
| `/deploy <stack>` | `pulumi up` with preview gate |
| `/audit` | Full codebase audit (best-practices, security, quality) |
| `/lint` | ruff + mypy |
| `/test` | pytest unit + integration |
| `/commit` | IaC-aware Conventional Commits |
| `/new-component <Name>` | Scaffold a typed `ComponentResource` |
| `/help` | Show all commands |

---

## One-time Global Setup (per developer machine)

Add this hook to `~/.claude/settings.json` so Claude always knows the current date:

```json
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
