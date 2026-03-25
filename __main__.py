"""p2bid-infra — Pulumi entrypoint.

Thin dispatcher: delegates to infra modules.
Pulumi scope: Flux bootstrap only.
Everything else is managed by Flux from flux/.
"""

from infra import flux  # noqa: F401
