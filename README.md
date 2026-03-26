# p2bid-infra

Infrastructure-as-Code for the **p2bid** project — [Pulumi](https://www.pulumi.com/) (Python) managing Flux GitOps bootstrap on a [Talos Linux](https://www.talos.dev/) Kubernetes cluster.

---

## Architecture Overview

```
GitHub ($GITHUB_REPO)
        │
        ├── Pulumi (Python)          — bootstraps Flux controllers + GitRepository + Kustomization
        │     └── GCS backend        gs://$GCS_BUCKET
        │
        └── Flux GitOps              — reconciles everything else from flux/
              ├── infrastructure/controllers/   cert-manager, ESO, CNPG, Flagger, Cilium, …
              ├── infrastructure/configs/       ClusterSecretStore, cert issuers, gateway
              └── apps/                         GitLab, GitLab Runner, databases
```

**Cluster:** Single-node Talos Linux (see `CLUSTER_IP` in [bootstrap vars](docs/bootstrap.md#variables))
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
├── pyproject.toml               # Python deps (uv)
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
├── docs/
│   ├── bootstrap.md             # Full from-scratch setup guide
│   ├── secrets-auth.md          # WIF pools, GCP secrets, GitHub secrets, auth map
│   ├── operations.md            # Day-to-day ops: add apps, JWKS rotation, pipelines
│   └── troubleshooting.md       # Common failure modes and fixes
│
└── .github/workflows/
    ├── pulumi-deploy.yml        # Deploy infra on push to main (infra/** changes)
    ├── pulumi-drift.yml         # Hourly drift detection via pulumi preview
    └── deploy-oidc-pages.yaml   # Deploy cloudflare/oidc/ to Cloudflare Pages
```

---

## Day 2 Quickstart (existing environment)

If the cluster and all accounts already exist, get running locally:

```bash
git clone "git@github.com:${GITHUB_REPO}.git"
cd p2bid-infra
uv sync

gcloud auth login
gcloud auth application-default login

export PULUMI_CONFIG_PASSPHRASE="$PULUMI_CONFIG_PASSPHRASE"
export PULUMI_BACKEND_URL="$PULUMI_BACKEND_URL"

talosctl --talosconfig "$TALOSCONFIG" kubeconfig ~/.kube/config

pulumi preview --stack "$PULUMI_STACK"
```

With Claude Code, run `/setup` to automate the above.

---

## Documentation

| Doc | Contents |
|-----|---------|
| [docs/bootstrap.md](docs/bootstrap.md) | Full from-scratch setup — GCP, Talos, Cloudflare, WIF, Pulumi, deploy |
| [docs/secrets-auth.md](docs/secrets-auth.md) | Authorization map, WIF pools, all secrets reference |
| [docs/operations.md](docs/operations.md) | Add a new app, JWKS rotation, GitHub Actions, Flux reconciliation, Claude Code commands |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Flux, HelmRelease, ESO, WIF, Pulumi state issues |
