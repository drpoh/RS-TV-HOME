# Phone settings — Preview 2.0.6

A standalone local service on port 8790, independent from the HA bridge. It accepts only the fixed launcher preferences schema (theme, one to six allowlisted favorite app IDs in order, six home widgets). No device command endpoints. The stable app and system Home button remain unchanged.

Use the dedicated phone button on the Preview home screen (or open Settings and select Phone settings) to display the local URL and a separate access code. Use a trusted home Wi-Fi only. HTTP is unencrypted; do not forward this port or share the code or screenshots containing it. Authentication is separate from HA, guesses are rate limited, writes are validated and revision checked. The TV polls while visible and not editing settings. Local TV changes are also saved to the shared service, provided it is reachable. Conflicting changes are resolved in favor of the already saved server version. If offline, the existing TV local settings still work; cross-device synchronization is best effort.

Build with python3 scripts/materialize.py preview. It generates local-only authentication on first build and copies the phone service into ignored dist/preview/phone-settings. Private settings are stored in ignored .local. Do not publish generated packages or runtime files. Run the server under the existing non-root user. The service assumes the current trusted LAN is a /24 network; adjust the private config if needed.

Next: custom backgrounds, additional HA card options, performance and deployment automation. No Home button redirection.

The phone editor can add or remove favorite tiles from the existing curated catalog. Unpinned entries remain available in the dropdown. Netflix and Live TV are excluded. No app packages are installed or uninstalled.
