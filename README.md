# RS TV Home

Lightweight custom launcher for legacy LG webOS televisions, using a local Raspberry Pi bridge to Home Assistant.

## Repository layout
- `apps/stable/` — v1.7.0
- `apps/preview/` — v2.0.0 Preview
- `ha-bridge/` — bridge source template
- `docs/` — architecture and project boundaries

## Local build
Copy `config.example.json` to `.local/config.json` and replace placeholders with your own local settings. Keep this file private. Run `python3 scripts/materialize.py stable` or `python3 scripts/materialize.py preview`. This generates deployable files under ignored `dist/`; package the generated app using LG webOS CLI. The generated bridge depends on an existing local HA MCP client, ffmpeg and a correctly configured Home Assistant. No automatic deployment is enabled.

Do not commit generated builds, action keys, private media, camera credentials or local configuration. Production deployment is unchanged. See [architecture](docs/architecture.md).

## Security
See [mandatory secret-handling rules](docs/security.md). Enable local hooks in every clone before committing.
