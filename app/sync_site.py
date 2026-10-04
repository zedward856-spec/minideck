#!/usr/bin/env python3
"""Bundle the app viewer (web/) with the deck assets from ~/minideck-site into build/assets/www."""
import re, shutil, sys
from pathlib import Path

APP = Path(__file__).resolve().parent
SITE = Path.home() / "minideck-site"
WWW = APP / "build/assets/www"

shutil.rmtree(WWW, ignore_errors=True)
(WWW / "assets").mkdir(parents=True)
for f in ("minideck.glb", "parts.json", "legends.png", "screen.mp4"):
    shutil.copy2(SITE / "assets" / f, WWW / "assets" / f)
shutil.copytree(APP / "vendor", WWW / "vendor")
for f in (APP / "web").iterdir():
    shutil.copy2(f, WWW / f.name)

# offline check: nothing may point at the web
for f in WWW.glob("*.*"):
    if f.suffix in (".html", ".js", ".css"):
        left = re.findall(r'https?://[^"\'\s)]+', f.read_text())
        if left:
            sys.exit(f"sync_site: external URLs in {f.name}: {left}")
print(f"bundled web/ + {SITE}/assets -> {WWW.relative_to(APP)}")
