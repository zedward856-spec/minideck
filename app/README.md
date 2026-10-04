# Minideck — offline Android viewer

A 3D viewer for the Minideck (`com.zedward.minideck`). It shows the deck with a parts on/off toggle.
Drag to orbit, pinch to zoom, use two fingers to pan, and tap RESET to frame it again. The LID slider opens the lid from 0° to 180°. Fully offline:
there is no INTERNET permission. Dark only. Loading plays the Optic animation.

- `./build.sh` (from anywhere: `app/build.sh`) builds `build/minideck.apk`; `./build.sh install` also installs it and launches it on the POCO F1.
- `web/`: the app page (`index.html`, `viewer.js`, `viewer.css`, `parts-panel.*`, `optic-loading.mp4`).
- `vendor/`: three.js r170 (core, GLTFLoader, OrbitControls, RoomEnvironment, BufferGeometryUtils) and the fonts.
- `sync_site.py` bundles `web/` + `vendor/` with the deck assets from `~/minideck-site/assets`
  (minideck.glb, parts.json, legends.png, screen.mp4). Re-run the build after re-exporting the model.
- `AssetClient.java` serves the bundle from `https://appassets.androidplatform.net/` and blocks everything else.
