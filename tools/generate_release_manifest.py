from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_PARTS = {"__pycache__", ".git"}


def iter_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_PARTS for part in path.parts):
            continue
        yield path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    lines = [
        "# RELEASE MANIFEST",
        "",
        "Generated file inventory with SHA-256 checksums.",
        "",
        "| Path | Size | SHA-256 |",
        "|---|---:|---|",
    ]

    count = 0
    total = 0
    for path in iter_files():
        rel = path.relative_to(ROOT).as_posix()
        size = path.stat().st_size
        total += size
        count += 1
        lines.append(f"| `{rel}` | {size} | `{sha256(path)}` |")

    lines.extend([
        "",
        f"Total files: {count}",
        f"Total bytes: {total}",
        "",
    ])

    (ROOT / "RELEASE_MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated RELEASE_MANIFEST.md for {count} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
