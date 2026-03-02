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
from typing import Iterable, Optional, Tuple
from typing import *
import hashlib
import fnmatch
import argparse

MSYS2_ROOT: Path = Path("C:/msys64")
MSYS2_HOME: Optional[Path] = None     # eg. 'C:/msys64/home/krist'
EMBEETLE_REPO: Optional[Path] = None  # eg. 'C:/msys64/home/krist/embeetle'
LLVM_REPO: Optional[Path] = None      # eg. 'C:/msys64/home/krist/llvm'
SA_REPO: Optional[Path] = None        # eg. 'C:/msys64/home/krist/sa'
SYS_REPO: Optional[Path] = None       # eg. 'C:/msys64/home/krist/embeetle/sys'
BUILD_DIR: Optional[Path] = None      # eg. 'C:/msys64/home/krist/bld'


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
    print(f"                           copy from: {c('<BUILD_DIR>/sa/sys-windows-x86_64', fg='bright_yellow')}")
    print(f"                           into:      {c('<EMBEETLE_REPO>/sys', fg='bright_yellow')}")
    print(f"                       It will *also* copy into {c('<BUILD_DIR>/embeetle/sys', fg='bright_yellow')} if")
    print(f"                       that folder exists (Embeetle was built before).")
    print(f"    ")
    print(f"    {c('--build-embeetle', fg='bright_cyan')}   Build Embeetle")
    print(f"                           sources: {c('<EMBEETLE_REPO>', fg='bright_yellow')}")
    print(f"                           output:  {c('<BUILD_DIR>/embeetle', fg='bright_yellow')}")
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
    print(f"              │   ├─ embeetle")
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
    print(f"            Navigate to the embeetle build at {c('<MSYS_HOME>/bld/embeetle', fg='bright_yellow')} and")
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
                f"\nERROR: Cannot update repo because it has local (unstaged/modified) changes:\n"
                f"  {repo_dir}\n\n"
                f"Please commit, stash, or revert these changes and rerun.\n"
                f"Git status (--porcelain):",
                fg="bright_red"
            )
            print(status.rstrip())
            raise SystemExit(2)

        # Not dirty -> propagate original error
        raise


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

    llvm_bld = BUILD_DIR / "llvm"
    sa_bld = BUILD_DIR / "sa"

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

    llvm_bld = BUILD_DIR / "llvm"
    sa_bld = BUILD_DIR / "sa"

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
    Copy the contents of '<BUILD_DIR>/sa/sys-windows-x86_64' into:
      - '<EMBEETLE_REPO>/sys'
      - '<BUILD_DIR>/embeetle/sys'

    Behavior:
      - Overlay-copy everything (overwrite existing, do NOT delete extras)
      - EXCEPT: mirror the 'esa' subtree (delete extras in destination/esa)
    """
    assert BUILD_DIR is not None
    assert EMBEETLE_REPO is not None

    src_sys = BUILD_DIR / "sa/sys-windows-x86_64"
    dst_sys = EMBEETLE_REPO / "sys"
    dst2_sys = BUILD_DIR / "embeetle/sys"

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


def build_embeetle() -> None:
    """
    Build Embeetle
    """
    assert MSYS2_HOME is not None
    assert EMBEETLE_REPO is not None
    assert BUILD_DIR is not None

    embeetle_bld = BUILD_DIR / "embeetle"
    venv_dir = BUILD_DIR / "embeetle_venv"

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
            str(BUILD_DIR / "embeetle").replace("\\", "/"),
        ],
        cwd=EMBEETLE_REPO,
        check=True,
    )
    return


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
            repo_url="https://github.com/Embeetle/sys-windows-x86_64.git",
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
        print(f"\nEmbeetle built at '{BUILD_DIR / 'embeetle'}'")
    
    # DO NOTHING
    # ==========
    if not (
        args.clone or
        args.install_packages or
        args.build_llvm or
        args.build_sa or
        args.install_sa or
        args.build_embeetle or
        args.all
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