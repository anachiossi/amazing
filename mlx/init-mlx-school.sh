#!/usr/bin/env bash
# Set up the MinilibX python wrapper on a 42 school machine.
#
#   bash ./mlx/init-mlx-school.sh [-f] [-c] [-l] [venv_path]
#   source ./mlx/init-mlx-school.sh [-f] [-c] [-l] [venv_path]
#
#   -f   rebuild the venv from scratch even if one is already there
#   -c   check only: report what is missing, install and build nothing
#   -l   skip sudo entirely and put the missing libraries in the venv
#
# Detects the distribution (Fedora or Debian/Ubuntu) and installs the
# missing system libraries with dnf or apt. School machines usually do
# not grant root: when sudo is missing or refused, the script falls back
# on downloading the packages and unpacking them inside the venv, which
# needs no privileges at all.

# Are we being sourced? The test differs per shell, and zsh needs its own
# branch because BASH_SOURCE does not exist there.
_mlx_sourced=0
if [ -n "${ZSH_VERSION:-}" ]; then
    case "${ZSH_EVAL_CONTEXT:-}" in *:file*) _mlx_sourced=1 ;; esac
elif [ -n "${BASH_VERSION:-}" ]; then
    [ "${BASH_SOURCE[0]}" != "$0" ] && _mlx_sourced=1
fi

# Path of this script, captured at top level on purpose: inside a zsh
# function $0 is the function's name, not the file, so resolving it any
# deeper than here gives the wrong directory.
_MLX_SELF="${BASH_SOURCE[0]:-$0}"

# Distro family, from /etc/os-release. Read in a subshell so ID and
# ID_LIKE do not leak into the caller's environment.
_mlx_family() {
    (
        [ -r /etc/os-release ] && . /etc/os-release
        case " ${ID:-} ${ID_LIKE:-} " in
            *debian*|*ubuntu*)        echo debian ;;
            *fedora*|*rhel*|*centos*) echo fedora ;;
            *)                        echo unknown ;;
        esac
    )
}

# Download packages and unpack them under $2/lib without root, then make
# the venv export LD_LIBRARY_PATH so libmlx.so finds them.
_mlx_local_libs() {
    local family="$1" venv="$2" libdir="$3" pkgs="$4" work pkg
    work="$(mktemp -d)" || return 1
    mkdir -p "$libdir" || { rm -rf "$work"; return 1; }

    case "$family" in
        debian)
            command -v dpkg-deb >/dev/null || {
                mlx_err "dpkg-deb not available, cannot unpack locally"
                rm -rf "$work"; return 1; }
            ( cd "$work" && apt-get download $pkgs >/dev/null 2>&1 ) || {
                mlx_err "apt-get download failed for: $(echo $pkgs)"
                rm -rf "$work"; return 1; }
            for pkg in "$work"/*.deb; do
                [ -f "$pkg" ] || continue
                dpkg-deb -x "$pkg" "$work/root" || { rm -rf "$work"; return 1; }
            done
            ;;
        fedora)
            command -v rpm2cpio >/dev/null && command -v cpio >/dev/null || {
                mlx_err "rpm2cpio/cpio not available, cannot unpack locally"
                rm -rf "$work"; return 1; }
            ( cd "$work" && dnf download $pkgs >/dev/null 2>&1 ) || {
                mlx_err "dnf download failed for: $(echo $pkgs)"
                mlx_err "it needs the dnf-plugins-core package"
                rm -rf "$work"; return 1; }
            mkdir -p "$work/root"
            for pkg in "$work"/*.rpm; do
                [ -f "$pkg" ] || continue
                ( cd "$work/root" && rpm2cpio "$pkg" | cpio -idmu \
                    >/dev/null 2>&1 ) || { rm -rf "$work"; return 1; }
            done
            ;;
        *)
            mlx_err "unknown distro, cannot download packages"
            rm -rf "$work"; return 1 ;;
    esac

    find "$work/root" -name 'lib*.so*' -exec cp -a {} "$libdir/" \; \
        2>/dev/null
    rm -rf "$work"
    [ -n "$(ls -A "$libdir" 2>/dev/null)" ] || {
        mlx_err "nothing was extracted into $libdir"; return 1; }

    export LD_LIBRARY_PATH="$libdir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    # Make it stick for anyone who activates the venv later.
    if [ -f "$venv/bin/activate" ] \
       && ! grep -q 'added by init-mlx-school' "$venv/bin/activate"; then
        cat >> "$venv/bin/activate" <<ACTIVATE

# added by init-mlx-school.sh — libmlx.so needs these local libraries
export LD_LIBRARY_PATH="$libdir\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
ACTIVATE
    fi
    mlx_say "libraries unpacked into $libdir"
    return 0
}

_mlx_school_main() {
    local here root tarball venv libdir force check local_only
    local tmp family flavour missing installer

    # zsh does not word-split unquoted parameters; this script relies on
    # sh semantics throughout. local_options confines the change to this
    # function and its callees, so the user's shell keeps its settings.
    if [ -n "${ZSH_VERSION:-}" ]; then
        setopt local_options sh_word_split
    fi

    here="$(cd "$(dirname "$_MLX_SELF")" && pwd)" || return 1
    # shellcheck source=lib-mlx-common.sh
    . "$here/lib-mlx-common.sh" || {
        printf 'error: cannot find lib-mlx-common.sh next to this script\n' >&2
        return 1
    }
    root="$(cd "$here/.." && pwd)"
    tarball="$root/subject/mlx-2.2.tgz"

    force=0; check=0; local_only=0
    while [ $# -gt 0 ]; do
        case "$1" in
            -f) force=1; shift ;;
            -c) check=1; shift ;;
            -l) local_only=1; shift ;;
            -h|--help) sed -n '2,17p' "$here/init-mlx-school.sh"; return 0 ;;
            *)  break ;;
        esac
    done
    venv="${1:-$here/venv}"
    libdir="$venv/mlx-libs"
    _MLX_VENV="$venv"

    [ -f "$tarball" ] || { mlx_err "missing $tarball"; return 1; }

    family="$(_mlx_family)"
    case "$family" in
        debian) installer="apt-get" ;;
        fedora) installer="dnf" ;;
        *) mlx_err "unrecognised distribution — check /etc/os-release"
           return 1 ;;
    esac
    mlx_say "distribution family: $family (package manager: $installer)"
    # On Fedora the fedora build is the one likely to load; try it first.
    [ "$family" = fedora ] && MLX_FLAVOUR_ORDER="fedora ubuntu"

    if [ "$force" -eq 0 ] && [ -d "$venv" ] && mlx_verify_venv "$venv"; then
        mlx_say "reusing existing venv $venv"
        return 0
    fi

    tmp="$(mktemp -d)" || return 1
    mlx_say "unpacking $(basename "$tarball")"
    mlx_unpack_all "$tmp" "$tarball" || { rm -rf "$tmp"; return 1; }

    mlx_collect_missing "$tmp" "$family"
    missing="$MLX_MISSING_PKGS"

    if [ -z "$missing" ]; then
        mlx_say "all system libraries are present"
    else
        mlx_say "missing system packages:"
        printf '      %s\n' $missing
        if [ "$check" -eq 1 ]; then
            mlx_say "check only. With root you would install them with:"
            if [ "$family" = debian ]; then
                printf '      sudo apt-get install -y %s\n' "$(echo $missing)"
            else
                printf '      sudo dnf install -y %s\n' "$(echo $missing)"
            fi
            printf '      without root, re-run this script with -l\n'
            rm -rf "$tmp"
            return 1
        fi

        local installed=0
        if [ "$local_only" -eq 0 ] && command -v sudo >/dev/null; then
            mlx_say "trying to install with sudo $installer"
            if [ "$family" = debian ]; then
                sudo apt-get update -qq >/dev/null 2>&1
                sudo apt-get install -y $missing >/dev/null 2>&1 && installed=1
            else
                sudo dnf install -y $missing >/dev/null 2>&1 && installed=1
            fi
        fi

        if [ "$installed" -eq 0 ]; then
            [ "$local_only" -eq 1 ] \
                && mlx_say "-l given: skipping sudo, unpacking locally" \
                || mlx_warn "no root here — falling back to local libraries"
            mkdir -p "$venv" 2>/dev/null
            _mlx_local_libs "$family" "$venv" "$libdir" "$missing" || {
                mlx_err "could not provide the missing libraries."
                mlx_err "ask staff to install: $(echo $missing)"
                rm -rf "$tmp"
                return 1
            }
        else
            mlx_say "packages installed"
        fi
    fi

    if [ "$check" -eq 1 ]; then
        mlx_say "check only — nothing was built"
        rm -rf "$tmp"
        return 0
    fi

    if [ -d "$venv" ] && [ "$force" -eq 1 ]; then
        mlx_say "removing $venv"
        rm -rf "$venv"
        # the local libs lived inside it, put them back if we made them
        [ -d "$libdir" ] || mkdir -p "$libdir" 2>/dev/null
    fi

    mlx_say "building venv $venv"
    flavour="$(mlx_build_venv "$venv" "$tmp")" || {
        mlx_err "neither wheel loads. Re-run with -c to see what is missing."
        rm -rf "$tmp"
        return 1
    }
    rm -rf "$tmp"

    mlx_verify_venv "$venv" || {
        mlx_err "the $flavour wheel installed but libmlx.so will not load"
        return 1
    }
    mlx_say "mlx 2.2 ($flavour build) installed in $venv"

    if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
        mlx_warn "DISPLAY is unset — no window will open. On a remote"
        mlx_warn "session reconnect with 'ssh -X', or work on the terminal"
        mlx_warn "renderer instead."
    else
        mlx_say "DISPLAY=${DISPLAY:-$WAYLAND_DISPLAY} — windows should open"
    fi
    return 0
}

_mlx_school_main "$@"
_mlx_rc=$?

if [ "$_mlx_rc" -eq 0 ] && [ "$_mlx_sourced" -eq 1 ]; then
    . "$_MLX_VENV/bin/activate"
    printf '==> venv activated — "deactivate" to leave it\n'
elif [ "$_mlx_rc" -eq 0 ]; then
    printf '==> activate it with:  source %s/bin/activate\n' "$_MLX_VENV"
    printf '==> then try:          python mlx/mlx-demo.py\n'
fi

_mlx_was_sourced="$_mlx_sourced"
unset -f _mlx_school_main _mlx_family _mlx_local_libs
unset _mlx_sourced _MLX_VENV

# Propagate the status. A sourced script must return, never exit — exit
# would close the user's shell.
if [ "$_mlx_was_sourced" -eq 1 ]; then
    unset _mlx_was_sourced _MLX_SELF
    return "$_mlx_rc"
fi
unset _mlx_was_sourced _MLX_SELF
exit "$_mlx_rc"
