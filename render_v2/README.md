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

## Termux/Android compatibility bridge

The Termux target uses Android arm64, where the native Rspack binding required by
Remotion 4.0.529 is not available in the standard npm package. Render Engine V2
therefore keeps Remotion's Webpack bundling path on Android and lazy-loads the
optional Rspack module only when Rspack is explicitly requested.

`npm install` runs a version-pinned local compatibility patch for
`@remotion/bundler@4.0.529`. The patch is fail-closed: if the installed bundler
version changes or the expected upstream anchors are missing, installation
fails instead of silently producing an unqualified runtime.

Verify after installation with:

```bash
npm run verify:android-bundle
npx tsc --noEmit
```

This does not claim full Android rendering compatibility. It only removes the
known eager-Rspack load blocker. Final qualification still requires a real
Termux render using FFmpeg/FFprobe and the production Render Engine V2 input.
