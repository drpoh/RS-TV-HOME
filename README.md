# RS TV Home

Lightweight custom launcher for legacy LG webOS televisions, using a local Raspberry Pi bridge to Home Assistant.

## Repository layout
- `apps/stable/` — v1.7.1
- `apps/preview/` — v2.0.0 Preview
- `ha-bridge/` — bridge source template
- `docs/` — architecture and project boundaries

## Local build
Copy `config.example.json` to `.local/config.json` and replace placeholders with your own local settings. Keep this file private. Run `python3 scripts/materialize.py stable` or `python3 scripts/materialize.py preview`. This generates deployable files under ignored `dist/`; package the generated app using LG webOS CLI. The generated bridge depends on an existing local HA MCP client, ffmpeg and a correctly configured Home Assistant. No automatic deployment is enabled.

Do not commit generated builds, action keys, private media, camera credentials or local configuration. Production deployment is unchanged. See [architecture](docs/architecture.md).

## Security
See [mandatory secret-handling rules](docs/security.md). Enable local hooks in every clone before committing.

## Family Frame
The TV client (1.1.1) and local photo/video and upload services are in apps/family-frame/ and services/family-frame/. Build with python3 scripts/materialize.py family-frame. See [Family Frame documentation](docs/family-frame.md).

## Magic Remote and Voice
The Magic Remote 1.4.0 TV app and Raspberry Pi services, including Magic Voice 0.6.2, are included. Build with python3 scripts/materialize.py magic-remote. See [documentation](docs/magic-remote.md).

Optional original TV icons: see [local icon sync](docs/tv-icons.md).

Phone settings (Preview): [local setup](docs/phone-settings.md).
