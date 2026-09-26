#!/usr/bin/env bash
# Pack references/private/ into a timestamped archive for offsite backup.
# Usage:
#   bash backup_private.sh              -> backups/private-<timestamp>.tar.gz
#   bash backup_private.sh --encrypt    -> AES-256 encrypted .tar.gz.enc
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PRIVATE_DIR="$PROJECT_ROOT/references/private"
BACKUP_DIR="$PROJECT_ROOT/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$BACKUP_DIR/private-$STAMP.tar.gz"

if [ ! -d "$PRIVATE_DIR" ]; then
  echo "error: $PRIVATE_DIR not found" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
tar -czf "$ARCHIVE" -C "$PROJECT_ROOT/references" private
echo "Created: $ARCHIVE"

if [ "${1:-}" = "--encrypt" ]; then
  openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
    -in "$ARCHIVE" -out "$ARCHIVE.enc"
  rm -f "$ARCHIVE"
  echo "Encrypted: $ARCHIVE.enc"
  echo "Restore: openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in <file>.enc -out <file>.tar.gz"
fi

echo "Copy the archive to cloud storage or another machine; backups/ stays out of git."
