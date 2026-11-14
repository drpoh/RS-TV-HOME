# RS Magic Remote 1.4.0 and RS Magic Voice 0.6.2

Source: apps/magic-remote and services/magic-remote. The voice service uses push-to-talk with Home Assistant Assist, a local read-only fast route, and allowlisted television intents. The original deployed services remain unchanged.

Build with python3 scripts/materialize.py magic-remote. Generated app and service code are under ignored dist/magic-remote. Raspberry Pi needs Python, ffmpeg, Bluetooth/HID access, pywebostv and ws4py. Install packages in an isolated virtual environment. The HID rules are local templates; apply them only after reviewing permissions and testing on the intended hardware.

Before deployment, configure the paired remote address, local TV and HA endpoints, Assist pipeline, speaker and service entities, and local application device profile. The menu key is generated from local configuration into the ignored build. Pairing information, learned button mapping, voice recordings, results and timings are runtime-only. The HA token must be configured in a private local terminal using setup_token.py. Never upload any of these data or the locally materialized app package.

Tests use synthetic input and mocks; they do not operate the TV, run devices or access HA. A real hardware deployment requires additional verification.
