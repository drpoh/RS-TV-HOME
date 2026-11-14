# Secret handling (mandatory)
No real credentials or private configuration may be committed, including test fixtures, docs, logs, packages, screenshots, backups, or historical commits. Keep local settings in ignored .local/config.json (permissions 0600) and materialized builds in ignored dist/. Never paste output containing credentials into issues, Actions logs, or commit messages.

Install repository hooks in each clone before editing or committing:
```sh
git config --local core.hooksPath .githooks
python3 scripts/check_secrets.py --history --staged
```
The pre-commit hook scans all staged blobs; the pre-push hook scans reachable history and outgoing commit tips. Never bypass these checks. The GitHub workflow repeats a pattern scan on push/PR without receiving local secrets. The local scan additionally compares known private values from local configuration. These checks are defense in depth, not a guarantee against arbitrary or obfuscated passwords. Repository-level GitHub Secret Protection and Push protection should also be enabled in Settings; do not bypass them.

If exposure is suspected, stop pushing, revoke or rotate the affected credentials, and review all history and copies. Do not assume deleting a file removes exposure.

The repository is public. Never commit personal names, home addresses, network identifiers, device identifiers, entity registry details, personal media, remote pairing information, diagnostic histories, recordings or personal calibration profiles. Use a non-personal Git author display name and an account-provided no-reply email. Keep all deployment-specific identifiers local. Review all staged changes before pushing. Existing published author metadata requires a separately coordinated history cleanup; changing the local author does not erase earlier commits.
