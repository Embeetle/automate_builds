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
- **Python 3.14+** — must be on `PATH` (`python --version` works in CMD)
- **MSYS2** — preferably installed at `C:/msys64`

> **Important:** Run the script from a native Windows CMD shell, not from an MSYS2
> shell. The script launches MSYS2 sub-shells automatically when needed.

### Quick start

Please note that `<MSYS2_HOME>` is used as placeholder for the `MSYS2` home folder on your system, eg. `C:/msys64/home/krist`.

**Standard build** (for anyone):

```cmd
> python automate_builds.py --all
```

Clones all repos, installs MSYS2 packages, and builds LLVM, SA, and Embeetle in
one go. The resulting executable lands at:

```
<MSYS2_HOME>/bld/embeetle-windows-x86_64/embeetle.exe
```

**Collaborator flow** (requires GitHub write access):

```cmd
> python automate_builds.py --check-access  # 1. verify token
> python automate_builds.py --inc-version   # 2. bump version (or use --set-version x.y.z)
> python automate_builds.py --all           # 3. full build
> python automate_builds.py --upload        # 4. publish release on GitHub
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

**From sources:**

```cmd
# Open a native(!) Windows CMD terminal and navigate to the repo:
> cd <MSYS2_HOME>/embeetle

# If a .venv subfolder doesn't exist yet, create and populate it:
> python -m venv .venv
> call .venv/Scripts/activate.bat
> python -m pip install -r requirements.txt

# Launch Embeetle:
> run.cmd
```

Next time, you can simply launch Embeetle with `run.cmd`. The script finds the python venv, activates it and then launches the IDE.

---

## LINUX

> For a complete description, please run `python automate_builds.py --help` in the `linux-x86_64` folder. Below is just a concise overview.

### Prerequisites

- **Git** — available on `PATH`
- **Python 3** — available on `PATH`
- **Docker** — user must have permission to run it without `sudo`

Docker can be installed automatically on Ubuntu/Debian:

```sh
$ python automate_builds.py --install-docker
$ newgrp docker   # or log out and back in
```

Verify with: `docker ps` (should produce no permission errors).

> The script and `Dockerfile` must be in the same directory. This is automatically
> satisfied when you clone `https://github.com/Embeetle/automate_builds.git`.

### Quick start

**Standard build** (for anyone):

```sh
# Only needed once if Docker isn't installed yet:
$ python automate_builds.py --install-docker
$ newgrp docker

# Full build:
$ python automate_builds.py --all
```

Clones all repos, builds the Docker image, and builds `llvm`, `sa`, and `embeetle` inside
Docker in one go. The resulting executable lands at:

```
~/bld/embeetle-linux-x86_64/embeetle
```

**Collaborator flow** (requires GitHub write access):

```sh
$ python automate_builds.py --check-access          # 1. verify token
$ python automate_builds.py --inc-version           # 2. bump version
$ python automate_builds.py --all                   # 3. full build
$ python automate_builds.py --upload                # 4. publish release
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

```sh
# Navigate into the embeetle repo:
$ cd ~/embeetle

# If a .venv subfolder doesn't exist yet, create and populate it:
$ python -m venv .venv
$ source .venv/bin/activate
$ python -m pip install -r requirements.txt

# Launch Embeetle:
$ chmod +x run.sh
$ ./run.sh
```

Next time, you can simply launch Embeetle with `run.sh`. The script finds the python venv, activates it and then launches the IDE.

---

## License

Copyright © 2018-2026 Johan Cockx, Matic Kukovec & Kristof Mulier.
Licensed under the GNU General Public License v3.0 or later — see the SPDX header
in each script for details.
