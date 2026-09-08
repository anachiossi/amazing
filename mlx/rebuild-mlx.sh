#!/usr/bin/env bash
# Rebuild MiniLibX 2.2 from subject/mlx-2.2.tgz with the local overlay:
# no 10px white border, KeyPress without auto-repeat, take input focus.
#
#   ./mlx/rebuild-mlx.sh [venv_path]
#
# Default venv is ./mlx/venv. The wheel must already be installed
# (init-mlx.sh does that first).

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/.." && pwd)"
tarball="$root/subject/mlx-2.2.tgz"
overlay="$here/overlay/src/backend"
venv="${1-$here/venv}"

so=""
for candidate in "$venv"/lib/python*/site-packages/mlx/libmlx.so; do
  [ -f "$candidate" ] && so="$candidate" && break
done
if [ -z "$so" ]; then
  echo "rebuild-mlx: no libmlx.so in $venv (run ./mlx/init-mlx.sh first)" >&2
  exit 1
fi
[ -f "$tarball" ] || { echo "rebuild-mlx: missing $tarball" >&2; exit 1; }
[ -d "$overlay" ] || { echo "rebuild-mlx: missing $overlay" >&2; exit 1; }

command -v "${CC:-cc}" >/dev/null || {
  echo "rebuild-mlx: no C compiler (cc or CC=...)" >&2
  exit 1
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "==> unpacking MiniLibX 2.2 sources"
tar xf "$tarball" -C "$tmp"
tar xf "$tmp/src/mlx_CLXV-2.2.tgz" -C "$tmp"
tree="$tmp/mlx_CLXV"
[ -d "$tree/src/backend" ] || {
  echo "rebuild-mlx: unexpected tarball layout" >&2
  exit 1
}

echo "==> applying overlay"
cp -f "$overlay/"*.c "$overlay/"*.h "$tree/src/backend/"

echo "==> compiling libmlx.so"
make -C "$tree" config
make -C "$tree" libmlx.so

echo "==> installing into $so"
cp -f "$tree/libmlx.so" "$so"
echo "==> patched MiniLibX installed"
