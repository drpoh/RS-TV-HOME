# Family Frame 1.2.3

Use the remote left/right for previous/next, OK for pause/resume and up/down for the playback menu. Clicking the displayed media also opens the menu. Back closes the menu (then exits the app). Opening the menu pauses playback; select Continue to resume. Photo interval is 5–120 seconds in five-second increments, videos play to completion. Choose all media, photos only, or videos only; shuffle or sequential order; optional clock. Local playback preferences persist in the TV's application storage.

Rotate either direction in 90-degree steps. Save rotation stores display orientation separately on the Pi, with no changes to original media and no video transcoding. Unsaved rotation is discarded when changing files. Delete requires confirmation and hides the item from playback; restore recovers the most recently hidden item. No original file is physically deleted. USB remains read-only.

Source contains no album content or metadata. Materialize family-frame to generate a separate local edit key, and deploy the app and server together. The authenticated edit endpoint accepts only requests from the configured TV, with an allowlisted operation and known media ID. Runtime orientation/hidden state is local-only under the user's configuration directory. Original upload service remains independent.

Run python3 services/family-frame/test_edits.py for isolated synthetic API tests. Real-TV rendering and remote operation require manual verification.

1.2.1 keeps menu nodes stable during unchanged album refreshes, uses a separate input surface above media, and restores focus on visibility and window changes. Cursor visibility is still controlled by webOS and the remote input connection.

## 1.2.3 — USB MP4 playback reliability

Most original USB MP4s had their container index (moov) beyond the first megabyte. Raspberry Pi prepares separate private copies under ~/.cache/rs-family-frame/video/ using ffmpeg stream-copy and +faststart. Video and audio are not re-encoded, and the original USB remains read-only. Cache filenames are derived from the source path, file size and modification time. Cache directory permissions are 0700 and files are 0600.

After materializing Family Frame, run the prepare_videos.py helper in the ignored dist/family-frame/service directory to prebuild the cache. The HTTP server serves optimized ready copies with normal byte-range support. For new MP4 files, one bounded background cache worker prepares copies while original playback remains available. At least 4 GiB free space must remain.

The TV client now checks actual media currentTime progress. After 8 seconds without progress, it retries the file once and seeks to the last seen position when supported. If playback freezes again, it skips the file instead of remaining stuck. Paused or hidden playback is excluded from this recovery check.

Tests: python3 services/family-frame/test_edits.py and node apps/family-frame/test-playback.cjs. They use synthetic media and never modify original USB. Some highly compressed or high-bitrate videos may still be incompatible with older TV hardware; playback on the real television requires final verification.

## 1.2.4 — Complete videos and universal video rotation

All video files play until the media element reports native `ended` (or the user explicitly selects the next item). The video no longer inherits a slideshow timeout, a 30-second startup/buffering watchdog or the 8-second playback-progress auto-skip. Network buffering displays a message but does not restart the source or advance the playlist. A fatal media error is still handled by the existing error route; unsupported/corrupt media cannot be guaranteed to play.

Every video's displayed orientation includes a permanent +90-degree clockwise baseline. Per-file saved rotation remains an additional offset: `(saved + 90) % 360`. Photos retain their existing orientation and interval. The original USB files and cached MP4 streams are not re-encoded or rotated, only the TV display is rotated. This baseline needs no new preference and therefore survives app restarts and future album refreshes.

Run `node apps/family-frame/test-playback.cjs`, which simulates long buffering, native video completion, global and per-file rotation, and unchanged photo timing. Real-TV playback and landscape/portrait visual proportions require verification on LG.
