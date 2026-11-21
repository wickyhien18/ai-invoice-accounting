#!/bin/sh
# Gom ma ai-service + file rieng cua Space vao thu muc ../hf-space-build, san sang de push len Space.
set -e
cd "$(dirname "$0")/.."
OUT=../hf-space-build
rm -rf "$OUT" && mkdir -p "$OUT"
cp -r app data models "$OUT"/
find "$OUT" -name __pycache__ -type d -prune -exec rm -rf {} +
cp hf-space/README.md hf-space/app.py hf-space/packages.txt hf-space/requirements.txt "$OUT"/
echo "Da tao $OUT:"; ls "$OUT"
