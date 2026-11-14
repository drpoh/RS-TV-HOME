# Architecture

- apps/stable: RS TV Home 1.7.0, production application.
- apps/preview: RS TV Home 2.0.0 Preview, separate application ID.
- ha-bridge: local HTTP bridge with restricted client addresses and allowlisted actions.
- Existing Raspberry Pi deployment remains separate from this repository.
- Family Frame and Magic Remote/Voice are currently separately deployed; not yet migrated.
- Home button interception and phone-based configuration are not implemented.

Design references (ideas only; no upstream code copied):
- https://github.com/OmkarK97/webos-vibehack
- https://github.com/chiotas/lightkeeper
