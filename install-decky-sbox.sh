#!/bin/sh

set -eu

REPOSITORY="ljm625/decky-sbox"
PLUGINS_DIR="$HOME/homebrew/plugins"
PLUGIN_DIR="$PLUGINS_DIR/decky-sbox"
ARCHIVE=""
STAGING_DIR=""
BACKUP_DIR="$PLUGINS_DIR/.decky-sbox.backup.$$"
LOADER_STOPPED=0

start_plugin_loader() {
    sudo systemctl start plugin_loader > /dev/null 2>&1 || \
        systemctl --user start plugin_loader > /dev/null 2>&1
}

cleanup() {
    if [ -n "$ARCHIVE" ]; then
        rm -f "$ARCHIVE"
    fi
    if [ -n "$STAGING_DIR" ]; then
        rm -rf "$STAGING_DIR"
    fi
    if [ "$LOADER_STOPPED" -eq 1 ]; then
        start_plugin_loader || true
    fi
}

trap cleanup EXIT
trap 'exit 1' HUP INT TERM

echo "Checking the latest Decky Sbox release..."
LATEST_RELEASE_URL=$(curl -fsSL -o /dev/null -w '%{url_effective}' \
    "https://github.com/$REPOSITORY/releases/latest")
LATEST_TAG=${LATEST_RELEASE_URL##*/}

case "$LATEST_TAG" in
    v[0-9]*) ;;
    *)
        echo "Unable to determine the latest release tag: $LATEST_TAG" >&2
        exit 1
        ;;
esac

ASSET_NAME="decky-sbox-$LATEST_TAG.zip"
DOWNLOAD_URL="https://github.com/$REPOSITORY/releases/download/$LATEST_TAG/$ASSET_NAME"
ARCHIVE=$(mktemp /tmp/decky-sbox.XXXXXX)
STAGING_DIR=$(mktemp -d /tmp/decky-sbox-install.XXXXXX)

echo "Downloading Decky Sbox $LATEST_TAG..."
curl -fL --retry 3 --retry-delay 2 -o "$ARCHIVE" "$DOWNLOAD_URL"
unzip -tq "$ARCHIVE" > /dev/null
unzip -q "$ARCHIVE" -d "$STAGING_DIR"

if [ ! -f "$STAGING_DIR/decky-sbox/main.py" ] || \
   [ ! -f "$STAGING_DIR/decky-sbox/plugin.json" ]; then
    echo "The release archive does not contain a valid Decky Sbox plugin." >&2
    exit 1
fi

sudo mkdir -p "$PLUGINS_DIR"
systemctl --user stop plugin_loader > /dev/null 2>&1 || true
sudo systemctl stop plugin_loader > /dev/null 2>&1 || true
LOADER_STOPPED=1

if [ -e "$BACKUP_DIR" ]; then
    sudo rm -rf "$BACKUP_DIR"
fi
if [ -e "$PLUGIN_DIR" ]; then
    echo "Backing up the existing installation..."
    sudo mv "$PLUGIN_DIR" "$BACKUP_DIR"
fi

if ! sudo mv "$STAGING_DIR/decky-sbox" "$PLUGIN_DIR"; then
    echo "Installation failed; restoring the previous version..." >&2
    sudo rm -rf "$PLUGIN_DIR"
    if [ -e "$BACKUP_DIR" ]; then
        sudo mv "$BACKUP_DIR" "$PLUGIN_DIR"
    fi
    exit 1
fi

if [ -e "$BACKUP_DIR" ]; then
    sudo rm -rf "$BACKUP_DIR"
fi

start_plugin_loader
LOADER_STOPPED=0

echo "Decky Sbox $LATEST_TAG is installed."
