#!/usr/bin/env bash
# Set up the MinilibX python wrapper on WSL2 / Ubuntu (this machine).
#
#   bash ./mlx/init-mlx-wsl.sh [-f] [-c] [venv_path]
#   source ./mlx/init-mlx-wsl.sh [-f] [-c] [venv_path]   # also activates
#
#   -f   rebuild the venv from scratch even if one is already there
#   -c   check only: report what is missing, install and build nothing
#
# Installs missing system libraries with apt (asks for sudo), then builds
# the venv from the wheel flavour that actually loads. Default venv path
# is <this script's dir>/venv.
#
# Your login shell is zsh, so prefer 'bash ./mlx/init-mlx-wsl.sh' and then
# 'source mlx/venv/bin/activate' — that activate script is POSIX and works
# in zsh unchanged.

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

_mlx_wsl_main() {
    local here root tarball venv force check tmp flavour missing

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

    force=0
    check=0
    while [ $# -gt 0 ]; do
        case "$1" in
            -f) force=1; shift ;;
            -c) check=1; shift ;;
            -h|--help) sed -n '2,20p' "$here/init-mlx-wsl.sh"; return 0 ;;
            *)  break ;;
        esac
    done
    venv="${1:-$here/venv}"
    _MLX_VENV="$venv"

    command -v apt-get >/dev/null || {
        mlx_err "no apt-get here — this script is for Ubuntu/WSL."
        mlx_err "on the school machine use init-mlx-school.sh instead."
        return 1
    }
    [ -f "$tarball" ] || { mlx_err "missing $tarball"; return 1; }

    # Reuse a venv that already works, unless asked to rebuild.
    if [ "$force" -eq 0 ] && [ -d "$venv" ] && mlx_verify_venv "$venv"; then
        mlx_say "reusing existing venv $venv"
        return 0
    fi

    tmp="$(mktemp -d)" || return 1
    mlx_say "unpacking $(basename "$tarball")"
    mlx_unpack_all "$tmp" "$tarball" || { rm -rf "$tmp"; return 1; }

    mlx_collect_missing "$tmp" debian
    missing="$MLX_MISSING_PKGS"

    if [ -n "$missing" ]; then
        mlx_say "missing system packages:"
        printf '      %s\n' $missing
        if [ "$check" -eq 1 ]; then
            mlx_say "check only — install them with:"
            printf '      sudo apt-get install -y %s\n' "$(echo $missing)"
            rm -rf "$tmp"
            return 1
        fi
        mlx_say "installing them with apt (sudo will ask for your password)"
        sudo apt-get update -qq \
            && sudo apt-get install -y $missing || {
            mlx_err "apt could not install: $(echo $missing)"
            rm -rf "$tmp"
            return 1
        }
    else
        mlx_say "all system libraries are present"
    fi

    if [ "$check" -eq 1 ]; then
        mlx_say "check only — nothing was built"
        rm -rf "$tmp"
        return 0
    fi

    [ -d "$venv" ] && { mlx_say "removing $venv"; rm -rf "$venv"; }

    mlx_say "building venv $venv"
    flavour="$(mlx_build_venv "$venv" "$tmp")" || {
        mlx_err "neither wheel loads even after installing the packages."
        mlx_err "run with -c to see what ldd still cannot resolve."
        rm -rf "$tmp"
        return 1
    }
    rm -rf "$tmp"

    mlx_verify_venv "$venv" || {
        mlx_err "the $flavour wheel installed but libmlx.so will not load"
        return 1
    }
    mlx_say "mlx 2.2 ($flavour build) installed in $venv"

    # WSL only: a window needs WSLg or an external X server.
    if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
        mlx_warn "DISPLAY and WAYLAND_DISPLAY are both unset — no window"
        mlx_warn "will open. Update WSL ('wsl --update' from PowerShell)."
    elif [ ! -d /mnt/wslg ]; then
        mlx_warn "/mnt/wslg not found: DISPLAY is set but WSLg is not"
        mlx_warn "running. An external X server would also work."
    else
        mlx_say "WSLg is up (DISPLAY=$DISPLAY) — windows should open"
    fi
    return 0
}

_mlx_wsl_main "$@"
_mlx_rc=$?

if [ "$_mlx_rc" -eq 0 ] && [ "$_mlx_sourced" -eq 1 ]; then
    . "$_MLX_VENV/bin/activate"
    printf '==> venv activated — "deactivate" to leave it\n'
elif [ "$_mlx_rc" -eq 0 ]; then
    printf '==> activate it with:  source %s/bin/activate\n' "$_MLX_VENV"
    printf '==> then try:          python mlx/mlx-demo.py\n'
fi

_mlx_was_sourced="$_mlx_sourced"
unset -f _mlx_wsl_main
unset _mlx_sourced _MLX_VENV

# Propagate the status. A sourced script must return, never exit — exit
# would close the user's shell.
if [ "$_mlx_was_sourced" -eq 1 ]; then
    unset _mlx_was_sourced _MLX_SELF
    return "$_mlx_rc"
fi
unset _mlx_was_sourced _MLX_SELF
exit "$_mlx_rc"
