#!/usr/bin/env bash
# Clone the standalone cpow-world branch into a sibling directory.
set -euo pipefail
DEST="${1:-../cpow-world}"
REPO="${CPOW_EXPORT_REPO:-https://github.com/weed97/test1.git}"
BRANCH="${CPOW_EXPORT_BRANCH:-cpow-world}"

if [[ -d "$DEST/.git" ]]; then
  echo "Already exists: $DEST (git repo)"
  exit 1
fi

git clone -b "$BRANCH" "$REPO" "$DEST"
echo "Cloned $BRANCH -> $DEST"
echo "  cd $DEST && pip install -r requirements-api.txt && bash scripts/verify.sh"
