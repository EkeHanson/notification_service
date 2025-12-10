CI secret names and setup

This file documents the GitHub repository secrets that the integration test workflow expects. Add these to the repository's Settings → Secrets → Actions (or use `gh` CLI) before running the workflow.

Recommended secret names (keys) and example values

- `CI_POSTGRES_USER` : postgres
- `CI_POSTGRES_PASSWORD` : password
- `CI_POSTGRES_DB` : test_notifications_db
- `CI_POSTGRES_PORT` : 5432
- `CI_REDIS_URL` : redis://localhost:6379/1
- `CI_KAFKA_BOOTSTRAP_SERVERS` : kafka:9092

Notes
- These values are for the CI environment and test compose. In production, use different secrets and better credentials.
- The workflows use these secrets to avoid embedding plaintext passwords in version control.

How to add secrets via the GitHub UI

1. Go to your repository on GitHub.
2. Click `Settings` → `Secrets and variables` → `Actions` → `New repository secret`.
3. Enter the `Name` (one of the keys above) and `Value`, then `Add secret`.

How to add secrets using the `gh` CLI (recommended for automation)

Install `gh` (GitHub CLI) and authenticate (if not already):

```bash
# login
gh auth login
```

Then set a secret (example):

```bash
# macOS / Linux example - set CI_POSTGRES_PASSWORD interactively
printf "%s" "password" | gh secret set CI_POSTGRES_PASSWORD -b -

# Windows PowerShell example - set CI_POSTGRES_PASSWORD
"password" | gh secret set CI_POSTGRES_PASSWORD -b -
```

Repeat for each secret name listed above.

Security recommendations

- Use least-privilege credentials for CI (do not use production DB credentials).
- Rotate these test credentials periodically.
- In more advanced CI, consider using ephemeral databases or GitHub Actions OIDC to provision test infra dynamically.
