#!/bin/bash
set -euo pipefail

echo "=== Building App Usage CLI Debian Package ==="

echo "Cleaning previous build..."
rm -rf build dist app-usage.spec

echo "Running PyInstaller..."
pyinstaller --onefile --name app-usage app_usage_cli/cli.py

echo "Preparing .deb structure..."
VERSION="0.1.0"
DEB_DIR="dist/app-usage_${VERSION}_amd64"

mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/usr/bin"

cp dist/app-usage "$DEB_DIR/usr/bin/"
chmod +x "$DEB_DIR/usr/bin/app-usage"

cat > "$DEB_DIR/DEBIAN/control" <<EOF
Package: app-usage
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Depends: xdotool, xprintidle
Maintainer: Jimmy <jimjoe1266@gmail.com>
Description: App Usage Tracking CLI
 A cross-platform app usage tracker that logs active window focus,
 idle time, and shell commands, exporting to Obsidian.
EOF

echo "Building .deb package..."
dpkg-deb --build "$DEB_DIR"

echo "=== Done! ==="
echo "Install with:"
echo "  sudo dpkg -i dist/app-usage_${VERSION}_amd64.deb"