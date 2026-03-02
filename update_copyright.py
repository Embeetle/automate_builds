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

"""Update copyright notices in all .py files to the new GPL-3.0 format.

Usage:
    python update_copyright.py [--dry-run]

Run from the embeetle root directory (or anywhere — it uses its own location).
Pass --dry-run to preview changes without writing any files.
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# The new copyright block (exactly as in CLAUDE.md)
# ---------------------------------------------------------------------------
NEW_COPYRIGHT = (
    "# Copyright © 2018-2026 Johan Cockx, Matic Kukovec & Kristof Mulier\n"
    "#\n"
    "# This program is free software: you can redistribute it and/or modify\n"
    "# it under the terms of the GNU General Public License as published by\n"
    "# the Free Software Foundation, either version 3 of the License, or\n"
    "# (at your option) any later version.\n"
    "#\n"
    "# This program is distributed in the hope that it will be useful,\n"
    "# but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
    "# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
    "# GNU General Public License for more details.\n"
    "#\n"
    "# You should have received a copy of the GNU General Public License\n"
    "# along with this program.  If not, see <https://www.gnu.org/licenses/>.\n"
    "\n"
    "# SPDX-License-Identifier: GPL-3.0-or-later\n"
)

# ---------------------------------------------------------------------------
# Regex: detect whether the new GPL-3.0 block is already present at the top
# ---------------------------------------------------------------------------
_NEW_RE = re.compile(
    r"^# Copyright © 2018-2026 Johan Cockx[^\n]*\n"
    r"#\n"
    r"# This program is free software",
)

# ---------------------------------------------------------------------------
# Regex: detect the old proprietary copyright block at the very top of a file
#
# Matches (in order):
#   1. "# Copyright © 2018-XXXX Johan Cockx …\n"
#   2. Zero or more additional "# …\n" comment lines
#      (covers "# SPDX-…", "#", "# All rights reserved.")
#   3. An optional blank line
#   4. An optional copyright docstring:  """ … """
#      (only consumed if the docstring content starts with "Copyright 2018-")
#   5. An optional blank line after the docstring
# ---------------------------------------------------------------------------
_OLD_RE = re.compile(
    r"^"
    r"# Copyright © 2018-\d{4} Johan Cockx[^\n]*\n"  # (1) copyright line
    r"(?:#[^\n]*\n)*"                                  # (2) more # lines
    r"\n?"                                             # (3) optional blank line
    r'(?:"""\s*Copyright 2018-\d{4}[^"]*?"""\n\n?)?', # (4+5) optional docstring
    re.DOTALL,
)


def process_file(filepath: Path, dry_run: bool) -> str:
    """Process one .py file.  Returns a short status string."""
    try:
        raw = filepath.read_bytes()
    except Exception as exc:
        return f"ERROR reading: {exc}"

    # Normalise line endings to \n
    content = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n").decode("utf-8")

    # --- Already correct? ---------------------------------------------------
    if _NEW_RE.match(content):
        return "already up-to-date"

    # --- Old proprietary block at the top? ----------------------------------
    match = _OLD_RE.match(content)
    if match:
        rest = content[match.end() :]
        # Ensure exactly one blank line separates copyright from rest
        new_content = NEW_COPYRIGHT + "\n" + rest
        action = "replaced"
    elif "Johan Cockx" not in content:
        # No copyright at all — prepend
        new_content = NEW_COPYRIGHT + "\n" + content
        action = "added"
    else:
        # "Johan Cockx" exists but old block not at the very top.
        # This is unusual; prepend the new block and flag it.
        new_content = NEW_COPYRIGHT + "\n" + content
        action = "prepended (unusual — check manually)"

    if new_content == content:
        return "no change needed"

    if not dry_run:
        try:
            filepath.write_bytes(new_content.encode("utf-8"))
        except Exception as exc:
            return f"ERROR writing: {exc}"

    return action


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    root = Path(__file__).parent
    print(f"{'[DRY RUN] ' if dry_run else ''}Processing .py files in: {root}")
    print()

    counts: dict[str, int] = {}
    for py_file in sorted(root.rglob("*.py")):
        result = process_file(py_file, dry_run)
        counts[result] = counts.get(result, 0) + 1
        if result not in ("already up-to-date", "no change needed"):
            print(f"  [{result}] {py_file.relative_to(root)}")

    print()
    print("Summary:")
    for action, count in sorted(counts.items()):
        print(f"  {action:45s} {count}")


if __name__ == "__main__":
    main()
