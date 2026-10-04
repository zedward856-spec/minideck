#!/usr/bin/env bash
# Build the Minideck offline viewer APK by hand (no gradle). Usage: ./build.sh [install]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BT="$HOME/.local/opt/android-14"          # build-tools 34.0.0
PLAT="$HOME/.local/opt/android-35/android.jar"
JDK="$HOME/.local/opt/jdk"
ADB="$HOME/.local/opt/platform-tools/adb"
POCO=6afe8752
export PATH="$JDK/bin:$PATH"              # d8/apksigner wrappers need `java`

cd "$ROOT"
rm -rf build
mkdir -p build/gen build/classes build/dex

# --- 0. bundle the site, offline-patched ---
python3 sync_site.py

# --- debug keystore (once) ---
if [ ! -f debug.keystore ]; then
  keytool -genkeypair -keystore debug.keystore -storepass android -keypass android \
    -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Android Debug,O=Android,C=US" >/dev/null 2>&1
fi

# --- 1. compile resources ---
"$BT/aapt2" compile --dir res -o build/res.zip

# --- 2. link (base.apk + R.java + assets) ---
"$BT/aapt2" link -o build/base.apk \
  -I "$PLAT" \
  --manifest AndroidManifest.xml \
  --java build/gen \
  -A build/assets -0 mp4 -0 woff2 -0 png \
  --min-sdk-version 26 --target-sdk-version 34 \
  --version-code "$(date +%y%m%d%H)" --version-name 1.0 \
  build/res.zip

# --- 3. compile Java ---
find src build/gen -name '*.java' > build/sources.txt
javac --release 11 -d build/classes -classpath "$PLAT" @build/sources.txt

# --- 4. dex ---
"$BT/d8" --release --min-api 26 --lib "$PLAT" --output build/dex \
  $(find build/classes -name '*.class')

# --- 5. bundle dex into the apk ---
cp build/base.apk build/app-unsigned.apk
"$JDK/bin/jar" --update --file build/app-unsigned.apk -C build/dex classes.dex

# --- 6. align ---
"$BT/zipalign" -f -p 4 build/app-unsigned.apk build/app-aligned.apk

# --- 7. sign ---
"$BT/apksigner" sign --ks debug.keystore --ks-pass pass:android \
  --out build/minideck.apk build/app-aligned.apk

echo "BUILT: $ROOT/build/minideck.apk ($(du -h build/minideck.apk | cut -f1))"

if [ "${1:-}" = install ]; then
  "$ADB" -s "$POCO" install --no-incremental -r build/minideck.apk
  "$ADB" -s "$POCO" shell am start -n com.zedward.minideck/.MainActivity
fi
