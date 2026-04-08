#!/usr/bin/env bash
set -euo pipefail

TMP_DIR="${TMP_MEDIA_ROOT:-/code/static_media/tmp}"

mkdir -p "$TMP_DIR"
find "$TMP_DIR" -type f -mtime +1 -delete
find "$TMP_DIR" -type d -mindepth 1 -empty -delete
