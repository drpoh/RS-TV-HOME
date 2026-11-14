# RS Family Frame 1.1.1
TV application: apps/family-frame (legacy ES5). Local service: services/family-frame.
Photos and MP4 videos come from a local album or read-only USB directory. The service filters file types, rejects symlinks, serves byte ranges for MP4, and resizes USB photos with ffmpeg on demand. No media are stored in Git.
The uploader accepts JPEG/PNG on the trusted LAN only. Run setup_upload.py interactively to create a separate PIN and local scrypt authentication file. Do not commit PINs, hashes, salts, media, cache, or configuration. HTTP is unencrypted; never publish ports outside the trusted LAN.
Build: configure local settings, then python3 scripts/materialize.py family-frame. Generated TV files are in dist/family-frame/app; Python services are in dist/family-frame/service. Existing production deployment is unchanged. Switching to generated deployment requires separate validation.
TV controls: left/right skip, OK pause, up/down interval 5–60 seconds. Manual or voice launch only.
