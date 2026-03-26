# Operations

Day-to-day operational tasks: deploying, adding apps, maintaining pipelines.

---

## Deploying Infrastructure Changes

```bash
# Preview what will change
pulumi preview --stack "$PULUMI_STACK"

# Apply
pulumi up --stack "$PULUMI_STACK"
```

Pulumi manages only the Flux bootstrap layer. All workloads (GitLab, CNPG, cert-manager, etc.) are reconciled by Flux automatically after bootstrap.

---

## Adding a New App

All workloads are managed by Flux — never deploy directly with `helm install` or `kubectl apply`.

1. Create a directory under `flux/apps/<app-name>/`:
   ```
   flux/apps/my-app/
   ├── namespace.yaml       # if needed
   ├── helmrepository.yaml  # if using a new Helm repo
   ├── helmrelease.yaml     # the workload
   └── kustomization.yaml   # lists all resources above
   ```

2. Register it in the apps layer (`flux/apps/kustomization.yaml`):
   ```yaml
   resources:
     - my-app
   ```

3. If the app needs secrets from GCP Secret Manager, add an `ExternalSecret`:
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ExternalSecret
   metadata:
     name: my-app-secret
     namespace: my-app
   spec:
     refreshInterval: 1h
     secretStoreRef:
       name: gcp-secret-store
       kind: ClusterSecretStore
     target:
       name: my-app-secret
     data:
       - secretKey: password
         remoteRef:
           key: ${CLUSTER_NAME}-my-app-password
   ```

4. Commit and push — Flux reconciles automatically within 1 minute:
   ```bash
   git add flux/apps/my-app/ flux/apps/kustomization.yaml
   git commit -m "feat: add my-app via Flux"
   git push
   ```

5. Watch it come up:
   ```bash
   kubectl get kustomization apps -n flux-system -w
   kubectl get helmrelease my-app -n my-app -w
   ```

---

## Flux Reconciliation Order

```
flux-system (root Kustomization)
└── infrastructure-controllers     cert-manager, ESO, CNPG, Flagger, Cilium config
    └── infrastructure-configs     ClusterSecretStore, cert issuers, gateway, WIF ConfigMap
        └── apps                   GitLab, GitLab Runner, databases
```

Each layer depends on the previous being `Ready`.

```bash
# Check status of all layers
kubectl get kustomization -n flux-system
kubectl get helmrelease -A

# Force a re-sync on a specific layer
kubectl annotate kustomization <name> -n flux-system \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" --overwrite
```

---

## JWKS Rotation

If the Talos API server signing key rotates (rare — happens on full cluster rebuild), update the static JWKS:

```bash
# 1. Fetch new JWKS from cluster
kubectl get --raw /openid/v1/jwks > cloudflare/oidc/staging/openid/v1/jwks

# 2. Commit and push — GitHub Actions deploys it to Cloudflare Pages automatically
git add cloudflare/oidc/ && git commit -m "fix: rotate JWKS" && git push
```

---

## GitHub Actions Pipelines

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| **Deploy Infrastructure** | Push to `main` (`infra/**`, `Pulumi.*.yaml`) or `workflow_dispatch` | `pulumi up --stack $PULUMI_STACK` |
| **Drift Detection** | Hourly cron + `workflow_dispatch` | `pulumi preview`; opens a GitHub issue if drift detected |
| **Deploy OIDC Pages** | Push to `main` (`cloudflare/oidc/**`) or `workflow_dispatch` | Deploys static OIDC files to Cloudflare Pages (`$CF_PAGES_PROJECT`) |

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
