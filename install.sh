#!/usr/bin/env bash

set -euo pipefail


SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"

APP_DIR="$DATA_HOME/desk-setup"
CONFIG_DIR="$CONFIG_HOME/desk-setup"
WRAPPER="$BIN_HOME/desk-setup"


require_command() {
    local command_name="$1"
    local description="$2"

    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Missing required command: $command_name ($description)" >&2
        exit 1
    fi
}


if [[ "$(uname -s)" != "Linux" ]]; then
    echo "desk-setup currently supports Linux only." >&2
    exit 1
fi

require_command python3 "Python 3 with the venv module"

if ! command -v qdbus6 >/dev/null 2>&1 \
    && ! command -v qdbus >/dev/null 2>&1; then
    echo "Missing qdbus6 or qdbus; install the KDE Qt D-Bus CLI tools." >&2
    exit 1
fi

mkdir -p "$DATA_HOME" "$CONFIG_DIR" "$BIN_HOME"

STAGING_DIR="$(
    mktemp -d "$DATA_HOME/.desk-setup-install.XXXXXX"
)"

cleanup() {
    if [[ -d "$STAGING_DIR" ]]; then
        rm -rf -- "$STAGING_DIR"
    fi
}

trap cleanup EXIT

cp -R -- "$SCRIPT_DIR/src" "$STAGING_DIR/src"
cp -- \
    "$SCRIPT_DIR/requirements.txt" \
    "$SCRIPT_DIR/README.md" \
    "$SCRIPT_DIR/LICENSE" \
    "$SCRIPT_DIR/uninstall.sh" \
    "$STAGING_DIR/"
chmod 755 "$STAGING_DIR/uninstall.sh"

python3 -m venv "$STAGING_DIR/.venv"
"$STAGING_DIR/.venv/bin/python" -m pip install \
    --upgrade pip
"$STAGING_DIR/.venv/bin/python" -m pip install \
    -r "$STAGING_DIR/requirements.txt"

BACKUP_DIR=""

if [[ -e "$APP_DIR" ]]; then
    BACKUP_DIR="${APP_DIR}.previous.$$"
    mv -- "$APP_DIR" "$BACKUP_DIR"
fi

if ! mv -- "$STAGING_DIR" "$APP_DIR"; then
    if [[ -n "$BACKUP_DIR" && -e "$BACKUP_DIR" ]]; then
        mv -- "$BACKUP_DIR" "$APP_DIR"
    fi

    exit 1
fi

if [[ -n "$BACKUP_DIR" && -e "$BACKUP_DIR" ]]; then
    rm -rf -- "$BACKUP_DIR"
fi

WRAPPER_TEMP="${WRAPPER}.tmp.$$"
printf '#!/usr/bin/env bash\n' > "$WRAPPER_TEMP"
printf 'export PYTHONPATH=%q\n' "$APP_DIR" >> "$WRAPPER_TEMP"
printf 'exec %q -m src.main "$@"\n' \
    "$APP_DIR/.venv/bin/python" >> "$WRAPPER_TEMP"
chmod 755 "$WRAPPER_TEMP"
mv -- "$WRAPPER_TEMP" "$WRAPPER"

for example in "$SCRIPT_DIR"/examples/*.yaml; do
    destination="$CONFIG_DIR/$(basename -- "$example")"

    if [[ ! -e "$destination" ]]; then
        cp -- "$example" "$destination"
        echo "Created configuration: $destination"
    else
        echo "Preserved configuration: $destination"
    fi
done

echo
echo "Installation complete."
echo "Application: $APP_DIR"
echo "Command:     $WRAPPER"
echo "Configs:     $CONFIG_DIR"

case ":$PATH:" in
    *":$BIN_HOME:"*)
        ;;
    *)
        echo
        echo "Add $BIN_HOME to PATH to run desk-setup directly."
        ;;
esac
