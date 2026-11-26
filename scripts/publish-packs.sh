#!/bin/sh
# Upload content/dist/<course>/ packs as packs.tar.gz to the `packs` GitHub release, where
# hosts that build from git (Vercel, via PACKS_URL in vercel.json) download them.
# Run after `cd content && uv run pipeline pack ko-en`.
set -eu
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# COPYFILE_DISABLE: no macOS ._ metadata files in the archive.
COPYFILE_DISABLE=1 tar -czf "$tmp/packs.tar.gz" -C content/dist .
if gh release view packs >/dev/null 2>&1; then
	gh release upload packs "$tmp/packs.tar.gz" --clobber
else
	gh release create packs "$tmp/packs.tar.gz" --prerelease --title "Course packs" \
		--notes "Built course packs (CC BY-SA 4.0, sources and licenses in each manifest.json). Updated by npm run publish-packs."
fi
echo "published: https://github.com/Mqdd27/boso/releases/download/packs/packs.tar.gz"
