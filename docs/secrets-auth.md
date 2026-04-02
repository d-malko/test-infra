# Secrets & Authorization

This project uses **zero long-lived credentials** in CI/CD. All authentication is based on short-lived tokens via Workload Identity Federation (WIF).

---

## Authorization Map

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

## GCP Workload Identity Federation Pools

### Pool: `talos-staging` — for ESO in-cluster

| Field | Value |
|-------|-------|
| Pool ID | `talos-staging` |
| Provider | `talos` |
| OIDC Issuer | `$OIDC_ISSUER` |
| Allowed audience | `$OIDC_ISSUER` |
| Impersonates SA | `$SA_ESO` |
| SA permissions | `roles/secretmanager.secretAccessor` on `$GCP_PROJECT` |

The Talos API server issues OIDC tokens. Because its JWKS endpoint is not publicly reachable directly, a static OIDC discovery document and JWKS are served from **Cloudflare Pages** at `$OIDC_ISSUER` (files in `cloudflare/oidc/`). GCP uses these to validate cluster-issued tokens.

ESO pods receive a projected ServiceAccount token (audience: `$OIDC_ISSUER`) and a ConfigMap (`gcp-wif-credential-config`) that tells the Google auth library how to exchange it for a GCP access token.

### Pool: `github-actions` — for CI/CD pipelines

| Field | Value |
|-------|-------|
| Pool ID | `github-actions` |
| Provider | `github` |
| OIDC Issuer | `https://token.actions.githubusercontent.com` |
| Attribute condition | `assertion.repository_owner == '$GITHUB_ORG'` |
| Impersonates SA | `$SA_PULUMI` |
| SA permissions | `roles/storage.objectAdmin` on `$GCS_BUCKET`<br>`roles/secretmanager.secretAccessor` on `$GCP_PROJECT` |

> ⚠️ If the repo is transferred to a different GitHub org, update the attribute condition:
> ```bash
> gcloud iam workload-identity-pools providers update-oidc github \
>   --workload-identity-pool=github-actions --location=global \
>   --project="$GCP_PROJECT" \
>   --attribute-condition="assertion.repository_owner == '<NEW_ORG>'"
> ```
> Also update the `workloadIdentityUser` binding on `$SA_PULUMI`.

---

## GCP Secret Manager Secrets

Project: `$GCP_PROJECT`

| Secret name | Contents | Consumed by |
|-------------|----------|-------------|
| `${CLUSTER_NAME}-gitlab-db-password` | GitLab PostgreSQL password | ESO → `gitlab` namespace |
| `${CLUSTER_NAME}-gitlab-runner-token` | GitLab Runner auth token (`glrt-…`) | ESO → `gitlab-runner` namespace |
| `${CLUSTER_NAME}-gitlab-runner-cache-s3` | MinIO credentials `{accessKey, secretKey}` | ESO → `gitlab-runner` namespace |
| `${CLUSTER_NAME}-cloudflare-api-token` | Cloudflare DNS API token | ESO → `cert-manager` namespace |
| `${CLUSTER_NAME}-cloudflare-pages-token` | Cloudflare Pages deploy token | GitHub Actions |
| `${CLUSTER_NAME}-pulumi-passphrase` | Pulumi stack encryption passphrase | Reference / onboarding |
| `${CLUSTER_NAME}-grafana-admin-user` | Grafana admin username (e.g. `admin`) | ESO → `monitoring` namespace |
| `${CLUSTER_NAME}-grafana-admin-password` | Grafana admin password | ESO → `monitoring` namespace |
| `${CLUSTER_NAME}-telegram-bot-token` | Telegram bot token from @BotFather | ESO → `monitoring` namespace (Alertmanager) |
| `${CLUSTER_NAME}-telegram-chat-id` | Telegram chat/group ID (numeric, e.g. `-1001234567890`) | ESO → `monitoring` namespace (Alertmanager) |
| `${CLUSTER_NAME}-grafana-google-oauth` | JSON `{"client_id":"…","client_secret":"…"}` from Google Cloud Console | ESO → `monitoring` namespace (Grafana OAuth) |

To add or update a secret:
```bash
# Create new
echo -n "value" | gcloud secrets create my-secret \
  --project="$GCP_PROJECT" --data-file=-

# Update existing
echo -n "new-value" | gcloud secrets versions add my-secret \
  --project="$GCP_PROJECT" --data-file=-
```

---

## Pulumi Stack Secrets

Encrypted in `Pulumi.staging.yaml` using `$PULUMI_CONFIG_PASSPHRASE`.

| Config key | Contents | How to update |
|------------|----------|---------------|
| `test-infra:git_ssh_key` | SSH private key for Flux to pull from GitHub | See [bootstrap Step 8](bootstrap.md#step-8--pulumi-setup) |

Passphrase is stored in GCP Secret Manager as `${CLUSTER_NAME}-pulumi-passphrase` and in GitHub Actions as `PULUMI_CONFIG_PASSPHRASE`.

---

## GitHub Actions Secrets

Set at `https://github.com/$GITHUB_REPO/settings/secrets/actions`:

| Secret | Used by | Description |
|--------|---------|-------------|
| `PULUMI_CONFIG_PASSPHRASE` | Deploy + Drift workflows | Decrypts `Pulumi.staging.yaml` secrets |
| `KUBECONFIG_B64` | Deploy workflow | Base64-encoded kubeconfig for Talos cluster access |
| `CLOUDFLARE_PAGES_TOKEN` | Deploy OIDC Pages workflow | Cloudflare API token with Pages write permission |
| `CLOUDFLARE_ACCOUNT_ID` | Deploy OIDC Pages workflow | Cloudflare account ID (`$CF_ACCOUNT_ID`) |

GCP authentication in CI uses WIF — no GCP credentials are stored as GitHub secrets.

To regenerate `KUBECONFIG_B64`:
```bash
talosctl --talosconfig "$TALOSCONFIG" kubeconfig /tmp/kube.yaml
gh secret set KUBECONFIG_B64 --repo "$GITHUB_REPO" \
  --body "$(base64 -w0 /tmp/kube.yaml)"
```

---

## Flux Git Credentials (in-cluster)

Flux pulls from `ssh://git@github.com/$GITHUB_REPO.git` using an SSH key stored as a Kubernetes secret in the `flux-system` namespace:

| Secret | Namespace | Keys |
|--------|-----------|------|
| `flux-git-credentials` | `flux-system` | `identity` (private key), `known_hosts` |

This secret is created by Pulumi from the `test-infra:git_ssh_key` stack config. The corresponding **public key must be added as a Deploy Key** on the GitHub repo:

`https://github.com/$GITHUB_REPO/settings/keys`
