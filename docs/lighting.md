# Lighting tab (2.0.8 development)

A room-based lighting view is available from My Home. The UI displays confirmed on/off/unavailable states. Arrow keys move between room list, controls and Back; OK toggles the selected available control. Clicking with a pointer also works. Read polling runs only while the panel is open.

The bridge reads a batch of configured light states; actions are limited to locally configured light entities and explicit on/off operations. The existing TV address restriction and scene action key protect write requests. No entity IDs, room configuration or household data are embedded in the public frontend.

Configure .local/lighting.json (mode 0600) as an array of room objects containing id, label and lights; each light has a globally unique id, label and a light entity ID. Materialize stable/preview to copy the private configuration into the ignored bridge build. Unknown or unavailable lights cannot be toggled through the UI. Omit duplicate integrations, device indicators and non-light devices. No HA writes are performed by tests.

Run node ha-bridge/test-lighting.mjs and node ha-bridge/test-lighting-http.mjs. The latter starts an isolated loopback bridge with synthetic MCP data and exercises read, rejected requests and a simulated switch command. Real remote navigation and legacy webOS rendering must be verified on the television before a production rollout.
