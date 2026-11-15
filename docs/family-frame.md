# Family Frame 1.2.0

Use the remote left/right for previous/next, OK for pause/resume and up/down for the playback menu. Clicking the displayed media also opens the menu. Back closes the menu (then exits the app). Opening the menu pauses playback; select Continue to resume. Photo interval is 5–120 seconds in five-second increments, videos play to completion. Choose all media, photos only, or videos only; shuffle or sequential order; optional clock. Local playback preferences persist in the TV's application storage.

Rotate either direction in 90-degree steps. Save rotation stores display orientation separately on the Pi, with no changes to original media and no video transcoding. Unsaved rotation is discarded when changing files. Delete requires confirmation and hides the item from playback; restore recovers the most recently hidden item. No original file is physically deleted. USB remains read-only.

Source contains no album content or metadata. Materialize family-frame to generate a separate local edit key, and deploy the app and server together. The authenticated edit endpoint accepts only requests from the configured TV, with an allowlisted operation and known media ID. Runtime orientation/hidden state is local-only under the user's configuration directory. Original upload service remains independent.

Run python3 services/family-frame/test_edits.py for isolated synthetic API tests. Real-TV rendering and remote operation require manual verification.
