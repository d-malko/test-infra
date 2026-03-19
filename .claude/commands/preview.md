Run `pulumi preview` for the specified stack and summarise the planned changes.

Usage: `/preview <stack>` (stack = staging | prod)

Steps:
1. Confirm the target stack from the argument. If omitted, ask the user — do not assume a default.
2. Run: `pulumi preview --stack <stack> --diff`
3. While preview runs, use an **Explore subagent** in parallel to scan `infra/` for any recently modified files and note which resources are likely affected.
4. Parse the preview output and produce a human-readable summary:
   - Resources to **create** (count + names)
   - Resources to **update** (count + what changes)
   - Resources to **delete** (count + names) — flag these prominently
   - Resources to **replace** — warn the user, replacing is destructive
5. Cross-reference with the subagent's findings — highlight if a modified file explains the planned change.
6. If any deletes or replacements are in the plan, explicitly ask the user to confirm before proceeding.
7. Do NOT run `pulumi up` — this command is preview only.
