# Shared helpers for init-mlx-wsl.sh and init-mlx-school.sh.
# Not meant to be run on its own — the wrappers source it.
#
# The flow both wrappers follow:
#   1. unpack subject/mlx-2.2.tgz and both wheels into a temp dir
#   2. ldd each libmlx.so to learn which sonames are missing
#   3. map those sonames to package names and install them
#   4. build the venv from the wheel that actually loads
#   5. verify the load once more from inside the venv

mlx_say()  { printf '==> %s\n' "$*"; }
mlx_warn() { printf 'warning: %s\n' "$*" >&2; }
mlx_err()  { printf 'error: %s\n' "$*" >&2; }

# Unpack a wheel without needing the unzip binary — python3 is already a
# hard requirement here, unzip is not always installed.
mlx_unpack_wheel() {
    python3 - "$1" "$2" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    archive.extractall(sys.argv[2])
PY
}

# The sonames the dynamic linker cannot resolve, one per line.
mlx_missing_sonames() {
    ldd "$1" 2>/dev/null | awk '/not found/ {print $1}'
}

# True when the shared object actually loads.
mlx_so_loads() {
    python3 -c 'import ctypes, sys; ctypes.CDLL(sys.argv[1])' "$1" 2>/dev/null
}

# soname -> package name, per distro family. Anything unmapped is echoed
# back unchanged so the user at least sees the soname in the message.
mlx_package_for() {
    local soname="$1" family="$2"
    case "$family:$soname" in
        debian:libxcb.so.1)          echo libxcb1 ;;
        debian:libxcb-keysyms.so.1)  echo libxcb-keysyms1 ;;
        debian:libvulkan.so.1)       echo libvulkan1 ;;
        debian:libbsd.so.0)          echo libbsd0 ;;
        debian:libz.so.1)            echo zlib1g ;;
        debian:libXau.so.6)          echo libxau6 ;;
        debian:libXdmcp.so.6)        echo libxdmcp6 ;;
        debian:libmd.so.0)           echo libmd0 ;;
        fedora:libxcb.so.1)          echo libxcb ;;
        fedora:libxcb-keysyms.so.1)  echo xcb-util-keysyms ;;
        fedora:libvulkan.so.1)       echo vulkan-loader ;;
        fedora:libbsd.so.0)          echo libbsd ;;
        fedora:libz.so.1)            echo zlib ;;
        fedora:libXau.so.6)          echo libXau ;;
        fedora:libXdmcp.so.6)        echo libXdmcp ;;
        fedora:libmd.so.0)           echo libmd ;;
        *)                           echo "$soname" ;;
    esac
}

# Collect the missing packages for both wheel flavours, deduplicated.
# Sets MLX_MISSING_PKGS as a newline-separated string.
mlx_collect_missing() {
    local unpacked="$1" family="$2" flavour so soname pkg
    local order="${MLX_FLAVOUR_ORDER:-ubuntu fedora}"
    MLX_MISSING_PKGS=""
    for flavour in $order; do
        so="$unpacked/$flavour/mlx/libmlx.so"
        [ -f "$so" ] || continue
        while IFS= read -r soname; do
            [ -n "$soname" ] || continue
            pkg="$(mlx_package_for "$soname" "$family")"
            case "$MLX_MISSING_PKGS" in
                *"$pkg"*) ;;
                *) MLX_MISSING_PKGS="${MLX_MISSING_PKGS}${pkg}"$'\n' ;;
            esac
        done <<< "$(mlx_missing_sonames "$so")"
    done
    MLX_MISSING_PKGS="$(printf '%s' "$MLX_MISSING_PKGS" | sed '/^$/d')"
}

# Unpack the tarball and both wheels into $1. Echoes nothing, returns 1
# on failure.
mlx_unpack_all() {
    local dest="$1" tarball="$2" flavour wheel
    tar xf "$tarball" -C "$dest" || return 1
    for flavour in ubuntu fedora; do
        wheel="$dest/$flavour/mlx-2.2-py3-none-any.whl"
        [ -f "$wheel" ] || continue
        mkdir -p "$dest/$flavour" || return 1
        mlx_unpack_wheel "$wheel" "$dest/$flavour" || return 1
    done
    return 0
}

# Build the venv from whichever flavour loads. Tries ubuntu first.
# $1 venv path, $2 unpacked dir. Echoes the flavour it settled on.
mlx_build_venv() {
    local venv="$1" unpacked="$2" py="${PYTHON:-python3}" flavour wheel
    local order="${MLX_FLAVOUR_ORDER:-ubuntu fedora}"
    "$py" -m venv "$venv" >/dev/null || return 1
    "$venv/bin/pip" install --quiet --upgrade pip >/dev/null || return 1
    for flavour in $order; do
        wheel="$unpacked/$flavour/mlx-2.2-py3-none-any.whl"
        [ -f "$wheel" ] || continue
        [ -f "$unpacked/$flavour/mlx/libmlx.so" ] || continue
        mlx_so_loads "$unpacked/$flavour/mlx/libmlx.so" || continue
        "$venv/bin/pip" install --quiet --force-reinstall "$wheel" \
            >/dev/null || continue
        echo "$flavour"
        return 0
    done
    return 1
}

# Load libmlx.so through the venv's own interpreter — the real proof.
mlx_verify_venv() {
    "$1/bin/python" - <<'PY' 2>/dev/null
import ctypes, os, mlx
ctypes.CDLL(os.path.join(os.path.dirname(mlx.__file__), "libmlx.so"))
PY
}
