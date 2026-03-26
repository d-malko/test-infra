# Troubleshooting

---

## Flux not syncing

```bash
# Check GitRepository status (SSH auth, connectivity)
kubectl describe gitrepository flux-system -n flux-system

# Check Kustomization errors
kubectl describe kustomization <name> -n flux-system

# Force re-sync
kubectl annotate kustomization <name> -n flux-system \
  reconcile.fluxcd.io/requestedAt="$(date -u +%Y-%m-%dT%H:%M:%SZ)" --overwrite
```

---

## HelmRelease stuck / failed

```bash
kubectl describe helmrelease <name> -n <namespace>

# Reset a stuck release — uninstall then let Flux reinstall
helm uninstall <release-name> -n <namespace>
flux suspend helmrelease <name> -n <namespace>
flux resume helmrelease <name> -n <namespace>
```

---

## ESO not syncing secrets

```bash
# Check ClusterSecretStore is Ready
kubectl describe clustersecretstore gcp-secret-store

# Check ExternalSecret status
kubectl describe externalsecret <name> -n <namespace>
```

Common causes:

| Symptom | Cause | Fix |
|---------|-------|-----|
| `gcp-wif-credential-config` not found | ConfigMap missing | Check `infrastructure-controllers` kustomization is reconciled |
| `audience mismatch` | Projected token audience ≠ WIF pool allowed audience | Verify `$OIDC_ISSUER` matches the `serviceAccountToken.audience` in the ESO HelmRelease |
| `secret not found` | GCP Secret Manager secret doesn't exist | Verify secret name matches `${CLUSTER_NAME}-<name>` in Secret Manager |

---

## WIF authentication errors (GitHub Actions)

**`attribute condition not met`** — repo was transferred to a different org:
```bash
gcloud iam workload-identity-pools providers update-oidc github \
  --workload-identity-pool=github-actions --location=global \
  --project="$GCP_PROJECT" \
  --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'"

# Also update the SA binding
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')
gcloud iam service-accounts add-iam-policy-binding "$SA_PULUMI" \
  --project="$GCP_PROJECT" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository_owner/${GITHUB_ORG}"
```

**`unauthorized_client`** — SA binding missing:
```bash
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')
gcloud iam service-accounts add-iam-policy-binding "$SA_PULUMI" \
  --project="$GCP_PROJECT" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions/attribute.repository_owner/${GITHUB_ORG}"
```

---

## Pulumi state out of sync

After manual cluster changes or namespace deletions:

```bash
pulumi refresh --stack "$PULUMI_STACK"
```

---

## Cluster unreachable from GitHub Actions

`KUBECONFIG_B64` secret may be stale (e.g. after cluster rebuild):

```bash
talosctl --talosconfig "$TALOSCONFIG" kubeconfig /tmp/kube.yaml
gh secret set KUBECONFIG_B64 --repo "$GITHUB_REPO" \
  --body "$(base64 -w0 /tmp/kube.yaml)"
```

---

## OIDC discovery returning stub / 404

The Cloudflare Pages project may not have the latest files deployed:

```bash
# Re-deploy manually
CLOUDFLARE_API_TOKEN="$CF_PAGES_TOKEN" \
CLOUDFLARE_ACCOUNT_ID="$CF_ACCOUNT_ID" \
  wrangler pages deploy cloudflare/oidc \
  --project-name="$CF_PAGES_PROJECT" --branch=main

# Verify
curl "${OIDC_ISSUER}/.well-known/openid-configuration"
curl "${OIDC_ISSUER}/openid/v1/jwks"
```
