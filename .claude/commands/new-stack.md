Create a new Pulumi stack with baseline configuration.

Usage: `/new-stack <stack-name>` (e.g. `/new-stack feature-payments`)

Steps:
1. Run: `pulumi stack init <stack-name>`
2. Copy config from the closest existing stack as a base:
   - `pulumi config cp --stack staging --dest <stack-name>` (copies staging config)
3. Set mandatory config values:
   ```
   pulumi config set --stack <stack-name> environment <stack-name>
   ```
4. Create `Pulumi.<stack-name>.yaml` if it doesn't exist.
5. Show the user the new stack config and ask them to review/adjust environment-specific values (instance sizes, replica counts, secrets).
6. Remind the user: never commit plaintext secrets — use `pulumi config set --secret`.
