# MINIDECK — promo site

Live: **https://zedward856-spec.github.io/minideck-site/**

Product page for the Minideck pocket cyberdeck. It's a static three.js site: the deck assembles on load, and scrolling tears it down, swings the lid through 180° and cycles the six colour palettes. Tap or drag the deck to spin it or blow it apart.

- `index.html`, `style.css`, `main.js`: the page (three.js from jsDelivr, no build step)
- `assets/minideck.glb`, `assets/parts.json`: web meshes and part metadata, exported from the CAD project by `site_export.py`
- `assets/screen.mp4`: the Optic loading animation on the screen

Run locally: `python3 -m http.server` and open http://localhost:8000.

© 2026 zedward
