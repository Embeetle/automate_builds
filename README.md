# Embeetle Build Automation

This repository contains a build automation script (one for Windows, one for Linux) to build Embeetle and all its components:

- [**Embeetle**](https://github.com/Embeetle/embeetle) — IDE for developing embedded C/C++ projects
- [**LLVM**](https://github.com/Embeetle/llvm) — compiler infrastructure used by Embeetle
- [**SA**](https://github.com/Embeetle/sa) — Source code Analyzer, whose output is bundled into Embeetle

The build automation script goes through the entire pipeline:
- clone the repos `embeetle`, `llvm` and `sa`
- build them
- merge the result in `~/bld/`

---

## Repository layout

```
automate_builds/
├── windows-x86_64/
│   └── automate_builds.py
└── linux-x86_64/
    ├── automate_builds.py
    └── Dockerfile
```

---

## WINDOWS

> For a complete description, please run `python automate_builds.py --help` in the `windows-x86_64` folder. Below is just a concise overview.

### Prerequisites

- **Git for Windows** — must be on `PATH` (`git --version` works in CMD)
- **Python 3.12+** — must be on `PATH` (`python --version` works in CMD)
- **MSYS2** — preferably installed at `C:/msys64`

> **Important:** Run the script from a native Windows CMD shell, not from an MSYS2
> shell. The script launches MSYS2 sub-shells automatically when needed.

### Quick start

Please note that `<MSYS2_HOME>` is used as placeholder for the `MSYS2` home folder on your system, eg. `C:/msys64/home/krist`.

**Standard build** (for anyone):

```bat
python automate_builds.py --all
```

Clones all repos, installs MSYS2 packages, and builds LLVM, SA, and Embeetle in
one go. The resulting executable lands at:

```
<MSYS2_HOME>/bld/embeetle-windows-x86_64/embeetle.exe
```

**Collaborator flow** (requires GitHub write access):

```bat
:: 1. Verify token
python automate_builds.py --check-access

:: 2. Bump version (or use --set-version x.y.z)
python automate_builds.py --inc-version

:: 3. Full build
python automate_builds.py --all

:: 4. Publish release on GitHub
python automate_builds.py --upload
```


### Output layout after `--all`

This is what you get with the default settings:

```
<MSYS2_HOME>/
  ├── bld/
  │   ├── embeetle-windows-x86_64/    ← built IDE
  │   ├── embeetle-windows-x86_64.7z  ← release archive
  │   ├── llvm/
  │   └── sa/
  ├── embeetle/
  │   └── .venv/                      ← isolated Python environment
  ├── llvm/
  └── sa/
```

You can override the paths with:

- `--msys-root`: If you didn't place `MSYS2` at `C:/msys64`, use the `--msys-root` parameter to tell the script where to find `MSYS2`

- `--embeetle-repo`: If you want another location for the `embeetle` repo

- `--llvm-repo`: If you want another location for the `llvm` repo

- `--sa-repo`: If you want another location for the `sa` repo

- `--output`: If you want another location for the build output


### Running Embeetle

**From the executable:**

Navigate to `<MSYS2_HOME>/bld/embeetle-windows-x86_64/` and launch `embeetle.exe`.

**From sources (Windows CMD):**

Open a CMD terminal. Move into the repo at `<MSYS2_HOME>/embeetle`:

```bat
cd embeetle
```

Create and activate a Python virtual environment, then install dependencies:

```bat
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

Run Embeetle:

```bat
run.cmd
```

The first time you run Embeetle, it downloads the required tools (such as the source analyzer, 7zip, ...). Wait a few minutes.

From now onwards you can simply launch `run.cmd`. It searches for a Python virtual environment in `.venv/`, activates it, then launches Embeetle.

**From sources (Windows PowerShell)**

Open a PowerShell terminal. Move into the repo at `<MSYS2_HOME>/embeetle`:

```powershell
cd embeetle
```

Create and activate a Python virtual environment, then install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

> **Note:** If you get a script execution error on the activation step, run this first:
> ```powershell
> Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

Run Embeetle:

```powershell
.\run.ps1
```

The first time you run Embeetle, it downloads the required tools (such as the source analyzer, 7zip, ...). Wait a few minutes.

From now onwards you can simply launch `run.ps1`. It searches for a Python virtual environment in `.venv/`, activates it, then launches Embeetle.



---

## LINUX

> For a complete description, please run `python automate_builds.py --help` in the `linux-x86_64` folder. Below is just a concise overview.

### Prerequisites

- **Git** — available on `PATH`
- **Python 3.12+** — available on `PATH`
- **Docker** — user must have permission to run it without `sudo`

Docker can be installed automatically on Ubuntu/Debian:

```sh
python automate_builds.py --install-docker
newgrp docker
```

Verify with: `docker ps` (should produce no permission errors).

> The script and `Dockerfile` must be in the same directory. This is automatically
> satisfied when you clone `https://github.com/Embeetle/automate_builds.git`.

### Quick start

**Standard build** (for anyone):

```sh
# Only needed once if Docker isn't installed yet:
python automate_builds.py --install-docker
newgrp docker

# Full build:
python automate_builds.py --all
```

Clones all repos, builds the Docker image, and builds `llvm`, `sa`, and `embeetle` inside
Docker in one go. The resulting executable lands at:

```
~/bld/embeetle-linux-x86_64/embeetle
```

**Collaborator flow** (requires GitHub write access):

```sh
# 1. Verify token
python automate_builds.py --check-access

# 2. Bump version (or use --set-version x.y.z)
python automate_builds.py --inc-version

# 3. Full build
python automate_builds.py --all

# 4. Publish release on GitHub
python automate_builds.py --upload
```

### Output layout after `--all`

```
~/
├── bld/
│   ├── embeetle-linux-x86_64/      ← built IDE
│   ├── embeetle-linux-x86_64.7z    ← release archive
│   ├── llvm/
│   └── sa/
├── embeetle/
├── llvm/
└── sa/
```

### Running Embeetle

**From the executable:**

Navigate to `~/bld/embeetle-linux-x86_64/` and launch the `embeetle` binary.

**From sources:**

Open a terminal. Move into the `embeetle` repository:

```bash
cd ~/embeetle
```

Create and activate a Python virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

> **Note:** If `python3 -m venv .venv` fails, install the venv package first:
> ```bash
> sudo apt install python3-venv
> ```

Make the run script executable and launch Embeetle:

```bash
chmod +x run.sh
./run.sh
```

The first time you run Embeetle, it downloads the required tools (such as the source analyzer, 7zip, ...). Wait a few minutes.

From now onwards, you can simply launch `run.sh`. It searches for a Python virtual environment in `.venv/`, activates it, then launches Embeetle.

> **Troubleshooting (Linux):** If Embeetle fails to start with an error like
> `Could not load the Qt platform plugin "xcb"`, Embeetle normally handles this
> automatically by bundling `libxcb-cursor.so.0` in its `sys/lib` directory and
> setting `LD_LIBRARY_PATH` at startup. If for some reason that mechanism doesn't
> work on your system, install the library manually as a last resort.
>
> Debian / Ubuntu / Mint:
> ```bash
> sudo apt install libxcb-cursor0
> ```
> Fedora / Red Hat:
> ```bash
> sudo dnf install xcb-util-cursor
> ```
> Arch / Manjaro:
> ```bash
> sudo pacman -S xcb-util-cursor
> ```
> openSUSE:
> ```bash
> sudo zypper install xcb-util-cursor
> ```

---

## License

Copyright © 2018-2026 Johan Cockx, Matic Kukovec & Kristof Mulier.
Licensed under the GNU General Public License v3.0 or later — see the SPDX header
in each script for details.
