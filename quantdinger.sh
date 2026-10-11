#!/usr/bin/env bash
# Convenience entrypoint for the local non-Docker launcher.
set -e
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/scripts/quantdinger.sh" "$@"
