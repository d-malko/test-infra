Pull latest changes from origin and sync the local environment.

Steps:
1. Run `git status` — if there are uncommitted changes, warn the user and ask whether to stash them first.
2. If stashing is needed: `git stash push -m "auto-stash before pull"`
3. Run `git pull --rebase origin main`
4. If stash was created: `git stash pop`
5. If `requirements.txt` or `pyproject.toml` changed in the pulled commits, run `uv sync` to update the virtualenv.
6. Show a summary of what changed: `git log --oneline ORIG_HEAD..HEAD`
