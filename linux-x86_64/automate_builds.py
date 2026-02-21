# ~/embeetle_docker/automate_builds.py

from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union, IO
import hashlib
import fnmatch
import argparse

# =============================================================================
# GLOBAL PATHS
# =============================================================================
HOME_DIR: Path = Path.home()
DOCKERFILE_DIR: Path = Path(__file__).parent.resolve()

EMBEETLE_REPO: Optional[Path] = None  # eg. '~/embeetle'
LLVM_REPO: Optional[Path] = None      # eg. '~/llvm'
SA_REPO: Optional[Path] = None        # eg. '~/sa'
SYS_REPO: Optional[Path] = None       # eg. '~/embeetle/sys'
BUILD_DIR: Optional[Path] = None      # eg. '~/bld'

DOCKER_IMAGE_NAME = "embeetle-build-env:latest"


def _help() -> None:
    """Help message"""
    header = (
        "\n"
        + "=" * 80
        + "\n"
        + "|"
        + " " * 24
        + "EMBEETLE BUILD AUTOMATION TOOL"
        + " " * 24
        + "|"
        + "\n"
        + "=" * 80
    )
    printc(header, fg="bright_blue")
    print(f"This tool automates everything for the Embeetle, LLVM and SA modules, all the")
    print(f"way from cloning the repos to the final builds. Runs on Linux using Docker.")
    print(f"")
    print(f"{c('PREREQUISITES', fg='bright_blue')}")
    print(f"    - Drop this script and the Dockerfile")
    print(f"      (see https://github.com/Embeetle/automate_builds/edit/master/linux-x86_64/Dockerfile)")
    print(f"      in the same directory")
    print(f"      (e.g., {c('~/embeetle_docker/', fg='bright_yellow')}). It will automatically target")
    print(f"      your home directory for cloning repos and building.")
    print(f"")
    print(f"    - Install Git.")
    print(f"")
    print(f"    - Install Docker and ensure your user has permission to run it. You may")
    print(f"      install it manually or use the automated installation:")
    print(f"          {c('$ python automate_builds.py --install-docker', fg='bright_yellow')}")
    print(f"          {c('$ newgrp docker', fg='bright_yellow')} (or log out and back in)")
    print(f"      After these two steps, you should be able to run {c('$ docker ps', fg='bright_yellow')} without sudo")
    print(f"      and see no permission errors.")
    print(f"")
    print(f"{c('USAGE', fg='bright_blue')}")
    print(f"    {c('-h', fg='bright_cyan')}, {c('--help', fg='bright_cyan')}         Show this help message and quit.")
    print(f"")
    print(f"    {c('--install-docker', fg='bright_cyan')}   Install Docker on Ubuntu/Debian-based systems.")
    print(f"                       For other systems, you need to do it manually.")
    print(f"                       Requires sudo, and you need to run {c('$ newgrp docker', fg='bright_yellow')} or")
    print(f"                       log out/in after.")
    print(f"    {c('--clean-docker', fg='bright_cyan')}     Stop and remove all Docker containers and images.")
    print(f"")
    print(f"    {c('--clone', fg='bright_cyan')}            Clone and/or update all repos on the host.")
    print(f"    {c('--install-packages', fg='bright_cyan')} Build the Docker image from the Dockerfile.")
    print(f"    {c('--build-llvm', fg='bright_cyan')}       Build LLVM inside Docker.")
    print(f"    {c('--build-sa', fg='bright_cyan')}         Build SA inside Docker.")
    print(f"    {c('--install-sa', fg='bright_cyan')}       Copy SA build output into Embeetle sources.")
    print(f"    {c('--build-embeetle', fg='bright_cyan')}   Build Embeetle inside Docker.")
    print(f"    {c('--all', fg='bright_cyan')}              Do everything (except installing Docker).")
    print(f"")
    print(f"{c('RESULTS', fg='bright_blue')}")
    print(f"    Running this script with the {c('--all', fg='bright_cyan')} flag should result in:")
    print(f"")
    print(f"         {c('~', fg='bright_yellow')}")
    print(f"         ├─ embeetle_docker")
    print(f"         │  ├─ Dockerfile")
    print(f"         │  └─ automate_builds.py [this script]")
    print(f"         ├─ bld")
    print(f"         │  ├─ embeetle")
    print(f"         │  ├─ llvm")
    print(f"         │  └─ sa")
    print(f"         ├─ embeetle  ")
    print(f"         ├─ llvm  ")
    print(f"         └─ sa  ")
    print(f"")
    print(f"    To run Embeetle..")
    print(f"")
    print(f"        {c('..from sources:', fg='bright_magenta')}")
    print(f"            Navigate to {c('~/embeetle', fg='bright_yellow')} and launch it natively:")
    print(f"                {c('$ pip install -r requirements.txt', fg='bright_yellow')}")
    print(f"                {c('$ cd beetle_core', fg='bright_yellow')}")
    print(f"                {c('$ python embeetle.py', fg='bright_yellow')}")
    print(f"")
    print(f"        {c('..from the executable:', fg='bright_magenta')}")
    print(f"            Navigate to {c('~/bld/embeetle', fg='bright_yellow')} and launch the built binary.")
    return


def c(text: str, *, fg: str | None = None, bold: bool = False) -> str:
    """Colorize text with ANSI SGR codes."""
    codes: list[str] = []
    if bold: codes.append("1")
    fg_map = {
        "black": "30", "red": "31", "green": "32", "yellow": "33",
        "blue": "34", "magenta": "35", "cyan": "36", "white": "37",
        "bright_black": "90", "bright_red": "91", "bright_green": "92",
        "bright_yellow": "93", "bright_blue": "94", "bright_magenta": "95",
        "bright_cyan": "96", "bright_white": "97",
    }
    if fg and fg.lower() in fg_map:
        codes.append(fg_map[fg.lower()])

    if not codes:
        return text
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def printc(*args, fg: Optional[str] = None, bold: bool = False, **kwargs) -> None:
    """Print the given text in the requested color."""
    if fg is None or fg.lower() == "default":
        print(*args, **kwargs)
        return
    sep = kwargs.pop("sep", " ")
    text = sep.join(str(arg) for arg in args)
    return print(c(text, fg=fg, bold=bold), **kwargs)


def run_native(args: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command natively on the Linux host."""
    cmd_str = " ".join(args)
    print(f"\n[HOST] {cmd_str}")
    return subprocess.run(args, cwd=str(cwd) if cwd else None, check=check, text=True)


def run_in_docker(docker_cmd: str, working_dir_in_container: str = "/root") -> subprocess.CompletedProcess[str]:
    """
    Run a shell command inside the Docker container, mapping host directories to /root/...
    Automatically fixes file permissions for the host user after the command finishes.
    """
    assert LLVM_REPO and SA_REPO and EMBEETLE_REPO and BUILD_DIR

    # 1. Get the current Linux user's UID and GID
    host_uid = os.getuid()
    host_gid = os.getgid()

    # 2. Wrap the command to ensure permissions are fixed even if the command fails,
    #    while preserving the original exit code.
    #
    # The `wrapped_cmd` runs `docker_cmd`, saves its exit status (EXIT_CODE=$?), recursively
    # changes the ownership of everything in the mapped '/data' folders back to your user
    # (chown -R ...), and finally exits with the original status so Python knows if the
    # command passed or failed. We add '2>/dev/null || true' so it doesn't throw errors
    # if a specific folder is missing.
    #
    # Changed /data/... to /root/...
    chown_cmd = f"chown -R {host_uid}:{host_gid} /root/llvm /root/sa /root/embeetle /root/bld 2>/dev/null || true"
    wrapped_cmd = f"{docker_cmd}; EXIT_CODE=$?; {chown_cmd}; exit $EXIT_CODE"

    args = [
        "docker", "run", "--rm",
        "-v", f"{LLVM_REPO}:/root/llvm",
        "-v", f"{SA_REPO}:/root/sa",
        "-v", f"{EMBEETLE_REPO}:/root/embeetle",
        "-v", f"{BUILD_DIR}:/root/bld",
        "-w", working_dir_in_container,
        DOCKER_IMAGE_NAME,
        "bash", "-c", wrapped_cmd
    ]
    
    print(f"\n[DOCKER] {docker_cmd}")
    return subprocess.run(args, check=True, text=True)


def clone_or_update_repo(repo_url: str, repo_dir: Path) -> None:
    """Clone or update given repository on the host."""
    repo_parent_dir = repo_dir.parent
    repo_parent_dir.mkdir(parents=True, exist_ok=True)

    if repo_dir.exists() and not (repo_dir / ".git").exists():
        raise RuntimeError(f"Path exists but is not a git repo: {repo_dir}")

    if not repo_dir.exists():
        print(f"\n==> Cloning {repo_dir}...")
        run_native(["git", "clone", repo_url, str(repo_dir)], cwd=repo_parent_dir)
        return

    print(f"\n==> Updating {repo_dir}...")
    try:
        run_native(["git", "-C", str(repo_dir), "pull", "--ff-only"], cwd=repo_parent_dir)
    except subprocess.CalledProcessError:
        printc(f"\nERROR: Cannot update repo. You have local changes in {repo_dir}.", fg="bright_red")
        raise SystemExit(2)
    return


def check_docker_ready() -> None:
    """Ensure Docker is installed and the daemon is reachable without sudo."""
    # 1. Check if the Docker CLI exists
    if shutil.which("docker") is None:
        printc("\nERROR: Docker is not installed.", fg="bright_red", bold=True)
        printc("Please install it manually, or run this script with:")
        printc("    $ python automate_builds.py --install-docker", fg="bright_cyan", bold=True)
        printc("After installing, run this command to refresh permissions:")
        printc("    $ newgrp docker", fg="bright_cyan", bold=True)
        printc("Or, completely log out and log back into your desktop environment.")
        raise SystemExit(1)
    
    # 2. Check if the daemon is reachable (this catches the 'newgrp docker' issue)
    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if result.returncode != 0:
        printc("\nERROR: Cannot connect to the Docker daemon.", fg="bright_red", bold=True)
        printc("If you just installed Docker, your user permissions haven't refreshed yet.", fg="bright_yellow")
        printc("Please run this command and try again:")
        printc("    $ newgrp docker", fg="bright_cyan", bold=True)
        printc("Or verify the daemon is running: $ sudo systemctl start docker")
        raise SystemExit(1)
    return


def _is_ubuntu_or_debian() -> bool:
    """Check if the current Linux distro is Ubuntu or Debian based."""
    try:
        with open("/etc/os-release") as f:
            content = f.read().lower()
            return any(x in content for x in ["id=ubuntu", "id=debian", "id_like=debian", "id_like=ubuntu"])
    except FileNotFoundError:
        return False


def install_docker_ubuntu() -> None:
    """Install Docker on Ubuntu/Debian based on the official apt repository."""
    if not _is_ubuntu_or_debian():
        printc("\nERROR: The automatic Docker installation only supports Ubuntu/Debian-based systems.", fg="bright_red")
        printc("Please install Docker manually according to your Linux distribution's official documentation.", fg="bright_yellow")
        raise SystemExit(1)

    printc("\n==> Installing Docker (you may be prompted for your sudo password)...", fg="bright_blue")

    # 1. Update and install prerequisite packages
    run_native(["sudo", "apt", "update"])
    run_native(["sudo", "apt", "install", "-y", "apt-transport-https", "ca-certificates", "curl", "software-properties-common", "lsb-release", "gnupg"])

    # 2. Remove older, conflicting versions (ignore errors if they aren't installed)
    run_native(["sudo", "apt", "remove", "-y", "docker", "docker-engine", "docker.io", "containerd", "runc"], check=False)

    # 3. Add Docker's official GPG key
    # We use a shell command here because of the pipe (|)
    print("\n[HOST] Adding Docker GPG key...")
    subprocess.run(
        "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --yes -o /usr/share/keyrings/docker-archive-keyring.gpg",
        shell=True, check=True
    )

    # 4. Set up the stable repository dynamically based on the Ubuntu version
    print("\n[HOST] Adding Docker apt repository...")
    repo_cmd = (
        'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] '
        'https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | '
        'sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'
    )
    subprocess.run(repo_cmd, shell=True, check=True)

    # 5. Install Docker Engine
    run_native(["sudo", "apt", "update"])
    run_native(["sudo", "apt", "install", "-y", "docker-ce", "docker-ce-cli", "containerd.io", "docker-compose-plugin"])

    # 6. Start and enable the Docker daemon
    run_native(["sudo", "systemctl", "enable", "docker"])
    run_native(["sudo", "systemctl", "start", "docker"])

    # 7. Add current user to the 'docker' group to avoid needing sudo for docker runs
    user = os.environ.get("USER")
    if user:
        run_native(["sudo", "usermod", "-aG", "docker", user])

    # 8. Run the Hello World test (using sudo since group permissions haven't refreshed yet)
    printc("\n==> Testing the installation with 'hello-world'...", fg="bright_blue")
    run_native(["sudo", "docker", "run", "--rm", "hello-world"])

    printc("\n" + "="*80, fg="bright_green", bold=True)
    printc("DOCKER INSTALLATION COMPLETE AND TESTED!", fg="bright_green", bold=True)
    printc("IMPORTANT: To run Docker without sudo, your group membership needs to refresh.", fg="bright_yellow")
    printc("Please run this command in your terminal before running the rest of the build:", bold=True)
    printc("    $ newgrp docker", fg="bright_cyan", bold=True)
    printc("Or, completely log out and log back into your desktop environment.", bold=True)
    printc("="*80 + "\n", fg="bright_green", bold=True)
    return


def clean_docker() -> None:
    """Stop and remove all running containers, and remove all images."""
    printc("==> Cleaning up Docker...", fg="bright_blue")

    # Stop all running containers
    print("\n[HOST] Stopping all running containers...")
    res = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True)
    containers = res.stdout.strip().split()
    if containers:
        subprocess.run(["docker", "stop"] + containers, check=True)
    else:
        print("No running containers to stop.")

    # Remove all containers
    print("\n[HOST] Removing all containers...")
    res = subprocess.run(["docker", "ps", "-aq"], capture_output=True, text=True)
    all_containers = res.stdout.strip().split()
    if all_containers:
        subprocess.run(["docker", "rm"] + all_containers, check=True)
    else:
        print("No containers to remove.")

    # Remove all images
    print("\n[HOST] Removing all images...")
    res = subprocess.run(["docker", "images", "-q"], capture_output=True, text=True)
    images = res.stdout.strip().split()
    if images:
        # We use -f (force) here just in case an image is stubborn
        subprocess.run(["docker", "rmi", "-f"] + images, check=True)
    else:
        print("No images to remove.")

    # Remove all build cache (BuildKit)
    print("\n[HOST] Removing Docker build cache...")
    # We use check=False because older Docker versions might not support this exact command, 
    # but for modern Docker, it safely wipes the hidden layer cache.
    subprocess.run(["docker", "builder", "prune", "-a", "-f"], check=False)

    printc("\nCleanup complete.", fg="bright_green", bold=True)
    return


def build_docker_image() -> None:
    """Build the Docker image from the Dockerfile."""
    if not DOCKERFILE_DIR.exists() or not (DOCKERFILE_DIR / "Dockerfile").exists():
        raise FileNotFoundError(f"Dockerfile not found at {DOCKERFILE_DIR}/Dockerfile")
    
    print(f"\n==> Building Docker Image '{DOCKER_IMAGE_NAME}'...")
    run_native(["docker", "build", "-t", DOCKER_IMAGE_NAME, "."], cwd=DOCKERFILE_DIR)
    return


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)
    return


def build_llvm() -> None:
    """Build LLVM inside Docker."""
    assert BUILD_DIR and SA_REPO

    llvm_bld = BUILD_DIR / "llvm"
    _ensure_dir(BUILD_DIR)
    _ensure_dir(llvm_bld)
    _ensure_dir(SA_REPO / "sys" / "linux")
    _ensure_dir(SA_REPO / "sys" / "linux" / "lib")

    # Changed /data/... to /root/...
    docker_cmd = "make -C /root/bld/llvm -f /root/sa/Makefile llvm"
    run_in_docker(docker_cmd, working_dir_in_container="/root/bld/llvm")
    return


def build_sa() -> None:
    """Build SA inside Docker."""
    assert BUILD_DIR and SA_REPO

    sa_bld = BUILD_DIR / "sa"
    _ensure_dir(BUILD_DIR)
    _ensure_dir(sa_bld)
    _ensure_dir(SA_REPO / "sys" / "linux")
    _ensure_dir(SA_REPO / "sys" / "linux" / "lib")

    # Changed /data/... to /root/...
    docker_cmd = "make -C /root/bld/sa -f /root/sa/Makefile"
    run_in_docker(docker_cmd, working_dir_in_container="/root/bld/sa")
    return


def mirror_dir(src: Union[str, Path], dst: Union[str, Path], delete: bool = False, exclude: Iterable[str] = (".git/**", "__pycache__/**")) -> None:
    """One-way mirror: makes dst look like src on the host filesystem."""
    def _excluded(_rel_posix: str, patterns: Iterable[str]) -> bool:
        return any(fnmatch.fnmatch(_rel_posix, _pat) for _pat in patterns)

    src_path: Path = Path(src).resolve()
    dst_path: Path = Path(dst).resolve()

    if not src_path.is_dir():
        raise ValueError(f"src is not a directory: '{src_path}'")

    for s in src_path.rglob("*"):
        rel: Path = s.relative_to(src_path)
        if _excluded(rel.as_posix(), exclude): continue
        d: Path = dst_path / rel

        if s.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            continue
        if not s.is_file():
            continue 

        do_copy = False
        if not d.exists():
            do_copy = True
        else:
            ss, ds = s.stat(), d.stat()
            if ss.st_size != ds.st_size or int(ss.st_mtime) != int(ds.st_mtime):
                do_copy = True

        if do_copy:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)

    if delete:
        for d in sorted(dst_path.rglob("*"), reverse=True):
            rel = d.relative_to(dst_path)
            if _excluded(rel.as_posix(), exclude): continue
            s = src_path / rel
            if not s.exists():
                if d.is_dir():
                    try: d.rmdir()
                    except OSError: pass
                else:
                    d.unlink()
    return


def install_sa_sys_into_embeetle_sys() -> None:
    """Copy Linux SA build outputs on the host."""
    assert BUILD_DIR and EMBEETLE_REPO

    src_sys = BUILD_DIR / "sa/sys-linux-x86_64"
    dst_sys = EMBEETLE_REPO / "sys"
    dst2_sys = BUILD_DIR / "embeetle/sys"

    if not src_sys.is_dir():
        raise RuntimeError(f"Source sys folder does not exist: '{src_sys}'. Did SA build successfully?")

    print(f"\n==> Installing SA sys overlay:")
    mirror_dir(src=src_sys, dst=dst_sys, delete=False)
    if dst2_sys.is_dir():
        mirror_dir(src=src_sys, dst=dst2_sys, delete=False)

    src_esa = src_sys / "esa"
    dst_esa = dst_sys / "esa"
    dst2_esa = dst2_sys / "esa"

    if src_esa.is_dir():
        mirror_dir(src=src_esa, dst=dst_esa, delete=True)
        if dst2_sys.is_dir():
            mirror_dir(src=src_esa, dst=dst2_esa, delete=True)
    return


FIX_SO_SCRIPT = r"""#!/bin/bash
set -e

if [ $# != 1 ]; then
    echo "Usage: $0 <embeetle-tree>"
    exit 1
fi

tree=$(realpath "$1")
sys="$tree/sys"

# Support several kinds of trees:
#  - sys/linux
#  - sys/linux-x86_64
#  - flattened trees (sys directly)
if [ -d "$sys/linux-x86_64" ]; then
    linuxdir="$sys/linux-x86_64"
elif [ -d "$sys/linux" ]; then
    linuxdir="$sys/linux"
elif [ -d "$sys/lib" ]; then
    linuxdir="$sys"
else
    shopt -s nullglob
    matches=( "$sys"/linux-* )
    shopt -u nullglob
    if [ "${#matches[@]}" -eq 1 ] && [ -d "${matches[0]}" ]; then
        linuxdir="${matches[0]}"
    else
        echo "Not an Embeetle linux tree: $tree"
        echo "Expected $sys/linux-x86_64, $sys/linux, or $sys/lib"
        exit 1
    fi
fi

bin="$linuxdir/bin"
lib="$linuxdir/lib"
if [ ! -d "$lib" ]; then
    echo "Not an Embeetle linux tree (missing lib dir): $tree"
    exit 1
fi

tmp=/tmp/$$
trap 'rm -rf $tmp' EXIT
rm -rf $tmp
mkdir "$tmp"

echo Fixing "$tree" ...

for so in \
 beetle_core/lib/PyQt6/Qt6/plugins/sqldrivers/libqsqlmimer.so \
 beetle_core/lib/PyQt6/Qt6/qml/QtQuick/Scene3D/libqtquickscene3dplugin.so \
 beetle_core/lib/PyQt6/Qt6/plugins/sceneparsers/libassimpsceneimport.so \
 beetle_core/lib/PyQt6/Qt6/qml/QtQuick/Scene2D/libqtquickscene2dplugin.so \
 beetle_core/lib/PyQt6/Qt6/plugins/geometryloaders/libgltfgeometryloader.so \
 beetle_core/lib/PyQt6/Qt6/plugins/geometryloaders/libdefaultgeometryloader.so \
 beetle_core/lib/PyQt6/Qt6/plugins/renderers/libopenglrenderer.so \
 beetle_core/lib/PyQt6/Qt6/plugins/renderers/librhirenderer.so \
 beetle_core/lib/PyQt6/Qt6/plugins/sceneparsers/libgltfsceneimport.so \
 beetle_core/lib/PyQt6/Qt6/plugins/sceneparsers/libgltfsceneexport.so \
 beetle_core/lib/PyQt6/Qt6/plugins/renderplugins/libscene2d.so \
 beetle_core/lib/PyQt6/Qt6/plugins/egldeviceintegrations/libqeglfs-x11-integration.so \
 beetle_core/lib/PyQt6/Qt6/plugins/egldeviceintegrations/libqeglfs-emu-integration.so \
 beetle_core/lib/PyQt6/Qt6/plugins/egldeviceintegrations/libqeglfs-kms-egldevice-integration.so \
 beetle_core/lib/PyQt6/Qt6/plugins/egldeviceintegrations/libqeglfs-kms-integration.so \
 beetle_core/lib/PyQt6/Qt6/plugins/platforms/libqeglfs.so \
 beetle_core/lib/PyQt6/Qt6/plugins/qmllint/libquicklintplugin.so \
 beetle_core/lib/PyQt6/Qt6/qml/QtQuick/LocalStorage/libqmllocalstorageplugin.so \
 beetle_core/lib/PyQt6/Qt6/qml/QtQml/XmlListModel/libqmlxmllistmodelplugin.so \
 beetle_core/lib/PyQt6/Qt6/qml/QtQuick3D/Helpers/impl/libqtquick3dhelpersimplplugin.so \
 beetle_core/lib/PyQt6/Qt6/qml/QtQuick3D/ParticleEffects/libqtquick3dparticleeffectsplugin.so \
 beetle_core/lib/PyQt6/Qt6/qml/QtQuick3D/Physics/Helpers/libqtquick3dphysicshelpersplugin.so \
 beetle_core/lib/PyQt6/Qt6/qml/QtQuick3D/Physics/libqquick3dphysicsplugin.so \
 beetle_core/lib/PyQt6/Qt6/qml/QtQuick/Effects/libeffectsplugin.so \
 beetle_core/lib/PyQt6/Qt6/plugins/webview/libqtwebview_webengine.so \
 beetle_core/lib/PyQt6/Qt6/plugins/multimedia/libffmpegmediaplugin.so \
 beetle_core/lib/readline.cpython-312-x86_64-linux-gnu.so \
 ; do
    if [ -f "$tree/$so" ]; then
        echo "Remove $so"
        rm "$tree/$so"
    fi
done

for path in \
    $(find "$tree" -name '*wayland*') \
  "$tree/beetle_core/lib/PyQt6/Qt6/plugins/multimedia/libgstreamermediaplugin.so" \
  "$tree/beetle_core/lib/PyQt6/Qt6/plugins/platformthemes/libqgtk3.so" \
; do
    if [ -e "$path" ]; then
        echo "Remove wayland $path"
        rm -rf "$path"
    fi
done

find "$tree/" -name '*.so' -type f >>"$tmp/needed"
find "$bin" "$lib" -type f >>"$tmp/needed"
for file in "$tree/beetle_core/lib/PyQt6/Qt6/libexec/QtWebEngineProcess"; do
    if [ -f "$file" ]; then
        echo "$file" >>"$tmp/needed"
    fi
done

export LD_LIBRARY_PATH="$lib"

ldd $(cat "$tmp/needed") 2>"$tmp/err" \
| sed -e 's@ (0x[0-9a-f]*)$@@' \
| sort -u \
| grep " => " \
| grep -v " => $tree/" >"$tmp/out" || true

sed <"$tmp/out" -e 's@^\t\(.*\) => not found$@\1@' -e t -e d > "$tmp/not-found"
if [ -s "$tmp/not-found" ]; then
    echo "Error: Some shared objects could not be found. See script logic."
    exit 1
fi

deps="$tmp/deps"
grep <"$tmp/out" -v " => not found$" \
| sed -e 's@^.* => @@' -e t -e d \
| grep -v \
       -e '/libc\.so\(\.[0-9\.]*\)\?$' \
       -e '/libdl\.so\(\.[0-9\.]*\)\?$' \
       -e '/libm\.so\(\.[0-9\.]*\)\?$' \
       -e '/librt\.so\(\.[0-9\.]*\)\?$' \
       -e '/libpthread\.so\(\.[0-9\.]*\)\?$' \
       -e '/libstdc++\.so\(\.[0-9\.]*\)\?$' \
       -e '/libnssckbi\.so\(\.[0-9\.]*\)\?$' \
       -e '/libglib-2\.0\.so\(\.[0-9\.]*\)\?$' \
       -e '/libnss3\.so\(\.[0-9\.]*\)\?$' \
       -e '/libnssutil3\.so\(\.[0-9\.]*\)\?$' \
       -e '/libk5crypto\.so\(\.[0-9\.]*\)\?$' \
       -e '/libsmime3\.so\(\.[0-9\.]*\)\?$' \
       -e '/libfontconfig\.so\(\.[0-9\.]*\)\?$' \
       -e '/libgtk-3\.so\(\.[0-9\.]*\)\?$' \
> "$deps" || true

log="$tree/so-copy.log"
: > "$log"

while IFS= read -r src; do
    [ -n "$src" ] || continue
    base=$(basename "$src")
    dst="$lib/$base"
    
    if ! cmp -s "$src" "$dst" 2>/dev/null; then
        echo "Copy: $src -> $dst" | tee -a "$log"
        cp -f "$src" "$dst"
    fi
done < "$deps"

echo Success
"""


def build_embeetle() -> None:
    """Build Embeetle inside Docker and fix shared objects."""
    assert BUILD_DIR and EMBEETLE_REPO

    embeetle_bld = BUILD_DIR / "embeetle"
    _ensure_dir(BUILD_DIR)
    _ensure_dir(embeetle_bld)

    # 1. Handle pip install & Embeetle build
    req_file = EMBEETLE_REPO / "requirements.txt"
    if not req_file.exists():
        printc(f"\n[WARN] No requirements.txt found at {req_file}", fg="bright_yellow")
        pip_cmd = "true"
    else:
        pip_cmd = "pip install --no-cache-dir -r requirements.txt"

    build_cmd = "python build.py --repo /root/embeetle --output /root/bld/embeetle"
    docker_build_cmd = f"{pip_cmd} && {build_cmd}"
    run_in_docker(docker_build_cmd, working_dir_in_container="/root/embeetle")

    # 2. Fix Shared Objects
    printc("\n==> Fixing shared objects (copying from Docker OS)...", fg="bright_blue")
    
    # Write the bash script temporarily to the host's build directory
    fix_so_script_path = BUILD_DIR / "fix_shared_objects.sh"
    fix_so_script_path.write_text(FIX_SO_SCRIPT, encoding="utf-8")
    
    # Run the script inside Docker, pointing it to the compiled Embeetle tree
    # Notice we use the internal /root/bld/... paths
    docker_fix_cmd = "bash /root/bld/fix_shared_objects.sh /root/bld/embeetle"
    run_in_docker(docker_fix_cmd, working_dir_in_container="/root/bld")

    # 3. Clean up the temporary script
    if fix_so_script_path.exists():
        fix_so_script_path.unlink()

    # 4. Make the main Embeetle launcher executable
    embeetle_launcher = embeetle_bld / "embeetle"
    if embeetle_launcher.exists():
        printc(f"\n==> Making launcher executable: {embeetle_launcher}", fg="bright_blue")
        # This is the Python equivalent of 'chmod +x'
        embeetle_launcher.chmod(embeetle_launcher.stat().st_mode | 0o111)
    return


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Embeetle, LLVM and SA", add_help=False)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("--install-docker", action="store_true")
    parser.add_argument("--clean-docker", action="store_true")
    parser.add_argument("--clone", action="store_true")
    parser.add_argument("--install-packages", action="store_true")
    parser.add_argument("--build-llvm", action="store_true")
    parser.add_argument("--build-sa", action="store_true")
    parser.add_argument("--install-sa", action="store_true")
    parser.add_argument("--build-embeetle", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.help:
        _help()
        sys.exit(0)

    # DETERMINE LOCATIONS
    global EMBEETLE_REPO, LLVM_REPO, SA_REPO, SYS_REPO, BUILD_DIR
    
    EMBEETLE_REPO = HOME_DIR / "embeetle"
    LLVM_REPO = HOME_DIR / "llvm"
    SA_REPO = HOME_DIR / "sa"
    SYS_REPO = EMBEETLE_REPO / "sys"
    BUILD_DIR = HOME_DIR / "bld"

    print(f"{c('EMBEETLE_REPO', fg='bright_yellow')} = '{EMBEETLE_REPO}'")
    print(f"{c('SYS_REPO', fg='bright_yellow')}      = '{SYS_REPO}'")
    print(f"{c('LLVM_REPO', fg='bright_yellow')}     = '{LLVM_REPO}'")
    print(f"{c('SA_REPO', fg='bright_yellow')}       = '{SA_REPO}'")
    print(f"{c('BUILD_DIR', fg='bright_yellow')}     = '{BUILD_DIR}'")

    # PRE-FLIGHT DOCKER CHECK
    # Only enforce the Docker check if the user is running a build command
    docker_needed = any([
        args.install_packages, 
        args.build_llvm, 
        args.build_sa, 
        args.build_embeetle, 
        args.clean_docker,
        args.all
    ])

    if docker_needed:
        check_docker_ready()

    if args.clean_docker:
            printc("\nCLEAN DOCKER", fg="bright_blue")
            printc("============", fg="bright_blue")
            clean_docker()
            # We generally shouldn't sys.exit(0) here just in case the user wants to 
            # do a completely fresh build in one command like: 
            # python automate_builds.py --clean-docker --install-packages --all

    if args.install_docker:
        printc("\nINSTALL DOCKER", fg="bright_blue")
        printc("==============", fg="bright_blue")
        install_docker_ubuntu()
        sys.exit(0) # Exit so the user can run 'newgrp docker' before continuing

    if args.clone or args.all:
        printc("\nCLONE REPOS", fg="bright_blue")
        printc("===========", fg="bright_blue")
        clone_or_update_repo("https://github.com/Embeetle/embeetle.git", EMBEETLE_REPO)
        clone_or_update_repo("https://github.com/Embeetle/llvm.git", LLVM_REPO)
        clone_or_update_repo("https://github.com/Embeetle/sa.git", SA_REPO)
        # Note the change to sys-linux-x86_64
        clone_or_update_repo("https://github.com/Embeetle/sys-linux-x86_64.git", SYS_REPO)
        print("\nAll repositories are up to date.")

    if args.install_packages or args.all:
        printc("\nBUILD DOCKER IMAGE", fg="bright_blue")
        printc("==================", fg="bright_blue")
        build_docker_image()
        print("\nDocker image built successfully.")

    if args.build_llvm or args.all:
        printc("\nBUILD LLVM", fg="bright_blue")
        printc("==========", fg="bright_blue")
        build_llvm()
        print("\nLLVM build finished.")

    if args.build_sa or args.all:
        printc("\nBUILD SA", fg="bright_blue")
        printc("========", fg="bright_blue")
        build_sa()
        print("\nSA build finished.")

    if args.install_sa or args.all:
        printc("\nINSTALL SA", fg="bright_blue")
        printc("==========", fg="bright_blue")
        install_sa_sys_into_embeetle_sys()
        print("\nInstalled SA sys into Embeetle sys.")

    if args.build_embeetle or args.all:
        printc("\nBUILD EMBEETLE", fg="bright_blue")
        printc("==============", fg="bright_blue")
        build_embeetle()
        print(f"\nEmbeetle built at '{BUILD_DIR / 'embeetle'}'")

    if not any([args.install_docker, args.clean_docker, args.clone, args.install_packages, args.build_llvm, args.build_sa, args.install_sa, args.build_embeetle, args.all]):
        print("\nNo action chosen. Print help...")
        _help()

    return 0

if __name__ == "__main__":

    raise SystemExit(main())
