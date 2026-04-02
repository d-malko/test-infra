Bootstrap a freshly cloned test-infra repository on a new machine.

Run the following steps in order, check each one succeeds before continuing, and report clearly if anything fails.

---

### 1. Check required tools

Verify these are installed and print their versions:

```bash
python3 --version        # must be 3.12+
pulumi version           # any recent version
uv --version             # preferred package manager
poetry --version         # fallback if uv is not available
```

If any are missing, print install instructions:

- **Python 3.12+**: `pyenv install 3.12` or https://www.python.org/downloads/
- **Pulumi**: `curl -fsSL https://get.pulumi.com | sh`
- **uv** (recommended): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Poetry** (fallback): `curl -sSL https://install.python-poetry.org | python3 -`

Stop and ask the user to install missing tools before continuing.

---

### 2. Install Python dependencies

Use `uv` if available, otherwise fall back to `poetry`:

```bash
# Preferred
uv sync

# Fallback
poetry install
```

---

### 3. Verify Pulumi login

```bash
pulumi whoami
```

If not logged in, prompt the user to run:

```bash
pulumi login
```

And wait for confirmation before continuing.

---

### 4. List available stacks

```bash
pulumi stack ls
```

Ask the user which stack they want to work with (`staging` or `prod`) and select it:

```bash
pulumi stack select <stack>
```

---

### 5. Verify cloud credentials

Run a dry-check by previewing the selected stack:

```bash
pulumi preview --stack <stack> --diff
```

If this fails with a credentials error, show the relevant provider setup instructions:

- **AWS**: `aws configure` or set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- **GCP**: `gcloud auth application-default login`
- **Azure**: `az login`

---

### 6. Done

Print a success summary:

```
✓ Python dependencies installed
✓ Pulumi authenticated
✓ Stack selected: <stack>
✓ Cloud credentials verified

Ready to work. Common next commands:
  /preview <stack>   — preview infrastructure changes
  /deploy <stack>    — deploy infrastructure
  /help              — show all available commands
```
