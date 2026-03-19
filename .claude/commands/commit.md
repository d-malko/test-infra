Commit staged infrastructure changes following Conventional Commits for IaC.

1. Suggest running `/simplify` first if any `.py` files are staged — skip if user already ran it.
2. Run `git status` and `git diff --staged` to review what's staged.
3. If nothing is staged, ask the user what to stage.
4. Determine the commit type:
   - `feat(infra):` — new resource or stack
   - `fix(infra):` — bug fix in existing resource config
   - `refactor(infra):` — restructuring without behaviour change
   - `chore:` — dependency bumps, config tweaks
   - `test:` — adding/fixing tests
   - `docs:` — README, CLAUDE.md, comments only
5. Write a concise subject line (≤72 chars). Body: explain *why*, not what.
6. Commit with:

```
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

<body if needed>
EOF
)"
```

Never use `--no-verify`. Never amend published commits.
