#!/usr/bin/env bash
set -euo pipefail
[ "$(uname -s)" = Darwin ] || { printf '%s\n' 'Docker Desktop auto-install is only available on macOS.' >&2; exit 1; }
case "$(uname -m)" in arm64) arch=arm64 ;; x86_64) arch=amd64 ;; *) exit 1 ;; esac
destination="$HOME/Applications/Docker.app"
[ ! -e "$destination" ] || { printf '%s\n' 'Docker.app already exists; install was left unchanged.'; exit 0; }
tmp="$(mktemp -d -t foliolet-docker)"
mounted=0
cleanup() { if [ "$mounted" = 1 ]; then hdiutil detach "$tmp/mount" -quiet || true; fi; rm -f "$tmp/Docker.dmg"; rmdir "$tmp/mount" "$tmp" 2>/dev/null || true; }
trap cleanup EXIT
printf '%s\n' 'Downloading Docker Desktop from the official Docker distribution (first run only)...'
curl --fail --location --proto '=https' --tlsv1.2 --retry 3 --output "$tmp/Docker.dmg" "https://desktop.docker.com/mac/main/$arch/Docker.dmg"
mkdir "$tmp/mount"
hdiutil attach "$tmp/Docker.dmg" -mountpoint "$tmp/mount" -nobrowse -quiet
mounted=1
codesign --verify --deep --strict "$tmp/mount/Docker.app"
spctl --assess --type execute "$tmp/mount/Docker.app"
mkdir -p "$HOME/Applications"
ditto "$tmp/mount/Docker.app" "$destination"
printf '%s\n' 'Docker Desktop installed in your Applications folder. Its first launch may ask for OS permissions/licence acceptance.'
