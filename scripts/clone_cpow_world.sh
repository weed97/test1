#!/usr/bin/env bash
# Clone CPoW World — prefers weed97/cpow-world, falls back to test1 export branch.
set -euo pipefail
DEST="${1:-../cpow-world}"
CPOW_REPO="https://github.com/weed97/cpow-world.git"
EXPORT_REPO="https://github.com/weed97/test1.git"
EXPORT_BRANCH="cpow-world"

if [[ -d "$DEST/.git" ]]; then
  echo "Already exists: $DEST (git repo)"
  exit 1
fi

if git ls-remote "$CPOW_REPO" refs/heads/main 2>/dev/null | grep -q .; then
  git clone "$CPOW_REPO" "$DEST"
  echo "Cloned $CPOW_REPO -> $DEST"
else
  echo "cpow-world repo empty — cloning test1/$EXPORT_BRANCH export branch..."
  git clone -b "$EXPORT_BRANCH" "$EXPORT_REPO" "$DEST"
  echo "Cloned $EXPORT_BRANCH -> $DEST"
  echo "To publish: cd $DEST && git remote set-url origin $CPOW_REPO && git branch -M main && git push -u origin main"
fi

echo "  cd $DEST && pip install -r requirements-api.txt && bash scripts/verify.sh"
