#!/usr/bin/env python3
"""
change_log.py — version bumper for Monika.

Reads the current version from docs/change_log.md, bumps it, and prepends a
new section populated from git log (or a supplied --message). Intended to be
run right before `git push`:

    python change_log.py                  # patch bump
    python change_log.py --bump minor
    python change_log.py --bump major
    python change_log.py --message "Ship the new reporting module"
    python change_log.py --dry-run        # show what would change
    python change_log.py --tag            # also create a git tag v{version}

Version format: `x.y.z (YYYY-MM-DD)`.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHANGELOG = ROOT / "docs" / "change_log.md"

VERSION_LINE_RE = re.compile(
    r"^##\s*v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\s*\((?P<date>\d{4}-\d{2}-\d{2})\)",
    re.MULTILINE,
)


class Version:
    def __init__(self, major: int, minor: int, patch: int):
        self.major, self.minor, self.patch = major, minor, patch

    def bump(self, part: str) -> "Version":
        if part == "major":
            return Version(self.major + 1, 0, 0)
        if part == "minor":
            return Version(self.major, self.minor + 1, 0)
        if part == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise ValueError(f"Unknown bump part: {part}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def read_current_version() -> tuple[Version, str]:
    if not CHANGELOG.exists():
        return Version(0, 0, 0), ""
    content = CHANGELOG.read_text()
    m = VERSION_LINE_RE.search(content)
    if not m:
        return Version(0, 0, 0), content
    return (
        Version(int(m["major"]), int(m["minor"]), int(m["patch"])),
        content,
    )


def collect_commit_messages_since_tag(tag: str | None) -> list[str]:
    """Return `git log` subjects newer than the last version tag."""
    ref = f"{tag}..HEAD" if tag else "HEAD"
    try:
        out = subprocess.run(
            ["git", "log", ref, "--pretty=format:%s", "--no-merges"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        # Tag doesn't exist yet — fall back to latest 30 commits.
        out = subprocess.run(
            ["git", "log", "-n", "30", "--pretty=format:%s", "--no-merges"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def last_version_tag(version: Version) -> str | None:
    """Return the matching `v{version}` tag if it exists in this repo."""
    tag = f"v{version}"
    try:
        subprocess.run(
            ["git", "rev-parse", tag],
            cwd=ROOT, capture_output=True, check=True,
        )
        return tag
    except subprocess.CalledProcessError:
        return None


def build_section(new_version: Version, commits: list[str], manual_message: str | None) -> str:
    today = date.today().isoformat()
    header = f"## v{new_version} ({today})\n"
    if manual_message:
        return header + "\n" + manual_message.strip() + "\n"
    if not commits:
        return header + "\n_No new commits recorded._\n"
    bullets = "\n".join(f"- {c}" for c in commits)
    return header + "\n" + bullets + "\n"


def insert_section(content: str, section: str) -> str:
    """Insert the new section directly above the first `## v` heading or at EOF."""
    m = VERSION_LINE_RE.search(content)
    if m is None:
        if not content.rstrip().endswith("---"):
            if not content.endswith("\n"):
                content += "\n"
            content += "---\n\n"
        return content + section + "\n"
    idx = m.start()
    return content[:idx] + section + "\n" + content[idx:]


def create_tag(version: Version) -> None:
    tag = f"v{version}"
    subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag}"], cwd=ROOT, check=True)
    print(f"  tagged {tag}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--bump", choices=["major", "minor", "patch"], default="patch")
    ap.add_argument("--message", default=None, help="Use this text as the section body instead of `git log`.")
    ap.add_argument("--dry-run", action="store_true", help="Print the new section without writing.")
    ap.add_argument("--tag", action="store_true", help="Also create a git tag v{version}.")
    ap.add_argument("--set", dest="explicit_version", default=None,
                    help="Set an explicit version (skips bump calculation).")
    args = ap.parse_args()

    current, content = read_current_version()

    if args.explicit_version:
        parts = args.explicit_version.strip().lstrip("v").split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            print(f"error: --set requires format x.y.z, got {args.explicit_version!r}", file=sys.stderr)
            return 2
        new = Version(int(parts[0]), int(parts[1]), int(parts[2]))
    else:
        new = current.bump(args.bump)

    tag = last_version_tag(current) if content else None
    commits = collect_commit_messages_since_tag(tag)
    section = build_section(new, commits, args.message)

    print(f"  {current}  →  {new}  ({args.bump if not args.explicit_version else 'set'})")
    print("  section preview:")
    for line in section.splitlines():
        print(f"    {line}")

    if args.dry_run:
        print("\n  dry-run: no file written.")
        return 0

    if not content:
        content = "# Change Log\n\nAll notable changes to Monika are recorded here. Version format: `x.y.z (YYYY-MM-DD)`.\n\n---\n"

    new_content = insert_section(content, section)
    CHANGELOG.write_text(new_content)
    print(f"\n  wrote {CHANGELOG.relative_to(ROOT)}")

    if args.tag:
        create_tag(new)

    return 0


if __name__ == "__main__":
    sys.exit(main())
