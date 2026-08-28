# Create (or reuse) a virtualenv with the MinilibX python wrapper from subject/mlx-2.2.tgz,
# then activate it.
#
#   source ./mlx/init-mlx.sh [-f] [venv_path]     # activates in this shell
#   ./mlx/init-mlx.sh [-f] [venv_path]            # opens a shell with it active
#
# Sourced, it activates the venv in your current shell. Run directly, it cannot
# touch your shell's environment, so it drops you into an interactive bash with
# the venv active instead — leave that with 'exit'.
#
# Default venv_path is <this script's dir>/venv, i.e. ./mlx/venv.
# If that venv already exists it is reused as-is; -f rebuilds it from scratch.

_mlx_sourced=0
(return 0 2>/dev/null) && _mlx_sourced=1

_mlx_init() {
    local here tarball force venv py tmp wheel flavour installed
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || return 1
    tarball="$(cd "$here/.." && pwd)/subject/mlx-2.2.tgz"

    force=0
    if [ "${1-}" = "-f" ]; then
        force=1
        shift
    fi
    venv="${1-$here/venv}"
    _MLX_VENV="$venv"

    [ "$force" -eq 1 ] && [ -d "$venv" ] && {
        echo "==> removing existing venv $venv"
        rm -rf "$venv" || return 1
    }

    # Already there: nothing to build, the caller just activates it.
    if [ -d "$venv" ]; then
        if [ -x "$venv/bin/python" ] && "$venv/bin/python" -c 'import mlx' 2>/dev/null; then
            echo "==> reusing existing venv $venv"
            return 0
        fi
        echo "init-mlx: $venv exists but has no working mlx (use -f to rebuild)" >&2
        return 1
    fi

    [ -f "$tarball" ] || { echo "init-mlx: missing $tarball" >&2; return 1; }

    py="${PYTHON:-python3}"
    command -v "$py" >/dev/null || { echo "init-mlx: no $py in PATH" >&2; return 1; }

    tmp="$(mktemp -d)" || return 1

    echo "==> unpacking $(basename "$tarball")"
    tar xf "$tarball" -C "$tmp" || { rm -rf "$tmp"; return 1; }

    echo "==> creating venv $venv"
    "$py" -m venv "$venv" || { rm -rf "$tmp"; return 1; }
    "$venv/bin/pip" install --quiet --upgrade pip || { rm -rf "$tmp"; return 1; }

    # The tarball ships one prebuilt wheel per distro; they only differ in how
    # libmlx.so was built, so try each until one imports and loads its .so.
    installed=""
    for flavour in ubuntu fedora; do
        wheel="$tmp/$flavour/mlx-2.2-py3-none-any.whl"
        [ -f "$wheel" ] || continue
        echo "==> trying the $flavour wheel"
        "$venv/bin/pip" install --quiet --force-reinstall "$wheel" || continue
        if "$venv/bin/python" -c '
import ctypes, os, mlx
ctypes.CDLL(os.path.join(os.path.dirname(mlx.__file__), "libmlx.so"))
' 2>/dev/null; then
            installed="$flavour"
            break
        fi
        echo "    the $flavour build of libmlx.so does not load here, trying the next one"
    done
    rm -rf "$tmp"

    if [ -z "$installed" ]; then
        echo "init-mlx: no bundled wheel works here (check libxcb, libxcb-keysyms," >&2
        echo "          vulkan-icd-loader, libbsd and zlib are installed)" >&2
        return 1
    fi

    echo "==> mlx 2.2 ($installed build) installed in $venv"
    return 0
}

_mlx_init "$@"
_mlx_rc=$?

if [ "$_mlx_rc" -eq 0 ]; then
    if [ "$_mlx_sourced" -eq 1 ]; then
        . "$_MLX_VENV/bin/activate"
        echo "==> venv activated — 'deactivate' to leave it"
    elif [ -t 0 ] && [ -t 1 ]; then
        # Run directly: a child cannot touch the caller's environment, so hand
        # over an interactive bash that has the venv active instead. The rcfile
        # replays the usual startup files first so the shell still feels normal.
        echo "==> entering a shell with the venv active — 'exit' to leave"
        _mlx_rc_file="$(mktemp)"
        {
            echo '[ -f /etc/bash.bashrc ] && . /etc/bash.bashrc'
            echo '[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"'
            printf '. %q/bin/activate\n' "$_MLX_VENV"
            printf 'rm -f %q\n' "$_mlx_rc_file"
        } > "$_mlx_rc_file"
        exec bash --rcfile "$_mlx_rc_file" -i
    else
        echo
        echo "the venv is ready but cannot be activated from a child process."
        echo "activate it with:  source ${BASH_SOURCE[0]}"
    fi
fi

unset -f _mlx_init
unset _mlx_sourced _MLX_VENV

if (return 0 2>/dev/null); then
    return "$_mlx_rc"
else
    exit "$_mlx_rc"
fi
