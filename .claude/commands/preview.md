Run `pulumi preview` for the specified stack and summarise the planned changes.

Usage: `/preview <stack>` (stack = staging | prod)

Steps:
1. Confirm the target stack from the argument. If omitted, ask the user — do not assume a default.
2. Run: `pulumi preview --stack <stack> --diff`
3. Parse the output and produce a human-readable summary:
   - Resources to **create** (count + names)
   - Resources to **update** (count + what changes)
   - Resources to **delete** (count + names) — flag these prominently
   - Resources to **replace** — warn the user, replacing is destructive
4. If any deletes or replacements are in the plan, explicitly ask the user to confirm before proceeding.
5. Do NOT run `pulumi up` — this command is preview only.
