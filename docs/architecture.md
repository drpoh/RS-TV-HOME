# Architecture

- apps/stable: RS TV Home 2.0.6, production application.
- apps/preview: RS TV Home 2.0.6 Preview, separate application ID.
- ha-bridge: local HTTP bridge with restricted client addresses and allowlisted actions.
- Existing Raspberry Pi deployment remains separate from this repository.
- Family Frame 1.2.0, Magic Remote 1.4.0 and Magic Voice 0.6.2 source are included; existing deployments remain separate.
- Home button interception is intentionally excluded. Preview supports local phone-based preferences via a separate service.

Design references (ideas only; no upstream code copied):
- https://github.com/OmkarK97/webos-vibehack
- https://github.com/chiotas/lightkeeper

The main app uses the original launcher ID, so manually opening RS TV Home uses the current release. The separate Preview remains available for development. Both share local phone preferences.
