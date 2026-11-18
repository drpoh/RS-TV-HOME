# Native LG SmartShare trial (webOS 1.4)

Target: legacy LG webOS 1.4 TV. Diagnostic experiment, not a production feature.
The installed RS Family Frame 1.2.4 remains the primary player.

## Results

- The native player is com.webos.app.smartshare. Launched via ares-launch with
  DLNA-compatible HTTP media parameters; it streams from the existing Pi
  media service. The USB source remains mounted read-only.
- The TV advertises UPnP MediaRenderer and AVTransport. GetTransportInfo with
  InstanceID=0 reports STOPPED, then PLAYING, then STOPPED on completion.
  GetPositionInfo returns zero for duration/time on this old firmware.
- A 10-second clip ended and the Pi automatically reopened Family Frame upon
  the actual PLAYING -> STOPPED transition. Foreground app confirmed.
- A 25-second clip changed to STOPPED about 34 seconds after launch.
- A 50.6-second H.264 clip remained PLAYING and changed to STOPPED about
  59 seconds after launch. The frame was reopened successfully.
- The largest 65.5-second clip failed to start a network transfer during the
  initial trial. Native compatibility has not been validated across the album.
- No rotation operation is exposed in the TV's AVTransport and RenderingControl
  action lists. A metadata-only rotated MP4 or transcoded display copy needs
  visual verification. The HTML5 frame's CSS rotation does not apply to native
  SmartShare playback.
- STOPPED may also mean user stop or an error. Production hybrid logic needs
  safeguards for incomplete playback, alternative TV app launches, power state,
  and playlist state restoration.

## One-off diagnostic test

From the project root:

    ~/lg-webos-tools/magic-remote/.venv/bin/python scripts/smartshare_probe.py --rank 2

Rank 1 selects the largest video; rank 2 the second largest. The probe uses
read-only AVTransport queries and the existing allowlisted HTTP media service.
It switches apps only for the diagnostic and always attempts to restore the
family frame. The original video and photo files are never modified.

## Rotation experiment (2026-11-18)

The private temporary test cache was created under the home-directory
.cache/rs-smartshare-rotation path. On one source H.264 clip with 720x1280
encoded pixels and no existing display matrix:

- A stream-copy produced an MP4 with -90-degree (clockwise) display metadata,
  preserving 720x1280 encoded pixels and the video/audio streams.
- A separate H.264 transcode using -noautorotate -vf transpose=clock
  produced physically rotated 1280x720 video with no display-rotation metadata.
  The short sample took approximately 16 seconds on Raspberry Pi 3.
- Both files were streamed through an isolated, read-only, allowlisted HTTP
  Range test server. Native SmartShare reached PLAYING and STOPPED for both,
  accepted the data, and Family Frame was restored after each test.
- This proves media compatibility and correct MP4 metadata on the Pi, but
  not what orientation the legacy LG actually displayed. There is no remote
  TV screenshot/rotation report from the native player. The visually correct
  orientation must be verified before changing all videos.
- The one-off test server has no persistent service or production endpoint.
- Tested scripts/test_smartshare_rotation_probe.py (synthetic
  range/security checks).

Audit of the 212 source MP4 files by ffprobe video tracks:
196 H.264, 16 HEVC. Display matrix: 189 have -90 degrees, 18 have 0/no matrix,
4 have +90, and 1 has -180. Thus a global extra clockwise quarter-turn must
be added to each existing orientation if using metadata, rather than
unconditionally replacing all matrices with -90. HEVC native compatibility on
the 2014 LG remains unverified. Don't mass-transcode on the Pi 3 until native
display orientation and throughput are confirmed.
