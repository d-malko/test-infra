# Bootstrap from Scratch

Follow this guide when setting up the full stack on a new machine or a brand-new environment — no GCP project, no cluster, no secrets.

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
| [wrangler](https://developers.cloudflare.com/workers/wrangler/) | Cloudflare Pages deploy |
| [gh CLI](https://cli.github.com/) | GitHub Actions secrets |

---

## Variables

Set these before running any commands below. All subsequent steps reference them via `$VAR`.

```bash
# GCP
export GCP_PROJECT="<gcp-project-id>"              # e.g. my-project-abc123
export GCP_REGION="europe-west1"
export GCP_BILLING_ACCOUNT="<billing-account-id>"  # gcloud billing accounts list
export GCS_BUCKET="<gcs-bucket-name>"              # Pulumi state bucket, must be globally unique

# GCP Service Accounts (derived — set after GCP_PROJECT is defined)
export SA_PULUMI="pulumi-backend@${GCP_PROJECT}.iam.gserviceaccount.com"
export SA_ESO="ext-secrets-operator@${GCP_PROJECT}.iam.gserviceaccount.com"

# Cluster
export CLUSTER_NAME="<cluster-name>"               # e.g. p2bid-staging
export CLUSTER_IP="<server-ip>"                    # public IP of the Talos node
export TALOSCONFIG="~/.talos/${CLUSTER_NAME}/talosconfig"

# GitHub
export GITHUB_ORG="<github-org>"                   # e.g. MyOrg
export GITHUB_REPO="${GITHUB_ORG}/p2bid-infra"

# Cloudflare
export CF_ACCOUNT_ID="<cloudflare-account-id>"     # Cloudflare dashboard → top-right
export CF_PAGES_PROJECT="<pages-project-name>"     # e.g. my-oidc
export CF_DNS_TOKEN="<cloudflare-dns-token>"        # Zone:DNS:Edit permission
export CF_PAGES_TOKEN="<cloudflare-pages-token>"   # Account:Cloudflare Pages:Edit permission

# OIDC
export OIDC_ISSUER="https://<your-oidc-domain>/<env>"  # e.g. https://oidc.example.com/staging

# Pulumi
export PULUMI_CONFIG_PASSPHRASE="<strong-passphrase>"
export PULUMI_BACKEND_URL="gs://${GCS_BUCKET}"
export PULUMI_STACK="staging"

# Secrets (values to store in GCP Secret Manager)
export GITLAB_DB_PASSWORD="<strong-password>"
export GITLAB_RUNNER_TOKEN="<runner-token>"        # fill after GitLab is deployed — see Step 4 note
export RUNNER_CACHE_ACCESS_KEY="<minio-access-key>"
export RUNNER_CACHE_SECRET_KEY="<minio-secret-key>"
```

---

## Step 1 — GCP Project & Infrastructure

### 1.1 Project & APIs
```bash
gcloud projects create "$GCP_PROJECT" --name="${CLUSTER_NAME^}"
gcloud config set project "$GCP_PROJECT"
gcloud billing projects link "$GCP_PROJECT" --billing-account="$GCP_BILLING_ACCOUNT"

gcloud services enable \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com
```

### 1.2 GCS State Bucket
```bash
gcloud storage buckets create "gs://${GCS_BUCKET}" \
  --project="$GCP_PROJECT" \
  --location="$GCP_REGION" \
  --uniform-bucket-level-access
```

### 1.3 Service Accounts & IAM
```bash
gcloud iam service-accounts create pulumi-backend \
  --display-name="Pulumi backend CI/CD" --project="$GCP_PROJECT"

gcloud iam service-accounts create ext-secrets-operator \
  --display-name="External Secrets Operator" --project="$GCP_PROJECT"

for ROLE in roles/storage.objectAdmin roles/secretmanager.secretAccessor roles/iam.serviceAccountTokenCreator; do
  gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
    --member="serviceAccount:${SA_PULUMI}" --role="$ROLE"
done

gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
  --member="serviceAccount:${SA_ESO}" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Step 2 — Talos Cluster

Provision a single-node server (OVH or any VPS), then:

```bash
# Generate Talos config
talosctl gen config "$CLUSTER_NAME" "https://${CLUSTER_IP}:6443" \
  --output-dir ~/.talos/"$CLUSTER_NAME"

# Apply config to node
talosctl apply-config --insecure --nodes "$CLUSTER_IP" \
  --file ~/.talos/"${CLUSTER_NAME}"/controlplane.yaml

# Bootstrap etcd (one-time only)
talosctl --talosconfig "$TALOSCONFIG" --nodes "$CLUSTER_IP" bootstrap

# Get kubeconfig
talosctl --talosconfig "$TALOSCONFIG" kubeconfig ~/.kube/config
```

---

## Step 3 — Cloudflare

### 3.1 DNS
Point your domain's nameservers to Cloudflare. Create an API token with **Zone:DNS:Edit** permission (`$CF_DNS_TOKEN`) — used by cert-manager.

### 3.2 Pages Project (OIDC discovery)
```bash
npm install -g wrangler

CLOUDFLARE_API_TOKEN="$CF_PAGES_TOKEN" wrangler pages project create "$CF_PAGES_PROJECT" \
  --production-branch=main
```

---

## Step 4 — GCP Secrets

```bash
create_secret() {
  gcloud secrets create "$1" --project="$GCP_PROJECT" --data-file=- <<< "$2"
}

create_secret "${CLUSTER_NAME}-pulumi-passphrase"      "$PULUMI_CONFIG_PASSPHRASE"
create_secret "${CLUSTER_NAME}-gitlab-db-password"     "$GITLAB_DB_PASSWORD"
create_secret "${CLUSTER_NAME}-cloudflare-api-token"   "$CF_DNS_TOKEN"
create_secret "${CLUSTER_NAME}-cloudflare-pages-token" "$CF_PAGES_TOKEN"
create_secret "${CLUSTER_NAME}-gitlab-runner-token"    "$GITLAB_RUNNER_TOKEN"
create_secret "${CLUSTER_NAME}-gitlab-runner-cache-s3" \
  "{\"accessKey\":\"${RUNNER_CACHE_ACCESS_KEY}\",\"secretKey\":\"${RUNNER_CACHE_SECRET_KEY}\"}"
```

> **GitLab runner token — update after GitLab is deployed (Step 10):**
> Once GitLab CE is running, register a runner and update the secret:
> ```bash
> # Admin → CI/CD → Runners → New instance runner → copy the token (glrt-…)
> export GITLAB_RUNNER_TOKEN="glrt-<token-from-gitlab-ui>"
>
> echo -n "$GITLAB_RUNNER_TOKEN" | gcloud secrets versions add \
>   "${CLUSTER_NAME}-gitlab-runner-token" \
>   --project="$GCP_PROJECT" --data-file=-
>
> # Force ESO to re-sync immediately
> kubectl annotate externalsecret gitlab-runner-token -n gitlab-runner \
>   force-sync="$(date +%s)" --overwrite
> ```

---

## Step 5 — GCP Workload Identity Federation

> **Ordering note — chicken-and-egg:** GCP validates the OIDC issuer URL when creating the WIF pool provider. The issuer must be live at `$OIDC_ISSUER` before Step 5.1 can succeed. The resolution:
> 1. Complete **Step 6** first (deploy static OIDC pages — cluster must be up).
> 2. Return here to create the WIF pools.
> 3. Then continue with Steps 7–11.

### 5.1 Pool for ESO (in-cluster)

```bash
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')

gcloud iam workload-identity-pools create talos-staging \
  --location=global --project="$GCP_PROJECT" \
  --display-name="Talos staging cluster"

gcloud iam workload-identity-pools providers create-oidc talos \
  --workload-identity-pool=talos-staging --location=global --project="$GCP_PROJECT" \
  --issuer-uri="$OIDC_ISSUER" \
  --allowed-audiences="$OIDC_ISSUER" \
  --attribute-mapping="google.subject=assertion.sub"

gcloud iam service-accounts add-iam-policy-binding "$SA_ESO" \
  --project="$GCP_PROJECT" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/talos-staging/*"
```

### 5.2 Pool for GitHub Actions

```bash
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')

gcloud iam workload-identity-pools create github-actions \
  --location=global --project="$GCP_PROJECT" \
  --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc github \
  --workload-identity-pool=github-actions --location=global --project="$GCP_PROJECT" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'"

gcloud iam service-accounts add-iam-policy-binding "$SA_PULUMI" \
  --project="$GCP_PROJECT" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository_owner/${GITHUB_ORG}"
```

---

## Step 6 — Deploy Static OIDC Pages

```bash
# Fetch live JWKS from the cluster
kubectl get --raw /openid/v1/jwks > cloudflare/oidc/staging/openid/v1/jwks

# Deploy to Cloudflare Pages
CLOUDFLARE_API_TOKEN="$CF_PAGES_TOKEN" \
CLOUDFLARE_ACCOUNT_ID="$CF_ACCOUNT_ID" \
  wrangler pages deploy cloudflare/oidc \
  --project-name="$CF_PAGES_PROJECT" --branch=main

# Verify both endpoints respond
curl "${OIDC_ISSUER}/.well-known/openid-configuration"
curl "${OIDC_ISSUER}/openid/v1/jwks"
```

Now go back and complete **Step 5**.

---

## Step 7 — SSH Key for Flux

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_flux_p2bid -N "" -C "flux@p2bid-infra"

# Add the PUBLIC key as a read-only Deploy Key on GitHub:
# https://github.com/${GITHUB_REPO}/settings/keys
cat ~/.ssh/id_ed25519_flux_p2bid.pub
```

---

## Step 8 — Pulumi Setup

```bash
git clone "git@github.com:${GITHUB_REPO}.git"
cd p2bid-infra
uv sync

gcloud auth login
gcloud auth application-default login

export PULUMI_CONFIG_PASSPHRASE
export PULUMI_BACKEND_URL

pulumi stack select "$PULUMI_STACK" --create

# Store SSH private key as an encrypted Pulumi secret (Automation API handles multiline)
python3 - <<'EOF'
import pulumi.automation as auto, pathlib, os

stack = auto.select_stack(stack_name=os.environ["PULUMI_STACK"], work_dir=".")
key = pathlib.Path("~/.ssh/id_ed25519_flux_p2bid").expanduser().read_text()
stack.set_config("git_ssh_key", auto.ConfigValue(value=key, secret=True))
print("SSH key stored.")
EOF
```

---

## Step 9 — GitHub Actions Secrets

```bash
gh secret set PULUMI_CONFIG_PASSPHRASE --repo "$GITHUB_REPO" \
  --body "$PULUMI_CONFIG_PASSPHRASE"

talosctl --talosconfig "$TALOSCONFIG" kubeconfig /tmp/kube.yaml
gh secret set KUBECONFIG_B64 --repo "$GITHUB_REPO" \
  --body "$(base64 -w0 /tmp/kube.yaml)"

gh secret set CLOUDFLARE_PAGES_TOKEN --repo "$GITHUB_REPO" \
  --body "$CF_PAGES_TOKEN"

gh secret set CLOUDFLARE_ACCOUNT_ID --repo "$GITHUB_REPO" \
  --body "$CF_ACCOUNT_ID"
```

---

## Step 10 — Deploy

```bash
pulumi preview --stack "$PULUMI_STACK"
pulumi up --stack "$PULUMI_STACK"
```

Pulumi installs Flux into the cluster and creates the `GitRepository` + `Kustomization` resources. Flux then takes over and reconciles all workloads from `flux/`.

---

## Step 11 — Verify

```bash
kubectl get pods -n flux-system
kubectl get kustomization -n flux-system
kubectl get helmrelease -A
kubectl get pods -A -w
```

Reconciliation order: `infrastructure-controllers` → `infrastructure-configs` → `apps`. Allow 5–10 minutes for all HelmReleases to reach `Ready`.
