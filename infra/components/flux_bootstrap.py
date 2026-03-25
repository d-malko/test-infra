"""FluxBootstrap ComponentResource — installs Flux controllers and wires up GitOps."""

from dataclasses import dataclass

import pulumi
import pulumi_kubernetes as kubernetes

_FLUX_NAMESPACE = "flux-system"
_GIT_REPO_NAME = "p2bid-infra"
_GIT_SECRET_NAME = "flux-git-credentials"

# Official Flux install manifests — no pre-install hooks (safe on Talos + Cilium).
# Regenerate with: flux install --export > flux/install/flux-{version}.yaml
_FLUX_INSTALL_URL = (
    "https://github.com/fluxcd/flux2/releases/download/"
    "v{version}/install.yaml"
)


@dataclass
class FluxBootstrapArgs:
    git_url: pulumi.Input[str]
    git_branch: pulumi.Input[str] = "main"
    cluster_path: str = "flux/clusters/staging"
    flux_version: str = "2.8.3"
    git_token: pulumi.Input[str] | None = None
    # No GCP credentials needed — ESO uses Workload Identity Federation
    # via projected K8s ServiceAccount tokens. GCP WIF config is in
    # flux/infrastructure/configs/secret-store/wif-credential-config.yaml


class FluxBootstrap(pulumi.ComponentResource):
    """Installs Flux via official manifests and creates the root GitRepository + Kustomization.

    Pulumi manages only:
      - Flux controllers (official install.yaml — no Helm pre-install hooks)
      - Bootstrap GitOps wiring (GitRepository + root Kustomization)

    All cluster workloads (cert-manager, CNPG, GitLab, …) are reconciled by Flux
    from the flux/ directory in this repository.
    """

    def __init__(
        self,
        name: str,
        args: FluxBootstrapArgs,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__("p2bid:components:FluxBootstrap", name, {}, opts)

        # ── Flux controllers via official install manifests ──────────────────
        # Uses the official GitHub release manifest — no pre-install hook jobs
        # that would fail on Talos + Cilium (pods can't reach API via ClusterIP).
        flux = kubernetes.yaml.v2.ConfigFile(
            f"{name}-controllers",
            file=_FLUX_INSTALL_URL.format(version=args.flux_version),
            opts=pulumi.ResourceOptions(parent=self),
        )

        # ── Git credentials (required for private repositories) ─────────────
        git_secret: kubernetes.core.v1.Secret | None = None
        if args.git_token is not None:
            git_secret = kubernetes.core.v1.Secret(
                f"{name}-git-credentials",
                metadata=kubernetes.meta.v1.ObjectMetaArgs(
                    name=_GIT_SECRET_NAME,
                    namespace=_FLUX_NAMESPACE,
                ),
                type="Opaque",
                string_data={
                    "username": "git",
                    "password": args.git_token,
                },
                opts=pulumi.ResourceOptions(
                    parent=self,
                    depends_on=[flux],
                    additional_secret_outputs=["stringData"],
                ),
            )

        # ── GitRepository — tracks this infra repository ─────────────────────
        git_repo = kubernetes.apiextensions.CustomResource(
            f"{name}-gitrepo",
            api_version="source.toolkit.fluxcd.io/v1",
            kind="GitRepository",
            metadata=kubernetes.meta.v1.ObjectMetaArgs(
                name=_GIT_REPO_NAME,
                namespace=_FLUX_NAMESPACE,
            ),
            spec={
                "interval": "1m",
                "url": args.git_url,
                "ref": {"branch": args.git_branch},
                **({"secretRef": {"name": _GIT_SECRET_NAME}} if git_secret else {}),
            },
            opts=pulumi.ResourceOptions(
                parent=self,
                depends_on=[flux] + ([git_secret] if git_secret else []),
            ),
        )

        # ── Root Kustomization — Flux syncs flux/clusters/<env>/ ─────────────
        kubernetes.apiextensions.CustomResource(
            f"{name}-kustomization",
            api_version="kustomize.toolkit.fluxcd.io/v1",
            kind="Kustomization",
            metadata=kubernetes.meta.v1.ObjectMetaArgs(
                name=_FLUX_NAMESPACE,
                namespace=_FLUX_NAMESPACE,
            ),
            spec={
                "interval": "10m",
                "retryInterval": "1m",
                "timeout": "5m",
                "sourceRef": {
                    "kind": "GitRepository",
                    "name": _GIT_REPO_NAME,
                },
                "path": f"./{args.cluster_path}",
                "prune": True,
                "wait": True,
            },
            opts=pulumi.ResourceOptions(parent=self, depends_on=[git_repo]),
        )

        self.register_outputs({
            "namespace": _FLUX_NAMESPACE,
            "git_repository": _GIT_REPO_NAME,
        })
