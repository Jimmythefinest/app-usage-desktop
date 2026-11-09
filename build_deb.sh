#!/bin/bash
set -euo pipefail

echo "=== Building App Usage CLI Debian Package ==="

echo "Cleaning previous build..."
rm -rf build dist app-usage.spec

echo "Running PyInstaller..."
pyinstaller --onefile --name app-usage \
  --hidden-import dbus_next --hidden-import dbus_next.aio \
  --hidden-import tkinter --hidden-import tkinter.scrolledtext \
  app_usage_cli/cli.py

echo "Preparing .deb structure..."
VERSION="0.3.0"
DEB_DIR="dist/app-usage_${VERSION}_amd64"

mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/usr/bin" "$DEB_DIR/usr/share/applications"

cp dist/app-usage "$DEB_DIR/usr/bin/"
chmod +x "$DEB_DIR/usr/bin/app-usage"

cat > "$DEB_DIR/usr/share/applications/app-usage.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=App Usage
Comment=Join your company and see what is shared
Exec=/usr/bin/app-usage gui
Icon=preferences-system-time
Terminal=false
Categories=Utility;
EOF

cat > "$DEB_DIR/DEBIAN/control" <<EOF
Package: app-usage
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Depends: xdotool, xprintidle
Maintainer: Jimmy <jimjoe1266@gmail.com>
Description: App Usage company activity agent
 Records foreground application usage and uploads summaries to your
 company server after you join. Open "App Usage" from the menu, or see: app-usage --help.
EOF

echo "Building .deb package..."
dpkg-deb --build "$DEB_DIR"

echo "=== Done! ==="
echo "Install with:"
echo "  sudo dpkg -i dist/app-usage_${VERSION}_amd64.deb"