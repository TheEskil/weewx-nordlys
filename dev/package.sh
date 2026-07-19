#!/usr/bin/env bash
# Builds the installable weewx extension zip into release/.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION=$(node -p "require('./package.json').version")
OUT="release/weewx-nordlys-$VERSION.zip"

npm run build
node tests/budget.mjs

# weectl extension install requires a single root directory in the zip.
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
ROOT="$STAGE/weewx-nordlys"
mkdir -p "$ROOT/bin/user" "$ROOT/skins"
cp install.py "$ROOT/"
cp -R bin/user/nordlys "$ROOT/bin/user/"
cp -R skins/Nordlys "$ROOT/skins/"
find "$STAGE" -name '.DS_Store' -delete
find "$STAGE" -name '__pycache__' -type d -exec rm -rf {} +

mkdir -p release
rm -f "$OUT"
(cd "$STAGE" && zip -qr - weewx-nordlys) > "$OUT"

echo "Built $OUT:"
unzip -l "$OUT"
