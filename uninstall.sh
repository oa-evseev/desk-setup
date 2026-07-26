#!/usr/bin/env bash

set -euo pipefail


usage() {
    echo "Usage: $0 [--purge]" >&2
}


PURGE=false

case "${1:-}" in
    "")
        ;;
    --purge)
        PURGE=true
        ;;
    *)
        usage
        exit 2
        ;;
esac

if [[ $# -gt 1 ]]; then
    usage
    exit 2
fi

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"

APP_DIR="$DATA_HOME/desk-setup"
CONFIG_DIR="$CONFIG_HOME/desk-setup"
WRAPPER="$BIN_HOME/desk-setup"

if [[ -e "$APP_DIR" ]]; then
    rm -rf -- "$APP_DIR"
    echo "Removed application: $APP_DIR"
else
    echo "Application is not installed: $APP_DIR"
fi

if [[ -e "$WRAPPER" || -L "$WRAPPER" ]]; then
    rm -- "$WRAPPER"
    echo "Removed command: $WRAPPER"
fi

if [[ "$PURGE" == true ]]; then
    if [[ -e "$CONFIG_DIR" ]]; then
        rm -rf -- "$CONFIG_DIR"
        echo "Removed configurations: $CONFIG_DIR"
    fi
else
    echo "User configurations preserved: $CONFIG_DIR"
    echo "Run uninstall.sh --purge to remove them."
fi
