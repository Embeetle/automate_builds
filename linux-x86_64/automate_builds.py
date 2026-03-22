# Copyright © 2018-2026 Johan Cockx, Matic Kukovec & Kristof Mulier
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# SPDX-License-Identifier: GPL-3.0-or-later

# ~/embeetle_docker/automate_builds.py

from __future__ import annotations
import os
import time
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union, IO
import hashlib
import fnmatch
import argparse
import re
import json
import http.client
import ssl
import atexit
import urllib.request
import urllib.error
from datetime import datetime

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
DOCKER_IMAGE_NAME: str = "embeetle-build-env:latest"
PLATFORM: str = "linux-x86_64"
GITHUB_EMBEETLE_REPO: str = "Embeetle/embeetle"


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
    print(f"    - This script and the Dockerfile should be in the same folder")
    print(f"      (this requirement is automatically met if you cloned the repo at")
    print(f"      https://github.com/Embeetle/automate_builds.git)")
    print(f"")
    print(f"      This script will automatically target your home directory for")
    print(f"      cloning repos and building.")
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
    print(f"{c('QUICK START', fg='bright_blue')}")
    print(f"    {c('Standard build', fg='bright_magenta')} (for anyone):")
    print(f"")
    print(f"        {c('1)', fg='bright_cyan')} If Docker isn't installed yet:")
    print(f"           {c('$', fg='bright_green')} {c('python automate_builds.py --install-docker', fg='bright_yellow')}")
    print(f"           {c('$', fg='bright_green')} {c('newgrp docker', fg='bright_yellow')}  {c('<-- or log out and back in', fg='bright_black')}")
    print(f"")
    print(f"        {c('2)', fg='bright_cyan')} Run the full build:")
    print(f"           {c('$', fg='bright_green')} {c('python automate_builds.py --all', fg='bright_yellow')}")
    print(f"")
    print(f"        Clones all repos, builds the Docker image, and builds LLVM, SA, and")
    print(f"        Embeetle in one go. Find the resulting executable at:")
    print(f"")
    print(f"            {c('~/bld/embeetle-linux-x86_64/embeetle', fg='bright_yellow')}")
    print(f"")
    print(f"    {c('Collaborator flow', fg='bright_magenta')} (requires GitHub write access):")
    print(f"")
    print(f"        {c('1)', fg='bright_cyan')} Verify your GitHub token grants write access:")
    print(f"           {c('$', fg='bright_green')} {c('python automate_builds.py --check-access', fg='bright_yellow')}")
    print(f"")
    print(f"        {c('2)', fg='bright_cyan')} Bump the version (pick one):")
    print(f"           {c('$', fg='bright_green')} {c('python automate_builds.py --set-version x.y.z', fg='bright_yellow')}  {c('<-- explicit version', fg='bright_black')}")
    print(f"           {c('$', fg='bright_green')} {c('python automate_builds.py --inc-version', fg='bright_yellow')}        {c('<-- auto-increment patch', fg='bright_black')}")
    print(f"")
    print(f"        {c('3)', fg='bright_cyan')} Run the full build:")
    print(f"           {c('$', fg='bright_green')} {c('python automate_builds.py --all', fg='bright_yellow')}")
    print(f"")
    print(f"        {c('4)', fg='bright_cyan')} Upload the release archive to GitHub:")
    print(f"           {c('$', fg='bright_green')} {c('python automate_builds.py --upload', fg='bright_yellow')}")
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
    print(f"    {c('--all', fg='bright_cyan')}              Run the full build pipeline (except installing Docker):")
    print(f"                           {c('--clone', fg='bright_cyan')}")
    print(f"                           {c('--install-packages', fg='bright_cyan')}")
    print(f"                           {c('--build-llvm', fg='bright_cyan')}")
    print(f"                           {c('--build-sa', fg='bright_cyan')}")
    print(f"                           {c('--install-sa', fg='bright_cyan')}")
    print(f"                           {c('--build-embeetle', fg='bright_cyan')}")
    print(f"                       {c('Note:', fg='bright_magenta')} Does NOT run the collaborator-only flags below.")
    print(f"")
    print(f"    {c('Collaborator-only flags', fg='bright_magenta')} (require write access to the GitHub repo):")
    print(f"")
    print(f"    {c('--set-version', fg='bright_cyan')} {c('X.Y.Z', fg='bright_yellow')}     Manually set the version in version.txt.")
    print(f"                       Checks that no GitHub release with this version tag")
    print(f"                       already exists before writing the file.")
    print(f"                       Requires GitHub write access (checked via token).")
    print(f"")
    print(f"    {c('--inc-version', fg='bright_cyan')}         Read the current version from version.txt, increment")
    print(f"                       the patch number by 1, and apply it (same as --set-version).")
    print(f"                       Requires GitHub write access (checked via token).")
    print(f"")
    print(f"    {c('--upload', fg='bright_cyan')}            Upload the {c('~/bld/embeetle-<PLATFORM>.7z', fg='bright_yellow')} archive to a")
    print(f"                       GitHub Release for the version in version.txt.")
    print(f"                       Creates the release if it doesn't exist yet.")
    print(f"                       Replaces an existing asset with the same name.")
    print(f"                       Requires GitHub write access (checked via token).")
    print(f"")
    print(f"    {c('--check-access', fg='bright_cyan')}      Verify that a GitHub token can be found and that it")
    print(f"                       grants write access to the Embeetle repository.")
    print(f"                       Exits with code 0 on success, 1 on failure.")
    print(f"                       Useful for diagnosing token/permission issues before")
    print(f"                       running {c('--set-version', fg='bright_cyan')} or {c('--upload', fg='bright_cyan')}.")
    print(f"")
    print(f"{c('RESULTS', fg='bright_blue')}")
    print(f"    Running this script with the {c('--all', fg='bright_cyan')} flag should result in:")
    print(f"")
    print(f"         {c('~', fg='bright_yellow')}")
    print(f"         ├─ bld")
    print(f"         │  ├─ embeetle-<PLATFORM>")
    print(f"         │  ├─ embeetle-<PLATFORM>.7z")
    print(f"         │  ├─ llvm")
    print(f"         │  └─ sa")
    print(f"         ├─ embeetle  ")
    print(f"         ├─ llvm  ")
    print(f"         └─ sa  ")
    print(f"")
    print(f"    To run Embeetle..")
    print(f"")
    print(f"        {c('..from sources:', fg='bright_magenta')}")
    print(f"            Navigate to {c('~/embeetle', fg='bright_yellow')}. If there is not yet a `.venv`")
    print(f"            folder, create one and install the Python dependencies:")
    print(f"                {c('$ python -m venv .venv', fg='bright_yellow')}")
    print(f"                {c('$ source .venv/bin/activate', fg='bright_yellow')}")
    print(f"                {c('$ python -m pip install -r requirements.txt', fg='bright_yellow')}")
    print(f"")
    print(f"            Once the python venv is set up, you can run Embeetle with it:")
    print(f"                {c('$ chmod +x run.sh', fg='bright_yellow')}")
    print(f"                {c('$ ./run.sh', fg='bright_yellow')}")
    print(f"")
    print(f"        {c('..from the executable:', fg='bright_magenta')}")
    print(f"            Navigate to {c('~/bld/embeetle-<PLATFORM>', fg='bright_yellow')} and launch the built binary.")
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


def run_native(args: list[str], cwd: Optional[Path] = None, check: bool = True, env: Optional[dict] = None) -> subprocess.CompletedProcess[str]:
    """Run a command natively on the Linux host."""
    cmd_str = " ".join(args)
    print(f"\n[HOST] {cmd_str}")
    try:
        return subprocess.run(args, cwd=str(cwd) if cwd else None, check=check, text=True, env=env)
    except subprocess.CalledProcessError as e:
        printc(
            f"\nERROR: Command failed with exit code {e.returncode} (see output above).\n"
            f"  If you see a network error, check your internet connection and try again.",
            fg="bright_red",
        )
        raise SystemExit(1)


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
    try:
        return subprocess.run(args, check=True, text=True)
    except subprocess.CalledProcessError as e:
        printc(
            f"\nERROR: Docker command failed with exit code {e.returncode} (see output above).\n"
            f"  If you see a network error, check your internet connection and try again.",
            fg="bright_red",
        )
        raise SystemExit(1)


def fix_git_config(repo_dir: Path) -> None:
    """
    Ensures the local repo config is set to autocrlf=false.
    If it was wrong, it refreshes the index to fix line endings.
    """
    if not repo_dir.exists():
        return

    # Check the LOCAL config (not global)
    try:
        current_val = subprocess.check_output(
            ["git", "-C", str(repo_dir), "config", "--local", "core.autocrlf"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        current_val = None

    if current_val != "false":
        print(f"==> Fixing line endings for existing repo: {repo_dir.name}...")
        # 1. Set local config
        run_native(["git", "-C", str(repo_dir), "config", "core.autocrlf", "false"])
        
        # 2. Refresh the index to recognize the change
        # This is the 'magic' to fix already-checked-out files
        run_native(["git", "-C", str(repo_dir), "add", "--renormalize", "."], check=False)
        printc(f"    Line endings normalized to LF in {repo_dir.name}", fg="green")
    return


def setup_git_auth_from_token() -> None:
    """
    If GITHUB_TOKEN is set in the environment, configure git to use it for all
    HTTPS operations against github.com — without any interactive prompt.

    Git calls the GIT_ASKPASS script whenever it needs a username or password.
    We write a small shell script that returns 'x-access-token' for the username
    and the token value for the password, then point GIT_ASKPASS at it and disable
    the terminal prompt entirely with GIT_TERMINAL_PROMPT=0.

    This is a no-op when GITHUB_TOKEN is not set (e.g. when GCM is used instead).
    """
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        return
    askpass_path = Path("/tmp/_embeetle_git_askpass.sh")
    askpass_path.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        '  *[Uu]sername*) echo "x-access-token" ;;\n'
        f'  *[Pp]assword*) echo "{token}" ;;\n'
        '  *) echo "" ;;\n'
        "esac\n"
    )
    askpass_path.chmod(0o700)
    os.environ["GIT_ASKPASS"] = str(askpass_path)
    os.environ["GIT_TERMINAL_PROMPT"] = "0"
    atexit.register(lambda: askpass_path.unlink(missing_ok=True))
    print(f"\n==> GITHUB_TOKEN detected — git configured to authenticate via token.")


def check_git_lfs_ready() -> None:
    """Ensure git-lfs is installed on the host."""
    if shutil.which("git-lfs") is None:
        printc("\nERROR: git-lfs is not installed.", fg="bright_red", bold=True)
        printc("Please install it first:", fg="bright_yellow")
        printc("    # Debian / Ubuntu / Mint:", fg="bright_green")
        printc("    $ sudo apt install git-lfs", fg="bright_cyan")
        printc("    # Fedora / Red Hat:", fg="bright_green")
        printc("    $ sudo dnf install git-lfs", fg="bright_cyan")
        printc("    # Arch / Manjaro:", fg="bright_green")
        printc("    $ sudo pacman -S git-lfs", fg="bright_cyan")
        raise SystemExit(1)
    # Set up LFS hooks globally (idempotent)
    run_native(["git", "lfs", "install"], check=False)
    return


def fix_sys_permissions(sys_dir: Path) -> None:
    """
    Ensure all files under a sys/ directory are executable.
    Git and LFS do not always preserve execute bits on Linux, so we enforce
    them explicitly after every clone, update, or install that touches sys/.
    """
    if not sys_dir.exists():
        return
    printc(f"\n==> Fixing executable permissions in '{sys_dir}'...", fg="bright_blue")
    for file_path in sys_dir.rglob("*"):
        if file_path.is_file():
            try:
                file_path.chmod(file_path.stat().st_mode | 0o111)
            except Exception as e:
                printc(f"    [WARN] Could not set permissions for {file_path.name}: {e}", fg="bright_yellow")


def clone_or_update_repo(repo_url: str, repo_dir: Path) -> None:
    """Clone or update given repository on the host."""
    repo_parent_dir = repo_dir.parent
    repo_parent_dir.mkdir(parents=True, exist_ok=True)

    if repo_dir.exists() and not (repo_dir / ".git").exists():
        raise RuntimeError(f"Path exists but is not a git repo: {repo_dir}")

    if not repo_dir.exists():
        print(f"\n==> Cloning {repo_dir}...")
        # GIT_CLONE_PROTECTION_ACTIVE=false allows post-checkout hooks to run
        # during clone (blocked by default since Git 2.38 for security).
        clone_env = {**os.environ, "GIT_CLONE_PROTECTION_ACTIVE": "false"}
        run_native(["git", "clone", "-c", "core.autocrlf=false", repo_url, str(repo_dir)], cwd=repo_parent_dir, env=clone_env)
        run_native(["git", "-C", str(repo_dir), "lfs", "pull"])
        return

    # Fix existing repo if it has wrong line-ending config
    fix_git_config(repo_dir)

    print(f"\n==> Updating {repo_dir}...")
    try:
        run_native(["git", "-C", str(repo_dir), "pull", "--ff-only"], cwd=repo_parent_dir)
    except subprocess.CalledProcessError:
        try:
            status = subprocess.check_output(
                ["git", "-C", str(repo_dir), "status", "--porcelain"],
                text=True,
                stderr=subprocess.STDOUT,
            )
        except Exception:
            status = ""

        if status.strip():
            printc(
                f"\nWARNING: Repo has local changes:\n"
                f"  {repo_dir}\n",
                fg="bright_yellow"
            )
            print(f"Git status (--porcelain):")
            print(status.rstrip())
            print(f"\nWhat would you like to do?")
            print(f"  [r] Reset and continue (discard local changes and pull)")
            print(f"  [s] Skip (leave repo as-is and continue)")
            print(f"  [a] Abort")
            choice = input("Your choice [r/s/a]: ").strip().lower()
            if choice == 'r':
                run_native(["git", "-C", str(repo_dir), "fetch", "--all"])
                run_native(["git", "-C", str(repo_dir), "reset", "--hard", "origin/HEAD"])
                run_native(["git", "-C", str(repo_dir), "clean", "-fd"])
            elif choice == 's':
                printc(f"\nSkipping update for '{repo_dir}'.", fg="bright_yellow")
                return
            else:
                raise SystemExit(2)
        else:
            raise
    run_native(["git", "-C", str(repo_dir), "lfs", "pull"])
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
        raise FileNotFoundError(
            f"Dockerfile not found at {DOCKERFILE_DIR}/Dockerfile"
        )
    
    print(f"\n==> Building Docker Image '{DOCKER_IMAGE_NAME}'...")
    run_native(
        [
            "docker",
            "build",
            "-t",
            DOCKER_IMAGE_NAME,
            ".",
        ],
        cwd=DOCKERFILE_DIR
    )
    return


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)
    return


def build_llvm() -> None:
    """Build LLVM inside Docker."""
    assert BUILD_DIR and SA_REPO

    llvm_bld: Path = BUILD_DIR / "llvm"
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

    sa_bld: Path = BUILD_DIR / "sa"
    _ensure_dir(BUILD_DIR)
    _ensure_dir(sa_bld)
    _ensure_dir(SA_REPO / "sys" / "linux")
    _ensure_dir(SA_REPO / "sys" / "linux" / "lib")

    # Changed /data/... to /root/...
    docker_cmd = "make -C /root/bld/sa -f /root/sa/Makefile"
    run_in_docker(docker_cmd, working_dir_in_container="/root/bld/sa")
    return


def mirror_dir(
        src: Union[str, Path],
        dst: Union[str, Path],
        delete: bool = False,
        exclude: Iterable[str] = (".git/**", "__pycache__/**"),
) -> None:
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

    src_sys: Path = BUILD_DIR / f"sa/sys-{PLATFORM}"
    dst_sys: Path = EMBEETLE_REPO / "sys"
    dst2_sys: Path = BUILD_DIR / f"embeetle-{PLATFORM}/sys"

    if not src_sys.is_dir():
        raise RuntimeError(
            f"Source sys folder does not exist: '{src_sys}'. "
            f"Did SA build successfully?"
        )

    print(f"\n==> Installing SA sys overlay:")
    mirror_dir(src=src_sys, dst=dst_sys, delete=False)
    if dst2_sys.is_dir():
        mirror_dir(src=src_sys, dst=dst2_sys, delete=False)

    src_esa: Path = src_sys / "esa"
    dst_esa: Path = dst_sys / "esa"
    dst2_esa: Path = dst2_sys / "esa"

    if src_esa.is_dir():
        mirror_dir(src=src_esa, dst=dst_esa, delete=True)
        if dst2_sys.is_dir():
            mirror_dir(src=src_esa, dst=dst2_esa, delete=True)

    fix_sys_permissions(dst_sys)
    if dst2_sys.is_dir():
        fix_sys_permissions(dst2_sys)
    return


# ==============================================================================
# VERSION UPDATING SCRIPT FOR DOCKER
# ==============================================================================
UPDATE_VERSION_SCRIPT = r"""
import sys
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
PLATFORM = "linux-x86_64"

def get_venv_info():
    # Query the venv for its Python version string and pip freeze list.
    py_ver = sys.version.replace('\n', ' ')
    try:
        pip_freeze = subprocess.check_output(
            [sys.executable, "-m", "pip", "freeze"],
            text=True
        ).strip()
    except Exception as e:
        pip_freeze = f"Error running pip freeze: {e}"
    return py_ver, pip_freeze

def main():
    # Read `version.txt` from the repo, extract the repo version and date, and
    # write a new `version.txt` in the build directory. The new version file
    # includes:
    #     - Embeetle version (from repo)
    #     - Repo date (from repo)
    #     - Build date (current date)
    #     - Platform (hardcoded as <PLATFORM>)
    #     - Python version (queried from the venv)
    #     - Installed packages (queried from the venv)
    version_file_rel = Path("beetle_core/version.txt")
    repo_dir = Path("/root/embeetle")
    build_dir = Path(f"/root/bld/embeetle-{PLATFORM}")
    repo_version_path = repo_dir / version_file_rel
    build_version_path = build_dir / version_file_rel

    assert repo_version_path.exists(), str(
        f"Version file not found at '{repo_version_path}'"
    )
    with open(repo_version_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Get repo version
    version_match = re.search(r"version:\s*([0-9.]+)", content)
    if version_match:
        current_version = version_match.group(1)
        print(f"\nRepo version: {current_version}")
    else:
        raise RuntimeError(
            f"Could not find repo version number in '{repo_version_path}'. "
            f"Expected a line like 'version: x.y.z'."
        )

    # 2. Get repo date
    repo_date_match = re.search(r"repo date:\s*(.*)", content)
    if repo_date_match:
        repo_date = repo_date_match.group(1).strip()
        print(f"Repo date: {repo_date}")
    else:
        raise RuntimeError(
            f"Could not find repo date in '{repo_version_path}'. "
            f"Expected a line like 'repo date: <date>'."
        )

    # 3. Construct build date string
    build_date_str = datetime.now().strftime("%d %b %Y")
    print(f"Build date: {build_date_str}")

    # 4. Construct Embeetle version block, like:
    #     Embeetle Version
    #     ================
    #     version: 2.0.2
    #     repo date: 04 Feb 2026
    #     build date: 11 Mar 2026
    #     platform: linux-x86_64
    embeetle_version_block = (
        f"Embeetle Version\n"
        f"===============\n"
        f"version: {current_version}\n"
        f"repo date: {repo_date}\n"
        f"build date: {build_date_str}\n"
        f"platform: {PLATFORM}\n"
    )

    # 5. Construct Python version block, like:
    #     Python Version
    #     ==============
    #     version: 3.13.7 (main, Jan 22 2026, 20:15:57) [GCC 15.2.0]
    py_ver, pkgs = get_venv_info()
    python_version_block = (
        f"Python Version\n"
        f"==============\n"
        f"version: {py_ver}\n"
    )

    # 6. Construct Installed Packages block, like:
    #     Installed Packages
    #     ==================
    #     package1==1.2.3
    #     package2==4.5.6
    installed_packages_block = (
        f"Installed Packages\n"
        f"==================\n"
        f"{pkgs}"
    )

    # 7. Combine all blocks into final content
    final_content = (
        f"{embeetle_version_block}\n"
        f"{python_version_block}\n"
        f"{installed_packages_block}\n"
    )
    # 8. Write to build version file
    build_version_path.parent.mkdir(parents=True, exist_ok=True)
    with open(build_version_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    return 0


if __name__ == "__main__":
    main()
"""

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
    embeetle_bld: Path = BUILD_DIR / f"embeetle-{PLATFORM}"
    embeetle_bld_in_docker: str = "/root/bld/" + embeetle_bld.relative_to(BUILD_DIR).as_posix()
    _ensure_dir(BUILD_DIR)
    _ensure_dir(embeetle_bld)

    # Write `update_version.py` script to a place Docker can read it
    update_script_path = BUILD_DIR / "update_version.py"
    update_script_path.write_text(UPDATE_VERSION_SCRIPT, encoding="utf-8")

    # 1. Handle pip install & Embeetle build & version update
    # Sequence: PIP INSTALL -> BUILD -> UPDATE VERSION (failsafe)
    req_file = EMBEETLE_REPO / "requirements.txt"
    assert req_file.exists()
    pip_cmd = "pip install --no-cache-dir -r requirements.txt"
    build_cmd = f"python build.py --auto --repo /root/embeetle --output {embeetle_bld_in_docker}"
    update_cmd = "python /root/bld/update_version.py"
    docker_build_cmd = f"{pip_cmd} && {build_cmd} && {update_cmd}"
    run_in_docker(docker_build_cmd, working_dir_in_container="/root/embeetle")

    # 2. Fix Shared Objects
    printc(
        "\n==> Fixing shared objects (copying from Docker OS)...",
        fg="bright_blue",
    )
    
    # Write the bash script temporarily to the host's build directory
    fix_so_script_path: Path = BUILD_DIR / "fix_shared_objects.sh"
    fix_so_script_path.write_text(FIX_SO_SCRIPT, encoding="utf-8")
    
    # Run the script inside Docker, pointing it to the compiled Embeetle tree
    # Notice we use the internal /root/bld/... paths
    docker_fix_cmd = f"bash /root/bld/fix_shared_objects.sh {embeetle_bld_in_docker}"
    run_in_docker(docker_fix_cmd, working_dir_in_container="/root/bld")

    # 3. Clean up the temporary scripts
    if fix_so_script_path.exists():
        fix_so_script_path.unlink()
    if update_script_path.exists():
        update_script_path.unlink()

    # 4. Make the main Embeetle launcher executable
    embeetle_launcher = embeetle_bld / "embeetle"
    if embeetle_launcher.exists():
        printc(
            f"\n==> Making launcher executable: {embeetle_launcher}",
            fg="bright_blue",
        )
        # This is the Python equivalent of 'chmod +x'
        embeetle_launcher.chmod(embeetle_launcher.stat().st_mode | 0o111)

    # 5. Make the sys directory contents executable
    fix_sys_permissions(embeetle_bld / "sys")

    # 6. Create 7zip archive
    # Also fix permissions on the repo's sys/bin/7za itself — git/lfs may not
    # preserve execute bits after a fresh clone or lfs pull.
    seven_zip: Path = EMBEETLE_REPO / "sys" / "bin" / "7za"
    if seven_zip.exists():
        seven_zip.chmod(seven_zip.stat().st_mode | 0o111)
    embeetle_archive: Path = BUILD_DIR / f"embeetle-{PLATFORM}.7z"
    if embeetle_archive.exists():
        embeetle_archive.unlink()
    print(f"\n==> Creating archive '{embeetle_archive}'...")
    run_native(
        [
            str(seven_zip), "a",
            str(embeetle_archive),
            "*",
            "-mx=9",           # Ultra compression
            "-mmt=on",         # Use all CPU cores
            "-md=128m",        # 128 MB dictionary for better ratio
            "-xr!__pycache__", # Exclude Python cache dirs
            "-xr!.git",        # Exclude any accidentally included git dirs
            "-y",              # Non-interactive (assume yes)
            "-snl",            # Store symlinks as symlinks (not as copies)
        ],
        cwd=embeetle_bld,
        check=True,
    )

    # 7. Print
    print(f"\nEmbeetle built at '{embeetle_bld}'")
    return


def get_github_token() -> str:
    """
    Verify the user has push access to the Embeetle GitHub repo.
    Tries to obtain a GitHub token in order:
      1. GITHUB_TOKEN environment variable
      2. git credential fill (covers GCM, macOS Keychain, etc.)
    Returns the token for reuse by the caller.
    """
    # 1. Try GITHUB_TOKEN environment variable
    token_source = None
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        token_source = "GITHUB_TOKEN environment variable"

    # 2. Try git credential manager
    if not token:
        try:
            result = subprocess.run(
                ["git", "credential", "fill"],
                input="protocol=https\nhost=github.com\n\n",
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                if line.startswith("password="):
                    token = line[len("password="):].strip()
                    if token:
                        token_source = "git credential manager"
                    break
        except Exception:
            pass

    if not token:
        printc(
            f"\nERROR: Could not obtain a GitHub token. Tried:\n"
            f"  1. GITHUB_TOKEN environment variable  (not set)\n"
            f"  2. git credential fill for github.com (no credentials found)\n"
            f"\nTo fix this, choose ONE of the following options:\n"
            f"\n"
            f"  Option A - Git Credential Manager (recommended):\n"
            f"      $ git credential-manager github login\n"
            f"    This opens a browser window for OAuth authentication with GitHub\n"
            f"    and stores the token securely in your system's credential store.\n"
            f"    No manual token management required.\n"
            f"\n"
            f"  Option B - GITHUB_TOKEN environment variable:\n"
            f"    Create a Personal Access Token (PAT) at:\n"
            f"      https://github.com/settings/tokens\n"
            f"    Make sure to grant it the 'repo' scope. Then set it as an\n"
            f"    environment variable named GITHUB_TOKEN.",
            fg="bright_red",
        )
        raise SystemExit(1)

    masked = token[:8] + "..." + token[-4:]
    print(f"\n==> Checking GitHub push access for '{GITHUB_EMBEETLE_REPO}'...")
    print(f"    Token source:     {token_source}")
    print(f"    Token:            {masked}")

    # Build a small helper for the two API calls below
    def _get(url: str) -> Tuple[dict, dict]:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "automate_builds/1.0",
            },
        )
        last_exc = None
        for attempt in range(3):
            if attempt:
                time.sleep(2 ** attempt)
            try:
                with urllib.request.urlopen(req) as resp:
                    return json.loads(resp.read()), dict(resp.headers)
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    printc(
                        f"\nERROR: GitHub token rejected (401 Unauthorized).\n"
                        f"  The token is invalid or has expired.\n"
                        f"  - If using Option A (GCM): re-run 'git credential-manager github login'\n"
                        f"    to refresh your credentials.\n"
                        f"  - If using Option B (GITHUB_TOKEN): generate a new PAT at\n"
                        f"    https://github.com/settings/tokens and update the environment variable.",
                        fg="bright_red",
                    )
                elif e.code == 403:
                    printc(
                        f"\nERROR: GitHub token lacks required permissions (403 Forbidden).\n"
                        f"  The token was accepted but is not authorized for this operation.\n"
                        f"  - If using Option A (GCM): re-run 'git credential-manager github login'\n"
                        f"    to re-authenticate and obtain a token with the correct scopes.\n"
                        f"  - If using Option B (GITHUB_TOKEN): make sure the PAT has the 'repo'\n"
                        f"    scope enabled at https://github.com/settings/tokens",
                        fg="bright_red",
                    )
                elif e.code == 404:
                    printc(
                        f"\nERROR: Repository '{GITHUB_EMBEETLE_REPO}' not found (404).\n"
                        f"  Either the repository does not exist, or your token does not have\n"
                        f"  permission to see it.",
                        fg="bright_red",
                    )
                else:
                    printc(f"\nERROR: GitHub API error {e.code}: {e.read().decode()}", fg="bright_red")
                raise SystemExit(1)
            except urllib.error.URLError as e:
                if isinstance(e.reason, OSError):
                    # Transient connection error — retry
                    last_exc = e
                    continue
                printc(
                    f"\nERROR: Network error contacting GitHub API: {e.reason}",
                    fg="bright_red",
                )
                raise SystemExit(1)
        printc(
            f"\nERROR: GitHub API unreachable after 3 attempts (connection reset).\n"
            f"  Check your internet connection or try again later.\n"
            f"  Last error: {last_exc}",
            fg="bright_red",
        )
        raise SystemExit(1)

    # Check authenticated user and token scopes
    user_data, user_headers = _get("https://api.github.com/user")
    scopes = user_headers.get("X-OAuth-Scopes", "n/a").strip()
    print(f"    Authenticated as: {user_data.get('login', 'unknown')}")
    print(f"    Token scopes:     {scopes}")

    # Check repo permissions
    repo_data, _ = _get(f"https://api.github.com/repos/{GITHUB_EMBEETLE_REPO}")
    if not repo_data.get("permissions", {}).get("push", False):
        printc(
            f"\nERROR: Your GitHub account does not have write access to '{GITHUB_EMBEETLE_REPO}'.\n"
            f"  The token itself is valid, but the GitHub account it belongs to is not a\n"
            f"  collaborator with write (or higher) permissions on this repository.\n"
            f"  Ask a repository admin to grant you write access at:\n"
            f"    https://github.com/{GITHUB_EMBEETLE_REPO}/settings/access\n"
            f"Contact:\n"
            f"info@embeetle.com\n",
            fg="bright_red",
        )
        raise SystemExit(1)

    print(f"    Write access confirmed (sufficient for releases and code push).")
    return token


def set_version(version: str) -> None:
    """
    Set the version of the Embeetle repo to x.y.z.
    For developers only (requires git push access).
    """
    assert EMBEETLE_REPO is not None

    # 0. Validate format
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        printc(
            f"\nERROR: Invalid version format '{version}'. Expected x.y.z (e.g. 2.1.3).",
            fg="bright_red",
        )
        raise SystemExit(1)
    tag = f"v{version}"

    # 1. Developer warning
    printc(
        f"\nWARNING: --set-version is for developers with git write access only.",
        fg="bright_yellow", bold=True,
    )
    choice = input("Do you want to continue? [y/n]: ").strip().lower()
    if choice != 'y':
        raise SystemExit(0)

    # 2. Verify GitHub write access
    # The token isn't needed here since git operations use GCM, so we only call
    # the get_github_token() function to check if the user has git write access.
    _ = get_github_token()

    # 3. Fetch first, then check if tag already exists on remote
    print(f"\n==> Fetching '{EMBEETLE_REPO}'...")
    run_native(["git", "-C", str(EMBEETLE_REPO), "fetch", "--all"])
    result = subprocess.run(
        ["git", "-C", str(EMBEETLE_REPO), "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
        capture_output=True, text=True,
    )
    if result.stdout.strip():
        printc(
            f"\nERROR: Tag '{tag}' already exists on the remote. "
            f"Did someone else already set this version?",
            fg="bright_red",
        )
        raise SystemExit(1)

    # 3. Update version.txt in the repo
    version_file = EMBEETLE_REPO / "beetle_core" / "version.txt"
    if not version_file.exists():
        raise RuntimeError(f"Version file not found at '{version_file}'")
    today = datetime.now().strftime("%d %b %Y")
    content = version_file.read_text(encoding="utf-8")
    content = re.sub(r"version:\s*[0-9.]+", f"version: {version}", content)
    content = re.sub(r"repo date:\s*.*", f"repo date: {today}", content)
    version_file.write_text(content, encoding="utf-8")
    print(f"\n==> Updated '{version_file}':")
    print(f"    version:   {version}")
    print(f"    repo date: {today}")

    # 4. Commit, tag, push
    run_native(["git", "-C", str(EMBEETLE_REPO), "add", "beetle_core/version.txt"])
    run_native(["git", "-C", str(EMBEETLE_REPO), "commit", "-m", tag])
    run_native(["git", "-C", str(EMBEETLE_REPO), "tag", tag])
    run_native(["git", "-C", str(EMBEETLE_REPO), "push"])
    run_native(["git", "-C", str(EMBEETLE_REPO), "push", "origin", tag])

    print(f"\nVersion '{tag}' set and pushed to remote.")


def inc_version() -> None:
    """
    Read the current version from the Embeetle repo, increment the patch number by 1,
    and call set_version() with the result.
    For developers only (requires git push access).
    """
    assert EMBEETLE_REPO is not None

    version_file = EMBEETLE_REPO / "beetle_core" / "version.txt"
    if not version_file.exists():
        raise RuntimeError(f"Version file not found at '{version_file}'")
    content = version_file.read_text(encoding="utf-8")
    match = re.search(r"version:\s*([0-9]+)\.([0-9]+)\.([0-9]+)", content)
    if not match:
        raise RuntimeError(f"Could not find version number in '{version_file}'")
    major, minor, patch = match.group(1), match.group(2), match.group(3)
    new_version = f"{major}.{minor}.{int(patch) + 1}"
    print(f"\nCurrent version: {major}.{minor}.{patch}")
    print(f"New version:     {new_version}")
    set_version(new_version)


def upload() -> None:
    """
    Upload the 7z build artifact to the GitHub Embeetle release page.
    For developers only (requires git push access and a GitHub token).
    """
    assert EMBEETLE_REPO is not None
    assert BUILD_DIR is not None

    # 1. Developer warning
    printc(
        f"\nWARNING: --upload is for developers with git write access only.",
        fg="bright_yellow", bold=True,
    )
    choice = input("Do you want to continue? [y/n]: ").strip().lower()
    if choice != 'y':
        raise SystemExit(0)

    # 2. Verify GitHub write access
    token = get_github_token()

    # 3. Read version from build output
    version_file = BUILD_DIR / f"embeetle-{PLATFORM}" / "beetle_core" / "version.txt"
    if not version_file.exists():
        raise RuntimeError(
            f"Build version file not found at '{version_file}'. "
            f"Did you run --build-embeetle first?"
        )
    content = version_file.read_text(encoding="utf-8")
    version_match = re.search(r"version:\s*([0-9.]+)", content)
    if not version_match:
        raise RuntimeError(f"Could not find version number in '{version_file}'")
    version = version_match.group(1)
    repo_version_file = EMBEETLE_REPO / "beetle_core" / "version.txt"
    if not repo_version_file.exists():
        raise RuntimeError(f"Repo version file not found at '{repo_version_file}'.")
    repo_content = repo_version_file.read_text(encoding="utf-8")
    repo_version_match = re.search(r"version:\s*([0-9.]+)", repo_content)
    if not repo_version_match:
        raise RuntimeError(f"Could not find version number in '{repo_version_file}'")
    repo_version = repo_version_match.group(1)
    if version != repo_version:
        raise RuntimeError(
            f"Version mismatch: build output has '{version}' but repo has '{repo_version}'.\n"
            f"  Build: {version_file}\n"
            f"  Repo:  {repo_version_file}\n"
            f"The build may be stale. Re-run --build-embeetle to sync them."
        )
    tag = f"v{version}"
    print(f"\nBuild version: {tag}")

    # 3. Check tag exists on remote
    result = subprocess.run(
        ["git", "-C", str(EMBEETLE_REPO), "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
        capture_output=True, text=True,
    )
    if not result.stdout.strip():
        printc(
            f"\nERROR: Tag '{tag}' does not exist on the remote. "
            f"Please run --set-version {version} first.",
            fg="bright_red",
        )
        raise SystemExit(1)

    # 4. Check archive exists
    archive = BUILD_DIR / f"embeetle-{PLATFORM}.7z"
    if not archive.exists():
        raise RuntimeError(
            f"Archive not found at '{archive}'. "
            f"Did you run --build-embeetle first?"
        )
    asset_name = f"embeetle-{PLATFORM}.7z"

    # Helper for GitHub REST API calls
    def _gh_api(method: str, url: str, data: dict = None) -> Optional[dict]:
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "automate_builds/1.0",
            },
        )
        last_exc = None
        for attempt in range(3):
            if attempt:
                time.sleep(2 ** attempt)
            try:
                with urllib.request.urlopen(req) as resp:
                    body = resp.read()
                    return json.loads(body) if body else None
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                raise RuntimeError(f"GitHub API error {e.code}: {e.read().decode()}")
            except urllib.error.URLError as e:
                if isinstance(e.reason, OSError):
                    last_exc = e
                    continue
                raise RuntimeError(f"GitHub API network error: {e.reason}")
        raise RuntimeError(
            f"GitHub API unreachable after 3 attempts (last error: {last_exc})"
        )

    # 6. Find or create the release
    print(f"\n==> Checking GitHub release for '{tag}'...")
    release = _gh_api("GET", f"https://api.github.com/repos/{GITHUB_EMBEETLE_REPO}/releases/tags/{tag}")
    if release is None:
        print(f"\nRelease notes (press Enter for 'Release {tag}'):")
        notes = input("> ").strip()
        if not notes:
            notes = f"Release {tag}"
        print(f"==> Creating release '{tag}'...")
        release = _gh_api(
            "POST",
            f"https://api.github.com/repos/{GITHUB_EMBEETLE_REPO}/releases",
            {"tag_name": tag, "name": tag, "body": notes},
        )
    release_id = release["id"]

    # Helper: delete existing release asset by name (makes re-runs idempotent)
    def _delete_asset_if_exists(name: str) -> None:
        assets = _gh_api("GET", f"https://api.github.com/repos/{GITHUB_EMBEETLE_REPO}/releases/{release_id}/assets")
        if assets:
            for asset in assets:
                if asset["name"] == name:
                    print(f"==> Deleting existing asset '{name}'...")
                    _gh_api("DELETE", f"https://api.github.com/repos/{GITHUB_EMBEETLE_REPO}/releases/assets/{asset['id']}")
                    break

    # Helper: upload a file as a release asset (streamed in chunks)
    def _upload_asset(file_path: Path, content_type: str) -> None:
        name = file_path.name
        size = file_path.stat().st_size
        size_mb = size / 1_048_576
        path = (
            f"/repos/{GITHUB_EMBEETLE_REPO}"
            f"/releases/{release_id}/assets?name={name}"
        )
        CHUNK = 8 * 1024 * 1024  # 8 MB
        MAX_ATTEMPTS = 5
        for attempt in range(1, MAX_ATTEMPTS + 1):
            _delete_asset_if_exists(name)
            if attempt == 1:
                print(f"==> Uploading '{name}' ({size_mb:.1f} MB)...")
            else:
                print(f"==> Uploading '{name}' ({size_mb:.1f} MB)... (attempt {attempt}/{MAX_ATTEMPTS})")
            try:
                ctx = ssl.create_default_context()
                conn = http.client.HTTPSConnection("uploads.github.com", context=ctx, timeout=600)
                conn.connect()
                conn.putrequest("POST", path)
                conn.putheader("Authorization", f"Bearer {token}")
                conn.putheader("Accept", "application/vnd.github+json")
                conn.putheader("X-GitHub-Api-Version", "2022-11-28")
                conn.putheader("Content-Type", content_type)
                conn.putheader("Content-Length", str(size))
                conn.endheaders()
                sent = 0
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(CHUNK)
                        if not chunk:
                            break
                        conn.send(chunk)
                        sent += len(chunk)
                        print(f"\r    {sent / 1_048_576:.1f} / {size_mb:.1f} MB  ({sent / size * 100:.0f}%)", end="", flush=True)
                print()
                resp = conn.getresponse()
                body = resp.read()
                conn.close()
                if resp.status not in (200, 201):
                    raise RuntimeError(f"Upload failed: HTTP {resp.status}: {body.decode()}")
                result = json.loads(body)
                print(f"    -> {result['browser_download_url']}")
                return
            except OSError as e:
                print()
                if attempt < MAX_ATTEMPTS:
                    wait = 2 ** attempt
                    printc(
                        f"    Connection error during upload: {e}\n"
                        f"    Retrying in {wait}s...",
                        fg="bright_yellow",
                    )
                    time.sleep(wait)
                else:
                    printc(
                        f"\nERROR: Upload failed after {MAX_ATTEMPTS} attempts: {e}",
                        fg="bright_red",
                    )
                    raise SystemExit(1)

    # 7. Upload the .7z archive
    _upload_asset(archive, "application/x-7z-compressed")

    # 8. Upload version.txt from the Embeetle repo (not the build output)
    version_txt = EMBEETLE_REPO / "beetle_core" / "version.txt"
    if not version_txt.exists():
        raise RuntimeError(f"version.txt not found at '{version_txt}'.")
    _upload_asset(version_txt, "text/plain")


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
    parser.add_argument("--set-version", metavar="x.y.z", default=None)
    parser.add_argument("--inc-version", action="store_true")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--check-access", action="store_true")
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

    # CONFIGURE GIT AUTH FROM TOKEN (if available)
    setup_git_auth_from_token()

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
        check_git_lfs_ready()
        clone_or_update_repo("https://github.com/Embeetle/embeetle.git", EMBEETLE_REPO)
        clone_or_update_repo("https://github.com/Embeetle/llvm.git", LLVM_REPO)
        clone_or_update_repo("https://github.com/Embeetle/sa.git", SA_REPO)
        # Note the change to sys-<PLATFORM>
        clone_or_update_repo(f"https://github.com/Embeetle/sys-{PLATFORM}.git", SYS_REPO)
        fix_sys_permissions(SYS_REPO)
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

    if args.set_version:
        printc("\nSET VERSION", fg="bright_blue")
        printc("===========", fg="bright_blue")
        set_version(args.set_version)

    if args.inc_version:
        printc("\nINC VERSION", fg="bright_blue")
        printc("===========", fg="bright_blue")
        inc_version()

    if args.check_access:
        printc("\nCHECK ACCESS", fg="bright_blue")
        printc("============", fg="bright_blue")
        _ = get_github_token()

    if args.upload:
        printc("\nUPLOAD", fg="bright_blue")
        printc("======", fg="bright_blue")
        upload()

    if not any([args.install_docker, args.clean_docker, args.clone, args.install_packages, args.build_llvm, args.build_sa, args.install_sa, args.build_embeetle, args.all, args.set_version, args.inc_version, args.upload, args.check_access]):
        print("\nNo action chosen. Print help...")
        _help()

    return 0

if __name__ == "__main__":

    raise SystemExit(main())