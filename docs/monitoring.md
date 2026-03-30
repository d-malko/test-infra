# Monitoring

Observability stack deployed to the `monitoring` namespace via Flux.

---

## Stack

| Component | Purpose |
|-----------|---------|
| **Prometheus** | Metrics collection & storage (30d retention, 20Gi PVC) |
| **Alertmanager** | Alert routing → Telegram |
| **Grafana** | Dashboards + log explorer — `https://grafana.p2bid.global` |
| **node-exporter** | Node-level CPU/memory/disk/network metrics |
| **kube-state-metrics** | Kubernetes object state metrics |
| **Loki** | Log aggregation (single-binary, 7d retention, 20Gi PVC) |
| **Promtail** | Log shipper — DaemonSet on every node → Loki |

All deployed via `kube-prometheus-stack` (Helm) + `loki` + `promtail` charts, managed by Flux HelmReleases.

---

## Grafana

**URL:** `https://grafana.p2bid.global`

**Login:** Use your `@p2bid.global` Google account via the **Sign in with Google** button.

Admin credentials (fallback) are in GCP Secret Manager:
```bash
gcloud secrets versions access latest --secret="p2bid-staging-grafana-admin-user" --project="p2bid-staging-xc69rp"
gcloud secrets versions access latest --secret="p2bid-staging-grafana-admin-password" --project="p2bid-staging-xc69rp"
```

Loki is pre-configured as a datasource — use **Explore → Loki** to query logs.

### Google OAuth setup

OAuth credentials live in GCP Secret Manager as a JSON secret:
```bash
# Check current value
gcloud secrets versions access latest \
  --secret="p2bid-staging-grafana-google-oauth" --project="p2bid-staging-xc69rp"

# Update (JSON format: {"client_id":"...","client_secret":"..."})
echo -n '{"client_id":"YOUR_ID.apps.googleusercontent.com","client_secret":"YOUR_SECRET"}' | \
  gcloud secrets versions add p2bid-staging-grafana-google-oauth \
    --project="p2bid-staging-xc69rp" --data-file=-
```

The Google OAuth client must have this redirect URI:
```
https://grafana.p2bid.global/login/google
```

Once OAuth is confirmed working, uncomment `disable_login_form: true` in
[helmrelease-kube-prometheus-stack.yaml](../flux/infrastructure/controllers/monitoring/helmrelease-kube-prometheus-stack.yaml)
to remove the username/password form.

---

## Flux manifests

```
flux/infrastructure/controllers/monitoring/
├── namespace.yaml
├── helmrepository-prometheus-community.yaml
├── helmrepository-grafana.yaml
├── helmrelease-kube-prometheus-stack.yaml   # Prometheus + Alertmanager + Grafana + exporters
├── helmrelease-loki.yaml
├── helmrelease-promtail.yaml
└── kustomization.yaml

flux/infrastructure/configs/monitoring/
├── externalsecret-grafana.yaml              # grafana-admin-secret ← GCP Secret Manager
├── externalsecret-telegram.yaml             # alertmanager-telegram-secret ← GCP Secret Manager
├── alertmanagerconfig.yaml                  # Telegram receiver (warning + critical)
├── grafana-httproute.yaml                   # HTTPRoute: grafana.p2bid.global → Grafana svc
└── kustomization.yaml
```

---

## Telegram Alerts

Alertmanager routes `warning` and `critical` alerts to a Telegram bot.

### Initial setup

1. Create a bot via [@BotFather](https://t.me/BotFather) → copy the token
2. Add the bot to your group/channel; get the chat ID via [@userinfobot](https://t.me/userinfobot)
3. Update the token secret:
   ```bash
   echo -n "123456:ABCdef..." | gcloud secrets versions add p2bid-staging-telegram-bot-token \
     --project="p2bid-staging-xc69rp" --data-file=-
   ```
4. Update `chatID` in [flux/infrastructure/configs/monitoring/alertmanagerconfig.yaml](../flux/infrastructure/configs/monitoring/alertmanagerconfig.yaml), commit, push

### Test an alert manually
```bash
kubectl exec -n monitoring deploy/kube-prometheus-stack-alertmanager -- \
  amtool alert add alertname=TestAlert severity=warning --alertmanager.url=http://localhost:9093
```

---

## Useful kubectl commands

```bash
# Check all monitoring components are running
kubectl get pods -n monitoring

# Check HelmRelease status
kubectl get helmrelease -n monitoring

# Check ExternalSecrets synced
kubectl get externalsecret -n monitoring

# Stream Promtail logs (verify it's shipping)
kubectl logs -n monitoring -l app.kubernetes.io/name=promtail -f

# Port-forward Prometheus locally
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090

# Port-forward Alertmanager locally
kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093
```

---

## Loki log queries (LogQL)

```logql
# All logs from a namespace
{namespace="gitlab"}

# Error logs across all pods
{namespace=~".+"} |= "error"

# Logs from a specific pod
{pod="gitlab-webservice-0"}

# Last 100 lines from cert-manager
{namespace="cert-manager"} | line_format "{{.message}}" | limit 100
```

---

## Talos-specific notes

The following Kubernetes control-plane endpoints are **not** exposed by Talos and are disabled in the HelmRelease:
- `kubeEtcd` — etcd metrics not available externally
- `kubeScheduler` — scheduler metrics not exposed
- `kubeControllerManager` — controller-manager metrics not exposed
- `kubeProxy` — kube-proxy is disabled (Cilium handles it)

These would show as `Down` in the default Kubernetes dashboards and are intentionally skipped.
