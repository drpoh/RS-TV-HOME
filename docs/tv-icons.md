# Optional original TV icons

Preview 2.0.2 supports local icons for five fixed launcher entries. The coffee action continues to use the bundled generic pictogram. The helper uses the existing paired local TV connection. It prefers the launch-point API because legacy firmware can expose broken icon URLs in listApps.

Run with the existing Python environment containing pywebostv and a private registration file:
```sh
python scripts/sync_tv_icons.py --registration /path/to/private/registration.json
python3 scripts/materialize.py preview
```

No new pairing is saved. Only local TV URLs are fetched, redirects are refused, and images are converted to bounded PNG with metadata stripped. Icons and pairing details must never be committed. If an icon is missing the original generic SVG is retained. Generated app packages are private because they also contain local configuration. No installed-app inventory is saved or published. Stable builds do not include this optional feature.
