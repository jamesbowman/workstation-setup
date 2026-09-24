# shellcheck shell=sh
# Shared entry point, sourced by the launchers. Reject macOS before Python runs.
set -eu
if [ "$(uname -s)" != Linux ]; then
    echo 'Refusing: setup commands run only on Debian 13, never on macOS.' >&2
    exit 1
fi
WS_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec /usr/bin/python3 -I -B "$WS_ROOT/scripts/lib/workstation.py" "$@"
