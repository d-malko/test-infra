"""Flux bootstrap — instantiates FluxBootstrap for the current stack."""

import pulumi

from infra.components.flux_bootstrap import FluxBootstrap, FluxBootstrapArgs

config = pulumi.Config()

env: str = config.get("environment") or "staging"
git_url: str = (
    config.get("git_url") or "ssh://git@github.com/Test/test-infra.git"
)
git_branch: str = config.get("git_branch") or "main"
cluster_path: str = config.get("cluster_path") or f"flux/clusters/{env}"
git_token: pulumi.Output[str] | None = config.get_secret("git_token")
git_ssh_key: pulumi.Output[str] | None = config.get_secret("git_ssh_key")

FluxBootstrap(
    f"flux-{env}",
    FluxBootstrapArgs(
        git_url=git_url,
        git_branch=git_branch,
        cluster_path=cluster_path,
        git_token=git_token,
        git_ssh_key=git_ssh_key,
    ),
)
