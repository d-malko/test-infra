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

## Secrets & Authorization

This project uses **zero long-lived credentials** in CI/CD. All authentication is based on short-lived tokens via Workload Identity Federation (WIF).

### Authorization Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WHO                    HOW                          WHAT they access        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Developer (local)      gcloud auth login            GCP Secret Manager      │
│                         + application-default        GCS state bucket        │
│                         PULUMI_CONFIG_PASSPHRASE env Pulumi stack config     │
│                         kubeconfig (talosctl)         Talos cluster           │
├─────────────────────────────────────────────────────────────────────────────┤
│  GitHub Actions CI/CD   WIF (OIDC token from GitHub) GCS state bucket        │
│                         → impersonates               GCP Secret Manager      │
│                           pulumi-backend@ SA         (via pulumi-backend SA) │
│                         PULUMI_CONFIG_PASSPHRASE      Pulumi stack config     │
│                         KUBECONFIG_B64 secret         Talos cluster           │
├─────────────────────────────────────────────────────────────────────────────┤
│  ESO (in-cluster)       WIF (projected K8s SA token)  GCP Secret Manager     │
│                         → impersonates                (read secrets)          │
│                           ext-secrets-operator@ SA                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Flux (in-cluster)      SSH key (flux-git-credentials) GitHub repo (pull)    │
│                         secret in flux-system ns                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### GCP Workload Identity Federation Pools

#### Pool: `talos-staging` — for ESO in-cluster

| Field | Value |
|-------|-------|
| Pool ID | `talos-staging` |
| Provider | `talos` |
| OIDC Issuer | `https://oidc.p2bid.global/staging` |
| Allowed audience | `https://oidc.p2bid.global/staging` |
| Impersonates SA | `ext-secrets-operator@p2bid-staging-xc69rp.iam.gserviceaccount.com` |
| SA permissions | `roles/secretmanager.secretAccessor` on `p2bid-staging-xc69rp` |

The Talos API server issues OIDC tokens. Because its JWKS endpoint is not publicly reachable directly, a static OIDC discovery document and JWKS are served from **Cloudflare Pages** at `https://oidc.p2bid.global/staging/` (files in `cloudflare/oidc/`). GCP uses these to validate cluster-issued tokens.

ESO pods receive a projected ServiceAccount token (audience: `https://oidc.p2bid.global/staging`) and a ConfigMap (`gcp-wif-credential-config`) that tells the Google auth library how to exchange it for a GCP access token.

#### Pool: `github-actions` — for CI/CD pipelines

| Field | Value |
|-------|-------|
| Pool ID | `github-actions` |
| Provider | `github` |
| OIDC Issuer | `https://token.actions.githubusercontent.com` |
| Attribute condition | `assertion.repository_owner == 'P2Bid'` |
| Impersonates SA | `pulumi-backend@p2bid-staging-xc69rp.iam.gserviceaccount.com` |
| SA permissions | `roles/storage.objectAdmin` on GCS state bucket<br>`roles/secretmanager.secretAccessor` on `p2bid-staging-xc69rp` |

> ⚠️ If the repo is transferred to a different GitHub org, update the attribute condition:
> ```bash
> gcloud iam workload-identity-pools providers update-oidc github \
>   --workload-identity-pool=github-actions --location=global \
>   --project=p2bid-staging-xc69rp \
>   --attribute-condition="assertion.repository_owner == '<NEW_ORG>'"
> ```
> Also update the `workloadIdentityUser` binding on the `pulumi-backend` SA.

---

### GCP Secret Manager Secrets

Project: `p2bid-staging-xc69rp`

| Secret name | Contents | Consumed by |
|-------------|----------|-------------|
| `p2bid-staging-gitlab-db-password` | GitLab PostgreSQL password | ESO → `gitlab` namespace |
| `p2bid-staging-gitlab-runner-token` | GitLab Runner auth token (`glrt-…`) | ESO → `gitlab-runner` namespace |
| `p2bid-staging-gitlab-runner-cache-s3` | MinIO credentials `{accessKey, secretKey}` | ESO → `gitlab-runner` namespace |
| `p2bid-staging-cloudflare-api-token` | Cloudflare DNS API token | ESO → `cert-manager` namespace |
| `p2bid-staging-cloudflare-pages-token` | Cloudflare Pages deploy token | GitHub Actions |
| `p2bid-staging-pulumi-passphrase` | Pulumi stack encryption passphrase | Reference / onboarding |

To add or update a secret:
```bash
# Create new
echo -n "value" | gcloud secrets create my-secret \
  --project=p2bid-staging-xc69rp --data-file=-

# Update existing
echo -n "new-value" | gcloud secrets versions add my-secret \
  --project=p2bid-staging-xc69rp --data-file=-
```

---

### Pulumi Stack Secrets (encrypted in `Pulumi.staging.yaml`)

| Config key | Contents | How to update |
|------------|----------|---------------|
| `p2bid-infra:git_ssh_key` | SSH private key for Flux to pull from GitHub | `pulumi config set --stack staging --secret p2bid-infra:git_ssh_key "$(cat ~/.ssh/id_ed25519)"` |

Encryption passphrase: stored in GCP Secret Manager as `p2bid-staging-pulumi-passphrase` and in GitHub Actions as `PULUMI_CONFIG_PASSPHRASE`.

---

### GitHub Actions Secrets

Set at `https://github.com/P2Bid/p2bid-infra/settings/secrets/actions`:

| Secret | Used by | Description |
|--------|---------|-------------|
| `PULUMI_CONFIG_PASSPHRASE` | Deploy + Drift workflows | Decrypts `Pulumi.staging.yaml` secrets |
| `KUBECONFIG_B64` | Deploy workflow | Base64-encoded kubeconfig for Talos cluster access |
| `CLOUDFLARE_PAGES_TOKEN` | Deploy OIDC Pages workflow | Cloudflare API token with Pages write permission |
| `CLOUDFLARE_ACCOUNT_ID` | Deploy OIDC Pages workflow | Cloudflare account ID (`651ba5636ca1bf71a2c53c0bb4a8da39`) |

GCP authentication in CI uses WIF — no GCP credentials are stored as GitHub secrets.

To regenerate `KUBECONFIG_B64`:
```bash
talosctl --talosconfig /path/to/talosconfig kubeconfig /tmp/kube.yaml
gh secret set KUBECONFIG_B64 --repo P2Bid/p2bid-infra \
  --body "$(base64 -w0 /tmp/kube.yaml)"
```

---

### Flux Git Credentials (in-cluster)

Flux pulls from `ssh://git@github.com/P2Bid/p2bid-infra.git` using an SSH key stored as a Kubernetes secret in the `flux-system` namespace:

| Secret | Namespace | Keys |
|--------|-----------|------|
| `flux-git-credentials` | `flux-system` | `identity` (private key), `known_hosts` |

This secret is created by Pulumi from the `p2bid-infra:git_ssh_key` stack config. The corresponding **public key must be added as a Deploy Key** on the GitHub repo:

`https://github.com/P2Bid/p2bid-infra/settings/keys`

---

## GitHub Actions

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| **Deploy Infrastructure** | Push to `main` (`infra/**`, `Pulumi.*.yaml`) or `workflow_dispatch` | `pulumi up --stack staging` (or prod) |
| **Drift Detection** | Hourly cron + `workflow_dispatch` | `pulumi preview`; opens a GitHub issue if drift detected |
| **Deploy OIDC Pages** | Push to `main` (`cloudflare/oidc/**`) or `workflow_dispatch` | Deploys static OIDC files to Cloudflare Pages (`p2bid-oidc`) |

---

## Flux Reconciliation Order

```
flux-system (root Kustomization)
└── infrastructure-controllers     cert-manager, ESO, CNPG, Flagger, Cilium config
    └── infrastructure-configs     ClusterSecretStore, cert issuers, gateway, WIF ConfigMap
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

## JWKS Rotation

If the Talos API server signing key rotates (rare, happens on full cluster rebuild), update the static JWKS:

```bash
# 1. Fetch new JWKS from cluster
kubectl get --raw /openid/v1/jwks > cloudflare/oidc/staging/openid/v1/jwks

# 2. Commit and push — GitHub Actions deploys it to Cloudflare Pages automatically
git add cloudflare/oidc/ && git commit -m "fix: rotate JWKS" && git push
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
