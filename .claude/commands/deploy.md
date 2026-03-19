Deploy infrastructure to a target stack using `pulumi up`.

Usage: `/deploy <stack>` (stack = staging | prod)

Steps:
1. Identify the target stack from the argument. If omitted, ask the user — never assume a default.
2. Run `pulumi preview --stack <stack> --diff` first and show the summary.
3. If the stack is **prod**:
   - Show a prominent warning.
   - Explicitly ask: "Are you sure you want to deploy to PRODUCTION? Type yes to confirm."
   - Do not proceed without explicit confirmation.
4. If approved, run: `pulumi up --stack <stack> --yes`
5. On success: show the stack outputs (`pulumi stack output --stack <stack>`).
6. On failure: show the error, suggest `pulumi refresh --stack <stack>` if state may be stale.
