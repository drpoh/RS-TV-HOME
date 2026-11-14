# Architecture

- apps/stable: RS TV Home 1.7.1, production application.
- apps/preview: RS TV Home 2.0.4 Preview, separate application ID.
- ha-bridge: local HTTP bridge with restricted client addresses and allowlisted actions.
- Existing Raspberry Pi deployment remains separate from this repository.
- Family Frame 1.1.1, Magic Remote 1.4.0 and Magic Voice 0.6.2 source are included; existing deployments remain separate.
- Home button interception is intentionally excluded. Preview supports local phone-based preferences via a separate service.

Design references (ideas only; no upstream code copied):
- https://github.com/OmkarK97/webos-vibehack
- https://github.com/chiotas/lightkeeper
