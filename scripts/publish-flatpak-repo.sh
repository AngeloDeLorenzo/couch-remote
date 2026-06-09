#!/usr/bin/env bash
# Build, GPG-sign and publish the Couch Remote Flatpak repository to the
# gh-pages branch. This is the reliable, supported way to refresh the repo:
# it runs on a machine where Flatpak already works.
#
# Requirements: flatpak, org.flatpak.Builder, git, and the local signing key
# (default name "Couch Remote Flatpak Repo"). Run from anywhere inside the repo.
#
#   ./scripts/publish-flatpak-repo.sh
#
set -euo pipefail

APP_ID="io.github.angelodelorenzo.couch-remote"
MANIFEST="packaging/flatpak/${APP_ID}.yml"
PAGES_URL="https://angelodelorenzo.github.io/couch-remote"
RUNTIME_REPO="https://dl.flathub.org/repo/flathub.flatpakrepo"
KEY_NAME="${FLATPAK_SIGN_KEY:-Couch Remote Flatpak Repo}"

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

KEYID="$(gpg --list-keys --with-colons "$KEY_NAME" | awk -F: '/^fpr:/{print $10; exit}')"
[ -n "$KEYID" ] || { echo "Signing key '$KEY_NAME' not found in the GPG keyring." >&2; exit 1; }
echo "Signing with $KEYID"

# Work under the repo (not /tmp): org.flatpak.Builder is sandboxed and cannot
# see the host's private /tmp, so the ostree repo must live somewhere it can reach.
WORK="$ROOT/.flatpak-publish"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK" "$ROOT/.flatpak-builder"' EXIT
SITE="$WORK/site"
mkdir -p "$SITE"

echo "Building and signing the ostree repository..."
flatpak run org.flatpak.Builder --force-clean --repo="$SITE/repo" "$WORK/build" "$MANIFEST"
flatpak build-sign "$SITE/repo" --gpg-sign="$KEYID" "$APP_ID"
flatpak build-update-repo "$SITE/repo" --gpg-sign="$KEYID" --generate-static-deltas --prune

echo "Assembling the site..."
cp packaging/flatpak-repo/index.html "$SITE/index.html"
touch "$SITE/.nojekyll"
gpg --export "$KEYID" > "$SITE/couch-remote.gpg"
GPGKEY="$(base64 -w0 "$SITE/couch-remote.gpg")"

cat > "$SITE/couch-remote.flatpakref" <<EOF
[Flatpak Ref]
Name=$APP_ID
Branch=master
Title=Couch Remote
Url=$PAGES_URL/repo
SuggestRemoteName=couch-remote
IsRuntime=false
GPGKey=$GPGKEY
RuntimeRepo=$RUNTIME_REPO
EOF

cat > "$SITE/couch-remote.flatpakrepo" <<EOF
[Flatpak Repo]
Title=Couch Remote
Url=$PAGES_URL/repo
Homepage=https://github.com/AngeloDeLorenzo/couch-remote
Comment=Couch Remote Flatpak repository (Android TV / Google TV remote)
GPGKey=$GPGKEY
EOF

echo "Publishing to gh-pages..."
REMOTE_URL="$(git remote get-url origin)"
PUB="$WORK/pages"
if git clone -q --branch gh-pages "$REMOTE_URL" "$PUB" 2>/dev/null; then
  rm -rf "${PUB:?}/repo" "$PUB"/*.flatpakref "$PUB"/*.flatpakrepo "$PUB"/*.gpg "$PUB"/index.html
else
  mkdir -p "$PUB"
  git -C "$PUB" init -q
  git -C "$PUB" checkout -q -b gh-pages
  git -C "$PUB" remote add origin "$REMOTE_URL"
fi
cp -a "$SITE"/. "$PUB"/
git -C "$PUB" add -A
if git -C "$PUB" commit -q -m "Publish Flatpak repository ($(date -u +%Y-%m-%d))"; then
  git -C "$PUB" push origin gh-pages
  echo "Published to $PAGES_URL"
else
  echo "Nothing to publish (repository unchanged)."
fi
