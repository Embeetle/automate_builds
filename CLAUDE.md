# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Build automation tool for three interdependent components: **Embeetle** (IDE for developing embedded C/C++ projects, the IDE itself is mostly written in Python/PyQt6), **LLVM** (compiler infrastructure), and **SA** (Source code Analyzer). Platform-specific implementations exist for Windows (MSYS2-based) and Linux (Docker-based).

## Running the Build Scripts

**Important:** On Windows, run from native CMD — NOT from the MSYS2 shell. The build script will invoke MSYS2 shells when needed.

```bash
# Windows
python windows-x86_64/automate_builds.py --help
python windows-x86_64/automate_builds.py --all

# Linux
python linux-x86_64/automate_builds.py --help
python linux-x86_64/automate_builds.py --all
```

### Common flags (both platforms)
```bash
--clone              # Clone or update all repos
--install-packages   # Install MSYS2 packages (Win) / build Docker image (Linux)
--build-llvm         # Build LLVM
--build-sa           # Build SA
--install-sa         # Install SA outputs into Embeetle
--build-embeetle     # Build Embeetle
--version 2.1.0      # Override version (default: auto-increment patch)
--all                # Run all steps
```

### Linux-only flags
```bash
--install-docker     # Install Docker (Ubuntu/Debian only)
--clean-docker       # Remove all containers and images
```

## Architecture

Both scripts follow the same pipeline, with environment differences:

```
Clone repos → Install tools → Build LLVM → Build SA → Install SA in Embeetle → Build Embeetle
```

**Windows:** Uses MSYS2 UCRT64 for compilation (`run_msys2_ucrt64()`), native CMD for orchestration.

**Linux:** Uses Docker container (based on `manylinux_2_34_x86_64`) for all compilation steps via `run_in_docker()`. After Docker operations, ownership is fixed with `chown` to restore host user permissions.

**Dependency chain:** SA's build output (`sys/`) is mirrored into Embeetle's `sys/` directory via `install_sa_sys_into_embeetle_sys()` before Embeetle is built.

**Version management:** `update_version_file()` auto-increments the patch version and writes a date-stamped `version.txt`.

## Key Design Conventions

- Scripts use **stdlib only** — no external Python dependencies.
- `run_msys2_ucrt64()` / `run_in_docker()` are the primary execution wrappers; all build commands go through one of these.
- `mirror_dir()` does one-way sync between directories with exclusion support.
- Git repos are always cloned with `core.autocrlf=false` (critical for Windows/MSYS2 line-ending compatibility).
- ANSI color output via `c()` helper and `printc()`.

## Default Paths

**Windows:**
- MSYS2 root: `C:/msys64`
- Repos: `<MSYS2_HOME>/embeetle`, `<MSYS2_HOME>/llvm`, `<MSYS2_HOME>/sa`
- Build output: `<MSYS2_HOME>/bld/`

**Linux:**
- Repos: `~/embeetle`, `~/llvm`, `~/sa`
- Build output: `~/bld/`
