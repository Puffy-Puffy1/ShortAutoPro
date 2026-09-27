# Render Engine V2

Canonical renderer boundary:

Media Acquisition -> Media Validation -> Frozen Render Job -> Remotion -> FFmpeg -> FFprobe -> Quality Gate -> Atomic Commit.

The Python entrypoint is `../render_engine_v2.py --short-id <SHORT_ID>`.

Each render job is isolated under `render_jobs/<SHORT_ID>/<render_id>/` and freezes local assets before rendering. The renderer never calls media providers.

Required runtime:
- Node.js/npm
- Remotion 4.0.529
- FFmpeg
- FFprobe
- compatible Chromium for server-side Remotion rendering

The repository CI runs a real Ubuntu smoke render. Termux/Android remains a separate production qualification because Remotion documents Linux system requirements that do not establish Android/Termux compatibility.

Canonical mode: `RENDER_ENGINE=v2`.
Temporary rollback: `RENDER_ENGINE=legacy`.
