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

from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Iterable, Optional, Tuple
from typing import *
import hashlib
import fnmatch
import argparse
import re
import json
import urllib.request
import urllib.error

MSYS2_ROOT: Path = Path("C:/msys64")
MSYS2_HOME: Optional[Path] = None     # eg. 'C:/msys64/home/krist'
EMBEETLE_REPO: Optional[Path] = None  # eg. 'C:/msys64/home/krist/embeetle'
LLVM_REPO: Optional[Path] = None      # eg. 'C:/msys64/home/krist/llvm'
SA_REPO: Optional[Path] = None        # eg. 'C:/msys64/home/krist/sa'
SYS_REPO: Optional[Path] = None       # eg. 'C:/msys64/home/krist/embeetle/sys'
BUILD_DIR: Optional[Path] = None      # eg. 'C:/msys64/home/krist/bld'
PLATFORM: str = "windows-x86_64"
GITHUB_EMBEETLE_REPO: str = "Embeetle/embeetle"


def _help() -> None:
    """
    Help message
    """
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
    print(f"way from cloning the repos to the final builds. For now it only works on")
    print(f"Windows.")
    print(f"")
    print(f"{c('PREREQUISITES', fg='bright_blue')}")
    print(f"    Make sure you meet these requirements:")
    print(f"    ")
    print(f"        - Install Git for Windows (https://git-scm.com/install/windows),")
    print(f"          test it in a Windows CMD shell: {c('> git --version', fg='bright_yellow')}")
    print(f"    ")
    print(f"        - Install Python3.14+ for Windows (https://www.python.org/),")
    print(f"          test it in a Windows CMD shell: {c('> python --version', fg='bright_yellow')}")
    print(f"    ")
    print(f"        - Install MSYS2 (preferrably at {c('C:/msys64', fg='bright_yellow')})")
    print(f"    ")
    print(f"        - You can place this script anywhere. It doesn't rely on where the script")
    print(f"          itself is located. Instead, it actively queries MSYS2 to find the home")
    print(f"          directory (the ~ path in MSYS2) and uses that as the default location")
    print(f"          for cloning the repos and building.")
    print(f"    ")
    print(f"    {c('WARNING: Do not run this tool in an MSYS shell!', fg='bright_red')} Instead, run it from the")
    print(f"    native CMD shell. The tool launches MSYS shells automatically and redirects")
    print(f"    the output whenever needed.")
    print(f"    ")
    print(f"{c('USAGE', fg='bright_blue')}")
    print(f"    All parameters are optional:")
    print(f"    ")
    print(f"    {c('-h', fg='bright_cyan')}, {c('--help', fg='bright_cyan')}                    Show this help message and quit.")
    print(f"    ")
    print(f"    {c('--msys-root', fg='bright_cyan')} {c('MSYS2_ROOT', fg='bright_yellow')}        Path to MSYS2 root directory.")
    print(f"                                  Defaults to: {c("'C:/msys64'", fg='bright_yellow')}")
    print(f"    ")
    print(f"    {c('--embeetle-repo', fg='bright_cyan')} {c('EMBEETLE_REPO', fg='bright_yellow')} Path to Embeetle repo.")
    print(f"                                  Defaults to: {c("'<MSYS2_HOME>/embeetle'", fg='bright_yellow')}")
    print(f"    ")
    print(f"    {c('--llvm-repo', fg='bright_cyan')} {c('LLVM_REPO', fg='bright_yellow')}         Path to LLVM repo.")
    print(f"                                  Defaults to: {c("'<MSYS2_HOME>/llvm'", fg='bright_yellow')}")
    print(f"    ")
    print(f"    {c('--sa-repo', fg='bright_cyan')} {c('SA_REPO', fg='bright_yellow')}             Path to SA repo.")
    print(f"                                  Defaults to: {c("'<MSYS2_HOME>/sa'", fg='bright_yellow')}")
    print(f"    ")
    print(f"    {c('--output', fg='bright_cyan')} {c('BUILD_DIR', fg='bright_yellow')}            Path to build output.")
    print(f"                                  Defaults to: {c("'<MSYS2_HOME>/bld'", fg='bright_yellow')}")
    print(f"    ")
    print(f"    {c('--clone', fg='bright_cyan')}            Clone and/or update all repos")
    print(f"    ")
    print(f"    {c('--install-packages', fg='bright_cyan')} Install all required MSYS2 packages")
    print(f"    ")
    print(f"    {c('--build-llvm', fg='bright_cyan')}       Build LLVM:")
    print(f"                           sources: {c('<LLVM_REPO>', fg='bright_yellow')}")
    print(f"                           output:  {c('<BUILD_DIR>/llvm', fg='bright_yellow')}")
    print(f"    ")
    print(f"    {c('--build-sa', fg='bright_cyan')}         Build SA:")
    print(f"                           sources: {c('<SA_REPO>', fg='bright_yellow')}")
    print(f"                           output:  {c('<BUILD_DIR>/sa', fg='bright_yellow')}")
    print(f"    ")
    print(f"    {c('--install-sa', fg='bright_cyan')}       Install SA; copy its build output into Embeetle sources:")
    print(f"                           copy from: {c(f'<BUILD_DIR>/sa/sys-{PLATFORM}', fg='bright_yellow')}")
    print(f"                           into:      {c('<EMBEETLE_REPO>/sys', fg='bright_yellow')}")
    print(f"                       It will *also* copy into {c(f'<BUILD_DIR>/embeetle-{PLATFORM}/sys', fg='bright_yellow')} if")
    print(f"                       that folder exists (Embeetle was built before).")
    print(f"    ")
    print(f"    {c('--build-embeetle', fg='bright_cyan')}   Build Embeetle")
    print(f"                           sources: {c('<EMBEETLE_REPO>', fg='bright_yellow')}")
    print(f"                           output:  {c('<BUILD_DIR>/embeetle-<PLATFORM>', fg='bright_yellow')}")
    print(f"                       When building Embeetle, the content of the 'sys' folder")
    print(f"                       in the Embeetle repo is transferred to the Embeetle")
    print(f"                       build.")
    print(f"                       So if you did a {c('--install-sa', fg='bright_cyan')} command earlier you have the")
    print(f"                       latest SA build output in your Embeetle build as well.")
    print(f"                       {c('Note:', fg='bright_magenta')} This step automatically creates a Python virtual")
    print(f"                       environment at {c('<BUILD_DIR>/embeetle_venv', fg='bright_yellow')} and safely")
    print(f"                       installs all required dependencies in isolation.")
    print(f"    ")
    print(f"    {c('--all', fg='bright_cyan')}              Do everything:")
    print(f"                           {c('--clone', fg='bright_cyan')}")
    print(f"                           {c('--install-packages', fg='bright_cyan')}")
    print(f"                           {c('--build-llvm', fg='bright_cyan')}")
    print(f"                           {c('--build-sa', fg='bright_cyan')}")
    print(f"                           {c('--install-sa', fg='bright_cyan')}")
    print(f"                           {c('--build-embeetle', fg='bright_cyan')}")
    print(f"    ")
    print(f"    ")
    print(f"{c('RESULTS', fg='bright_blue')}")
    print(f"    Running this script with the default parameters and the {c('--all', fg='bright_cyan')} flag should")
    print(f"    result in:")
    print(f"    ")
    print(f"        {c('<MSYS2_HOME>', fg='bright_yellow')}")
    print(f"              ├─ bld")
    print(f"              │   ├─ embeetle-<PLATFORM>")
    print(f"              │   ├─ embeetle_venv  {c('<-- Isolated Python environment', fg='bright_black')}")
    print(f"              │   ├─ llvm")
    print(f"              │   └─ sa")
    print(f"              ├─ embeetle  ")
    print(f"              ├─ llvm  ")
    print(f"              └─ sa  ")
    print(f"    ")
    print(f"    To run Embeetle..")
    print(f"    ")
    print(f"        {c('..from sources:', fg='bright_magenta')}")
    print(f"            Open a native(!) Windows CMD shell.")
    print(f"            Navigate to the embeetle repo at {c('<MSYS_HOME>/embeetle/beetle_core', fg='bright_yellow')} and")
    print(f"            launch Embeetle using the generated virtual environment:")
    print(f"                {c('>', fg='bright_green')} {c('<MSYS2_HOME>/bld/embeetle_venv/Scripts/activate.bat', fg='bright_yellow')}")
    print(f"                {c('(embeetle_venv) >', fg='bright_green')} {c(' cd <MSYS2_HOME>/embeetle/beetle_core', fg='bright_yellow')}")
    print(f"                {c('(embeetle_venv) >', fg='bright_green')} {c(' python embeetle.py', fg='bright_yellow')}")
    print(f"    ")
    print(f"        {c('..from the executable:', fg='bright_magenta')}")
    print(f"            Navigate to the embeetle build at {c('<MSYS_HOME>/bld/embeetle-<PLATFORM>', fg='bright_yellow')} and")
    print(f"            launch {c('embeetle.exe', fg='bright_yellow')}.")
    print(f"    ")
    return


def _enable_color_printing() -> None:
    """
    Enable ANSI escape processing in Windows console (cmd/PowerShell).
    Safe to call multiple times. No-op on non-Windows.
    """
    if os.name != "nt":
        return
    try:
        import ctypes  # stdlib

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
        if handle == 0 or handle == -1:
            return

        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return

        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(handle, new_mode)
    except Exception:
        # If it fails, we just print without color.
        return

_enable_color_printing()

def c(text: str, *, fg: str | None = None, bold: bool = False) -> str:
    """
    Colorize text with ANSI SGR codes.
    fg: one of {black, red, green, yellow, blue, magenta, cyan, white, bright_black, ...}
    """
    codes: list[str] = []
    if bold:
        codes.append("1")

    fg_map = {
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "bright_black": "90",
        "bright_red": "91",
        "bright_green": "92",
        "bright_yellow": "93",
        "bright_blue": "94",
        "bright_magenta": "95",
        "bright_cyan": "96",
        "bright_white": "97",
    }
    if fg:
        code = fg_map.get(fg.lower())
        if code:
            codes.append(code)

    if not codes:
        return text
    ANSI_RESET = "\x1b[0m"
    return f"\x1b[{';'.join(codes)}m{text}{ANSI_RESET}"


def printc(
    *args,
    fg: Optional[str] = None,
    bold: bool = False,
    **kwargs,
) -> None:
    """Print the given text in the requested color. This function simply over-
    rides the builtin print() function and adds characters to give the text
    a color in the terminal.

        :param args:    Text to print. Normally this is a string, but it can
                        actually be anything that can be converted into a
                        string. It can be several values as well which will then
                        be concatenated by the 'sep' parameter.

        :param kwargs:  The keyword parameters from the builtin print() function:
                        > sep:     String inserted between values, defaults to a space.
                        > end:     String appended after the last value, defaults to a newline.
                        > file:    A file-like object (stream); defaults to the current sys.stdout.
                        > flush:   Forcibly flush the stream.

        :param color:   Pass a color for the text. Choose one of these:
                            - None (default color)
                            - 'default'
                            - 'black'
                            - 'red'
                            - 'green'
                            - 'yellow'
                            - 'blue'
                            - 'magenta'
                            - 'cyan'
                            - 'white'

        :param bright:  Make the color look brighter. This parameter only has
                        effect if you passed an actual color in the previous
                        parameter.
    """
    if fg is None or fg.lower() == "default":
        print(*args, **kwargs)
        return

    # Extract 'sep' from kwargs to join the args (defaults to a space).
    # We use pop() so 'sep' isn't passed to the final print() call, 
    # since we are reducing the args to a single combined string.
    sep = kwargs.pop("sep", " ")
    text = sep.join(str(arg) for arg in args)

    # Colorize the concatenated string using the c() function.
    colorized_text = c(text, fg=fg, bold=bold)

    # Print the result, passing any remaining kwargs (like 'end', 'file', 'flush').
    return print(colorized_text, **kwargs)


def run_native(
    args: list[str],
    cwd: Optional[Path] = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a command natively on Windows (no shell), streaming output."""
    def fmt_cmd(args: Iterable[str]) -> str:
        def q(s: str) -> str:
            if any(ch in s for ch in [" ", "\t", '"']):
                return '"' + s.replace('"', r"\"") + '"'
            return s

        return " ".join(q(a) for a in args)

    print(f"\n[CMD] {fmt_cmd(args)}")
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
    )


def _msys2_bash() -> Path:
    bash = MSYS2_ROOT / "usr" / "bin" / "bash.exe"
    if not bash.exists():
        raise FileNotFoundError(f"bash.exe not found at: {bash}")
    return bash


def _msys2_ucrt64_env() -> dict[str, str]:
    """
    Create an environment that reliably behaves like the UCRT64 shell.
    """
    env = os.environ.copy()
    env["MSYSTEM"] = "UCRT64"
    env["CHERE_INVOKING"] = "1"
    env["MSYS2_PATH_TYPE"] = "inherit"

    prepend = [
        str(MSYS2_ROOT / "ucrt64" / "bin"),
        str(MSYS2_ROOT / "usr" / "bin"),
        str(MSYS2_ROOT / "bin"),
    ]
    env["PATH"] = ";".join(prepend + [env.get("PATH", "")])
    return env


def run_msys2_ucrt64(
    command: str,
    cwd: Optional[Path] = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command inside MSYS2 UCRT64 environment using bash.exe directly.
    This captures stdout/stderr reliably (unlike msys2_shell.cmd in some setups).
    """
    bash = _msys2_bash()
    env = _msys2_ucrt64_env()
    args = [str(bash), "--login", "-c", command]

    print(f"\n[MSYS2/UCRT64] {command}")
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=check,
        text=True,
    )


def run_msys2_ucrt64_capture(
    command: str,
    cwd: Optional[Path] = None,
) -> Tuple[int, str]:
    """
    Run a command inside MSYS2 UCRT64 and capture combined stdout/stderr.
    Returns: (returncode, output_text)
    """
    bash = _msys2_bash()
    env = _msys2_ucrt64_env()
    args = [str(bash), "--login", "-c", command]

    print(f"\n[MSYS2/UCRT64] {command}")
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.returncode, (proc.stdout or "")


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


def check_git_lfs_ready() -> None:
    """Ensure git-lfs is installed."""
    if shutil.which("git-lfs") is None:
        printc("\nERROR: git-lfs is not installed.", fg="bright_red", bold=True)
        printc("Git for Windows ships with git-lfs, but it may not be on your PATH.", fg="bright_yellow")
        printc("Please reinstall Git for Windows or install git-lfs manually.", fg="bright_yellow")
        raise SystemExit(1)
    # Set up LFS hooks globally (idempotent)
    run_native(["git", "lfs", "install"], check=False)
    return


def clone_or_update_repo(
    repo_url: str,
    repo_dir: Path,
) -> None:
    """
    Clone or update given repository.
    """
    repo_parent_dir = repo_dir.parent
    repo_parent_dir.mkdir(parents=True, exist_ok=True)

    # Check .git
    if repo_dir.exists() and not (repo_dir / ".git").exists():
        raise RuntimeError(f"Path exists but is not a git repo: {repo_dir}")

    # Clone
    if not repo_dir.exists():
        print(f"\n==> Cloning {repo_dir}...")
        # Add the -c flag here to force LF endings for this specific repo
        run_native(["git", "clone", "-c", "core.autocrlf=false", repo_url, str(repo_dir)], cwd=repo_parent_dir)
        run_native(["git", "-C", str(repo_dir), "lfs", "pull"])
        return

    # Fix existing repo if it has wrong line-ending config
    fix_git_config(repo_dir)

    # Update (fast-forward only avoids accidental merge commits)
    print(f"\n==> Updating {repo_dir}...")
    try:
        run_native(["git", "-C", str(repo_dir), "pull", "--ff-only"], cwd=repo_parent_dir)
    except subprocess.CalledProcessError:
        # If pull failed, check if working tree is dirty
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

        # Not dirty -> propagate original error
        raise
    run_native(["git", "-C", str(repo_dir), "lfs", "pull"])
    return


def determine_msys2_home() -> Path:
    """
    Ask MSYS2 what ~ expands to, and convert to a Windows path.
    """
    out = subprocess.check_output(
        [str(_msys2_bash()), "--login", "-c", "cygpath -w ~"],
        text=True,
        stderr=subprocess.STDOUT,
        env=_msys2_ucrt64_env(),
    ).strip()

    # If there are startup messages, take the last line.
    return Path(out.splitlines()[-1]).resolve()


def msys2_first_run_bootstrap(noconfirm: bool = True) -> None:
    """
    First-run bootstrap / repair step for MSYS2 pacman keyring & certs.
    Safe to run even on an already-initialized install.
    """
    flags = " --noconfirm" if noconfirm else ""

    run_msys2_ucrt64("pacman-key --init", check=False)
    run_msys2_ucrt64("pacman-key --populate msys2", check=False)

    run_msys2_ucrt64(f"pacman -Sy{flags}", check=False)
    run_msys2_ucrt64(
        f"pacman -S --needed{flags} msys2-keyring ca-certificates",
        check=False,
    )

    run_msys2_ucrt64("update-ca-trust", check=False)


def msys2_update_system(noconfirm: bool = True) -> None:
    """
    Update MSYS2 base system.
    MSYS2 recommends running 'pacman -Syu' twice.
    """
    flags = " --noconfirm" if noconfirm else ""

    required_successes = 2
    successes = 0
    attempts = 0
    max_attempts = 6

    bootstrapped = False

    while successes < required_successes and attempts < max_attempts:
        attempts += 1
        proc = run_msys2_ucrt64(f"pacman -Syu{flags}", check=False)

        if proc.returncode == 0:
            successes += 1
            continue

        successes = 0
        if not bootstrapped:
            print(
                "\n[INFO] pacman update failed; attempting MSYS2 bootstrap (keyring/certs) and retrying..."
            )
            msys2_first_run_bootstrap(noconfirm=noconfirm)
            bootstrapped = True
        else:
            print("\n[WARN] pacman update failed again; retrying...")

    if successes < required_successes:
        raise RuntimeError(
            f"MSYS2 update did not complete successfully after {attempts} attempts. "
            "Open an MSYS2 UCRT64 terminal and run 'pacman -Syu' manually to see details."
        )


def msys2_install_packages(packages: list[str], noconfirm: bool = True) -> None:
    """
    Install MSYS2 packages in UCRT64 shell.
    Uses --needed to skip already-installed packages.
    """
    flags = " --noconfirm" if noconfirm else ""
    pkg_str = " ".join(packages)
    run_msys2_ucrt64(f"pacman -S --needed{flags} {pkg_str}")


def _last_nonempty_line(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def msys2_check_tools() -> None:
    """
    Verify that key tools resolve to the UCRT64 prefix.
    Uses 'command -v' which returns the actual executable that would run.
    """

    def norm(s: str) -> str:
        return s.strip().replace("\\", "/")

    def expect(tool: str, expected_no_ext: str) -> None:
        rc, out = run_msys2_ucrt64_capture(f"command -v {tool}")
        if rc != 0:
            raise RuntimeError(
                f"Tool check failed for '{tool}' (rc={rc}).\nOutput:\n{out}"
            )

        got = norm(_last_nonempty_line(out))
        exp1 = expected_no_ext
        exp2 = expected_no_ext + ".exe"

        if got not in (exp1, exp2):
            # extra diagnostics
            rc2, out2 = run_msys2_ucrt64_capture(f"type -a {tool}")
            raise RuntimeError(
                f"Tool path check failed for '{tool}'.\n"
                f"Expected: {exp1} (or {exp2})\n"
                f"Got:      {got}\n\n"
                f"'type -a {tool}' output:\n{out2}"
            )

        print(f"[CHECK] {tool} resolves to {got} : OK")

    expect("cmake", "/ucrt64/bin/cmake")
    expect("ninja", "/ucrt64/bin/ninja")
    expect("gcc", "/ucrt64/bin/gcc")
    expect("g++", "/ucrt64/bin/g++")

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _sh_quote(s: str) -> str:
    # safe single-quote for bash
    return "'" + s.replace("'", "'\"'\"'") + "'"


def build_llvm() -> None:
    """
    Build LLVM:
      make -C <BUILD_DIR/llvm> -f <SA_REPO/Makefile> llvm
    """
    assert MSYS2_HOME is not None
    assert SA_REPO is not None
    assert LLVM_REPO is not None
    assert BUILD_DIR is not None

    llvm_bld: Path = BUILD_DIR / "llvm"
    sa_bld: Path = BUILD_DIR / "sa"

    # Create build dirs
    _ensure_dir(BUILD_DIR)
    _ensure_dir(llvm_bld)

    # Create empty folders in the SA repo if they don't exist
    _ensure_dir(SA_REPO / "sys" / "windows")
    _ensure_dir(SA_REPO / "sys" / "windows" / "lib")

    # Use the Makefile from the SA repo
    makefile = SA_REPO / "Makefile"
    if not makefile.exists():
        raise RuntimeError(
            f"Expected Makefile at '{makefile}', but it does not exist."
        )

    llvm_bld_s = llvm_bld.as_posix()
    makefile_s = makefile.as_posix()

    # Build llvm target
    run_msys2_ucrt64(
        f"make -C {_sh_quote(llvm_bld_s)} -f {_sh_quote(makefile_s)} llvm",
        cwd=llvm_bld,
        check=True,
    )
    return


def build_sa() -> None:
    """
    Build SA:
      make -C <BUILD_DIR/sa>   -f <SA_REPO/Makefile>
    """
    assert MSYS2_HOME is not None
    assert SA_REPO is not None
    assert LLVM_REPO is not None
    assert BUILD_DIR is not None

    llvm_bld: Path = BUILD_DIR / "llvm"
    sa_bld: Path = BUILD_DIR / "sa"

    # Create build dirs
    _ensure_dir(BUILD_DIR)
    _ensure_dir(llvm_bld)
    _ensure_dir(sa_bld)

    # Create empty folders in the SA repo if they don't exist
    _ensure_dir(SA_REPO / "sys" / "windows")
    _ensure_dir(SA_REPO / "sys" / "windows" / "lib")

    # Use the Makefile from the SA repo
    makefile = SA_REPO / "Makefile"
    if not makefile.exists():
        raise RuntimeError(
            f"Expected Makefile at '{makefile}', but it does not exist."
        )

    sa_bld_s = sa_bld.as_posix()
    makefile_s = makefile.as_posix()

    # Build SA target
    current_python = sys.executable.replace("\\", "/")
    run_msys2_ucrt64(
        f"make -C {_sh_quote(sa_bld_s)} -f {_sh_quote(makefile_s)} PYTHON_CMD={_sh_quote(current_python)}",
        cwd=sa_bld,
        check=True,
    )
    return


def mirror_dir(
    src: Union[str, Path],
    dst: Union[str, Path],
    delete: bool = False,
    checksum: bool = False,
    exclude: Iterable[str] = (".git/**", "__pycache__/**"),
    dry_run: bool = False,
) -> None:
    """
    One-way mirror: makes dst look like src.

    - delete=True    removes files/dirs present in dst but not src.
    - checksum=True  uses sha256 when size/mtime differ (slower but safer).
    - exclude        uses fnmatch patterns on POSIX-style relative paths.

    Example:
    mirror_dir(
        src = "C:/data/source",
        dst = "D:/backup/dest",
        delete = True,
        checksum = False,
    )
    """
    def _excluded(_rel_posix: str, patterns: Iterable[str]) -> bool:
        _pat: str
        _matched: bool = any(fnmatch.fnmatch(_rel_posix, _pat) for _pat in patterns)
        return _matched

    def _sha256(_p: Path) -> str:
        h: hashlib._Hash = hashlib.sha256()
        f: IO[bytes]
        chunk: bytes
        with _p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        digest: str = h.hexdigest()
        return digest

    src_path: Path = Path(src).resolve()
    dst_path: Path = Path(dst).resolve()

    if not src_path.is_dir():
        raise ValueError(f"src is not a directory: '{src_path}'")

    # 1) Copy/update from src -> dst
    s: Path
    for s in src_path.rglob("*"):
        rel: Path = s.relative_to(src_path)
        rel_posix: str = rel.as_posix()

        if _excluded(rel_posix, exclude):
            continue

        d: Path = dst_path / rel

        if s.is_dir():
            if not dry_run:
                d.mkdir(parents=True, exist_ok=True)
            continue

        if not s.is_file():
            continue  # skip symlinks/devices by default

        do_copy: bool = False
        if not d.exists():
            do_copy = True
        else:
            ss: os.stat_result = s.stat()
            ds: os.stat_result = d.stat()
            if ss.st_size != ds.st_size or int(ss.st_mtime) != int(ds.st_mtime):
                do_copy = True
                if checksum and d.is_file():
                    do_copy = _sha256(s) != _sha256(d)

        if do_copy:
            if dry_run:
                print(f"COPY {s} -> {d}")
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)  # preserves mtime; best-effort metadata
                                    # cross-platform

    # 2) Delete extras from dst if requested
    if delete:
        d: Path
        for d in sorted(dst_path.rglob("*"), reverse=True):
            rel: Path = d.relative_to(dst_path)
            rel_posix: str = rel.as_posix()

            if _excluded(rel_posix, exclude):
                continue

            s: Path = src_path / rel
            if not s.exists():
                if dry_run:
                    print(f"DELETE {d}")
                else:
                    if d.is_dir():
                        # Remove only if empty; if not empty (e.g., contains
                        # excluded items), leave it.
                        try:
                            d.rmdir()
                        except OSError:
                            pass
                    else:
                        d.unlink()


def msys2_uname_m() -> str:
    """
    Determine arch as MSYS2 sees it (matches Makefile logic).
    """
    rc, out = run_msys2_ucrt64_capture("uname -m")
    if rc != 0:
        return "x86_64"
    arch = _last_nonempty_line(out).strip()
    if arch in ("amd64", "x64"):
        arch = "x86_64"
    return arch


def install_sa_sys_into_embeetle_sys() -> None:
    """
    Copy the contents of '<BUILD_DIR>/sa/sys-<PLATFORM>' into:
      - '<EMBEETLE_REPO>/sys'
      - '<BUILD_DIR>/embeetle-<PLATFORM>/sys'

    Behavior:
      - Overlay-copy everything (overwrite existing, do NOT delete extras)
      - EXCEPT: mirror the 'esa' subtree (delete extras in destination/esa)
    """
    assert BUILD_DIR is not None
    assert EMBEETLE_REPO is not None

    src_sys: Path = BUILD_DIR / f"sa/sys-{PLATFORM}"
    dst_sys: Path = EMBEETLE_REPO / "sys"
    dst2_sys: Path = BUILD_DIR / f"embeetle-{PLATFORM}/sys"

    if not dst_sys.is_dir():
        raise RuntimeError(
            f"Destination sys folder does not exist: '{dst_sys}'"
        )
    if not dst2_sys.is_dir():
        pass

    print(f"\n==> Installing SA sys overlay:")
    print(f"    src: '{src_sys}'")
    print(f"    dst: '{dst_sys}'")
    if dst2_sys.is_dir():
        print(f"         and '{dst2_sys}'")

    # 1) Overlay copy (no deletions)
    mirror_dir(
        src=src_sys,
        dst=dst_sys,
        delete=False,
        checksum=False,
        exclude=(".git/**", "__pycache__/**"),
        dry_run=False,
    )
    if dst2_sys.is_dir():
        mirror_dir(
            src=src_sys,
            dst=dst2_sys,
            delete=False,
            checksum=False,
            exclude=(".git/**", "__pycache__/**"),
            dry_run=False,
        )

    # 2) Mirror only the 'esa' subtree (delete extras in destination/esa)
    src_esa = src_sys / "esa"
    dst_esa = dst_sys / "esa"
    dst2_esa = dst2_sys / "esa"

    if not src_esa.is_dir():
        raise RuntimeError(
            f"Expected '{src_esa}' to exist (esa folder in SA sys output)."
        )
    mirror_dir(
        src=src_esa,
        dst=dst_esa,
        delete=True,
        checksum=False,
        exclude=(".git/**", "__pycache__/**"),
        dry_run=False,
    )
    if dst2_sys.is_dir():
        mirror_dir(
            src=src_esa,
            dst=dst2_esa,
            delete=True,
            checksum=False,
            exclude=(".git/**", "__pycache__/**"),
            dry_run=False,
        )
    return


def get_venv_info(venv_python: Path) -> Tuple[str, str]:
    """
    Query the venv for its Python version string and pip freeze list.
    """
    if not venv_python.exists():
        return "N/A", "N/A"
    try:
        py_ver = subprocess.check_output(
            [str(venv_python), "-c", "import sys; print(sys.version)"], text=True
        ).strip()
        pip_freeze = subprocess.check_output(
            [str(venv_python), "-m", "pip", "freeze"], text=True
        ).strip()
        return py_ver, pip_freeze
    except Exception as e:
        printc(f"    [ERROR] Could not query venv: {e}", fg="bright_red")
        return "Unknown", "Unknown"


def update_version_file(
    repo_dir: Path, 
    build_dir: Path, 
    venv_python: Path, 
) -> None:
    """
    Read `version.txt` from the repo, extract the repo version and date, and
    write a new `version.txt` in the build directory. The new version file
    includes:
        - Embeetle version (from repo)
        - Repo date (from repo)
        - Build date (current date)
        - Platform (hardcoded as <PLATFORM>)
        - Python version (queried from the venv)
        - Installed packages (queried from the venv)
    """
    version_file_rel: Path = Path("beetle_core/version.txt")
    repo_version_path: Path = repo_dir / version_file_rel
    build_version_path: Path = build_dir / version_file_rel

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
    #     platform: windows-x86_64
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
    #     version: 3.14.2 (tags/v3.14.2:df79316, Dec  5 2025, 17:18:21) [MSC v.1944 64 bit (AMD64)]
    assert venv_python.exists(), f"Venv Python not found at '{venv_python}'"
    py_ver = get_venv_info(venv_python)[0]
    pkgs = get_venv_info(venv_python)[1]
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
    return


def build_embeetle() -> None:
    """
    Build Embeetle from '<EMBEETLE_REPO>' to '<BUILD_DIR>/embeetle-<PLATFORM>'
    """
    assert MSYS2_HOME is not None
    assert EMBEETLE_REPO is not None
    assert BUILD_DIR is not None

    embeetle_bld: Path = BUILD_DIR / f"embeetle-{PLATFORM}"
    venv_dir: Path = BUILD_DIR / "embeetle_venv"

    # Create build dirs
    _ensure_dir(BUILD_DIR)
    _ensure_dir(embeetle_bld)

    # 1. Create the virtual environment if it doesn't exist
    if not venv_dir.exists():
        print(f"\n==> Creating Python virtual environment at '{venv_dir}'...")
        # We use sys.executable to ensure the venv uses the exact same Python 
        # version that is currently running this automation script.
        run_native([sys.executable, "-m", "venv", str(venv_dir)])

    # 2. Path to the Python executable inside the venv (Windows specific)
    venv_python = venv_dir / "Scripts" / "python.exe"
    if not venv_python.exists():
        raise RuntimeError(f"Failed to find venv Python at '{venv_python}'")

    # 3. Install requirements into the venv
    req_file = EMBEETLE_REPO / "requirements.txt"
    if req_file.exists():
        print(f"\n==> Installing/Updating pip requirements from '{req_file}'...")
        run_native(
            [str(venv_python), "-m", "pip", "install", "-r", str(req_file)],
            cwd=EMBEETLE_REPO,
            check=True,
        )
    else:
        printc(f"\n[WARN] No requirements.txt found at '{req_file}'. Skipping pip install.", fg="bright_yellow")

    # 4. Build Embeetle using the venv's Python
    print(f"\n==> Running Embeetle build.py...")
    run_native(
        [
            str(venv_python),
            "build.py",
            "--repo",
            str(EMBEETLE_REPO).replace("\\", "/"),
            "--output",
            str(embeetle_bld).replace("\\", "/"),
        ],
        cwd=EMBEETLE_REPO,
        check=True,
    )

    # 5. Update version file
    update_version_file(EMBEETLE_REPO, embeetle_bld, venv_python)

    # 6. Create 7zip archive
    seven_zip: Path = EMBEETLE_REPO / "sys" / "bin" / "7za.exe"
    embeetle_archive: Path = BUILD_DIR / f"embeetle-{PLATFORM}.7z"
    if embeetle_archive.exists():
        embeetle_archive.unlink()
    print(f"\n==> Creating archive '{embeetle_archive}'...")
    run_native(
        [
            str(seven_zip), "a",
            f"embeetle-{PLATFORM}.7z",
            f"embeetle-{PLATFORM}",
            "-mx=9",           # Ultra compression
            "-mmt=on",         # Use all CPU cores
            "-md=128m",        # 128 MB dictionary for better ratio
            "-xr!__pycache__", # Exclude Python cache dirs
            "-xr!*.pyc",       # Exclude Python bytecode
            "-xr!.git",        # Exclude any accidentally included git dirs
            "-y",              # Non-interactive (assume yes)
        ],
        cwd=BUILD_DIR,
        check=True,
    )

    # 7. Print
    print(f"\nEmbeetle built at '{embeetle_bld}'")
    return


def get_github_token() -> str:
    """
    Verify the user has write access to the Embeetle GitHub repo.
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
            f"\nTo fix this, either:\n"
            f"  - Set the GITHUB_TOKEN environment variable to a personal access token, or\n"
            f"  - Sign in to GitHub via Git Credential Manager by running:\n"
            f"      git clone https://github.com/Embeetle/embeetle.git",
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
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read()), dict(resp.headers)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                printc("\nERROR: Invalid GitHub token (401 Unauthorized).", fg="bright_red")
            elif e.code == 403:
                printc("\nERROR: GitHub token lacks required permissions (403 Forbidden).", fg="bright_red")
            elif e.code == 404:
                printc(f"\nERROR: Resource not found (404): {url}", fg="bright_red")
            else:
                printc(f"\nERROR: GitHub API error {e.code}: {e.read().decode()}", fg="bright_red")
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
            f"\nERROR: Your GitHub token does not have write access to '{GITHUB_EMBEETLE_REPO}'.",
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
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise RuntimeError(f"GitHub API error {e.code}: {e.read().decode()}")

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

    # 7. Delete existing asset with same name (makes re-runs idempotent)
    assets = _gh_api("GET", f"https://api.github.com/repos/{GITHUB_EMBEETLE_REPO}/releases/{release_id}/assets")
    if assets:
        for asset in assets:
            if asset["name"] == asset_name:
                print(f"==> Deleting existing asset '{asset_name}'...")
                _gh_api("DELETE", f"https://api.github.com/repos/{GITHUB_EMBEETLE_REPO}/releases/assets/{asset['id']}")
                break

    # 8. Upload asset
    size_mb = archive.stat().st_size / 1_048_576
    print(f"==> Uploading '{asset_name}' ({size_mb:.1f} MB)...")
    file_data = archive.read_bytes()
    upload_url = (
        f"https://uploads.github.com/repos/{GITHUB_EMBEETLE_REPO}"
        f"/releases/{release_id}/assets?name={asset_name}"
    )
    req = urllib.request.Request(
        upload_url,
        data=file_data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/x-7z-compressed",
            "Content-Length": str(len(file_data)),
        },
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    print(f"\nUploaded: {result['browser_download_url']}")


def main() -> int:
    # CHECK PYTHON VERSION
    # ====================
    if sys.version_info < (3, 12):
        printc(
            f"\n[WARNING] You are running Python {sys.version_info.major}.{sys.version_info.minor}.",
            fg="bright_yellow", bold=True
        )
        printc(
            "Embeetle is tested on Python 3.14, and Python 3.12 is known to work.\n"
            "Using an older version is risky and may cause unexpected build or runtime errors.\n",
            fg="bright_yellow"
        )
        try:
            input("Press Enter to continue at your own risk, or Ctrl+C to abort... ")
        except KeyboardInterrupt:
            printc("\nBuild aborted by user.", fg="bright_red")
            sys.exit(1)
        print()  # Add an empty line for visual spacing

    # PARSE ARGUMENTS
    # ===============
    parser = argparse.ArgumentParser(
        description="Build Embeetle, LLVM and SA",
        add_help=False
    )
    parser.add_argument(
        "-h", "--help",
        action="store_true",
    )
    parser.add_argument(
        "--msys-root",
        required=False,
        default="C:/msys64",
    )
    parser.add_argument(
        "--embeetle-repo",
        required=False,
        default=None,
    )
    parser.add_argument(
        "--llvm-repo",
        required=False,
        default=None,
    )
    parser.add_argument(
        "--sa-repo",
        required=False,
        default=None,
    )
    parser.add_argument(
        "--output",
        required=False,
        default=None,
    )
    parser.add_argument(
        "--clone",
        action="store_true",
    )
    parser.add_argument(
        "--install-packages",
        action="store_true",
    )
    parser.add_argument(
        "--build-llvm",
        action="store_true",
    )
    parser.add_argument(
        "--build-sa",
        action="store_true",
    )
    parser.add_argument(
        "--install-sa",
        action="store_true",
    )
    parser.add_argument(
        "--build-embeetle",
        action="store_true",
    )
    parser.add_argument(
        "--all",
        action="store_true",
    )
    parser.add_argument(
        "--set-version",
        metavar="x.y.z",
        default=None,
    )
    parser.add_argument(
        "--upload",
        action="store_true",
    )
    parser.add_argument(
        "--check-access",
        action="store_true",
    )
    args = parser.parse_args()
    if args.help:
        _help()
        print("")
        input("Press any key to quit...")
        sys.exit(0)

    # DETERMINE LOCATIONS
    # ===================
    global MSYS2_ROOT, MSYS2_HOME
    global EMBEETLE_REPO, LLVM_REPO, SA_REPO, SYS_REPO
    global BUILD_DIR
    MSYS2_ROOT = Path(args.msys_root)
    if not (MSYS2_ROOT / "usr" / "bin" / "bash.exe").exists():
        print(
            f"MSYS2 bash not found at {(MSYS2_ROOT / 'usr' / 'bin' / 'bash.exe')}. "
            "Install MSYS2 to C:/msys64.",
            file=sys.stderr,
        )
        return 2
    MSYS2_HOME = determine_msys2_home()

    if args.embeetle_repo:
        EMBEETLE_REPO = Path(args.embeetle_repo)
    else:
        EMBEETLE_REPO = MSYS2_HOME / "embeetle"

    if args.llvm_repo:
        LLVM_REPO = Path(args.llvm_repo)
    else:
        LLVM_REPO = MSYS2_HOME / "llvm"

    if args.sa_repo:
        SA_REPO = Path(args.sa_repo)
    else:
        SA_REPO = MSYS2_HOME / "sa"

    SYS_REPO = EMBEETLE_REPO / "sys"

    if args.output:
        BUILD_DIR = Path(args.output)
    else:
        BUILD_DIR = MSYS2_HOME / "bld"

    print(f"{c('MSYS2_ROOT', fg='bright_yellow')}    = '{MSYS2_ROOT}'")
    print(f"{c('MSYS2_HOME', fg='bright_yellow')}    = '{MSYS2_HOME}'")
    print(f"{c('EMBEETLE_REPO', fg='bright_yellow')} = '{EMBEETLE_REPO}'")
    print(f"{c('SYS_REPO', fg='bright_yellow')}      = '{SYS_REPO}'")
    print(f"{c('LLVM_REPO', fg='bright_yellow')}     = '{LLVM_REPO}'")
    print(f"{c('SA_REPO', fg='bright_yellow')}       = '{SA_REPO}'")
    print(f"{c('BUILD_DIR', fg='bright_yellow')}     = '{BUILD_DIR}'")

    # CLONE REPOS
    # ===========
    if args.clone or args.all:
        printc("")
        printc("CLONE REPOS", fg="bright_blue")
        printc("===========", fg="bright_blue")
        check_git_lfs_ready()
        clone_or_update_repo(
            repo_url="https://github.com/Embeetle/embeetle.git",
            repo_dir=EMBEETLE_REPO,
        )
        clone_or_update_repo(
            repo_url="https://github.com/Embeetle/llvm.git",
            repo_dir=LLVM_REPO,
        )
        clone_or_update_repo(
            repo_url="https://github.com/Embeetle/sa.git",
            repo_dir=SA_REPO,
        )
        clone_or_update_repo(
            repo_url=f"https://github.com/Embeetle/sys-{PLATFORM}.git",
            repo_dir=SYS_REPO,
        )
        print("\nAll repositories are up to date.")

    # INSTALL PACKAGES
    # ================
    if args.install_packages or args.all:
        printc("")
        printc("INSTALL PACKAGES", fg="bright_blue")
        printc("================", fg="bright_blue")
        msys2_first_run_bootstrap(noconfirm=True)
        msys2_update_system(noconfirm=True)
        msys2_install_packages(
            [
                "git",
                "p7zip",
                "rsync",
                "base-devel",
                "mingw-w64-ucrt-x86_64-toolchain",
                "mingw-w64-ucrt-x86_64-cmake",
                "mingw-w64-ucrt-x86_64-ninja",
                "mingw-w64-ucrt-x86_64-pkgconf",
            ],
            noconfirm=True,
        )
        print("\nMSYS2 packages installed/updated.")
        msys2_check_tools()
        print("\nMSYS2 toolchain sanity checks passed.")

    # BUILD LLVM
    # ==========
    if args.build_llvm or args.all:
        printc("")
        printc("BUILD LLVM", fg="bright_blue")
        printc("==========", fg="bright_blue")
        build_llvm()
        print("\nLLVM build finished")

    # BUILD SA
    # ========
    if args.build_sa or args.all:
        printc("")
        printc("BUILD SA", fg="bright_blue")
        printc("========", fg="bright_blue")
        build_sa()
        print("\nSA build finished")

    # INSTALL SA
    # ==========
    if args.install_sa or args.all:
        printc("")
        printc("INSTALL SA", fg="bright_blue")
        printc("==========", fg="bright_blue")
        install_sa_sys_into_embeetle_sys()
        print("\nInstalled SA sys into Embeetle sys")

    # BUILD EMBEETLE
    # ==============
    if args.build_embeetle or args.all:
        printc("")
        printc("BUILD EMBEETLE", fg="bright_blue")
        printc("==============", fg="bright_blue")
        build_embeetle()

    # SET VERSION
    # ===========
    if args.set_version:
        printc("")
        printc("SET VERSION", fg="bright_blue")
        printc("===========", fg="bright_blue")
        set_version(args.set_version)

    # CHECK ACCESS
    # ============
    if args.check_access:
        printc("")
        printc("CHECK ACCESS", fg="bright_blue")
        printc("============", fg="bright_blue")
        _ = get_github_token()

    # UPLOAD
    # ======
    if args.upload:
        printc("")
        printc("UPLOAD", fg="bright_blue")
        printc("======", fg="bright_blue")
        upload()

    # DO NOTHING
    # ==========
    if not (
        args.clone or
        args.install_packages or
        args.build_llvm or
        args.build_sa or
        args.install_sa or
        args.build_embeetle or
        args.all or
        args.set_version or
        args.upload or
        args.check_access
    ):
        print("")
        print("No action chosen. Print help...")
        _help()
        print("")
        input("Press any key to quit...")
        sys.exit(0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())