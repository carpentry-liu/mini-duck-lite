#!/usr/bin/env python3
"""Verify every versioned payload in this training release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    for item in manifest["payload"]:
        path = ROOT / item["path"]
        if not path.is_file():
            failures.append(f"missing: {item['path']}")
            continue
        actual_size = path.stat().st_size
        if actual_size != item["bytes"]:
            failures.append(
                f"size: {item['path']} expected={item['bytes']} actual={actual_size}"
            )
        actual_hash = sha256(path)
        if actual_hash != item["sha256"]:
            failures.append(
                f"sha256: {item['path']} expected={item['sha256']} actual={actual_hash}"
            )

    if failures:
        print("Release verification FAILED")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print(f"Release verification passed: {len(manifest['payload'])} payload files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
