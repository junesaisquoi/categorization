#!/usr/bin/env python3
"""Copy the packaged campaign intake into a thread visualization directory."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    source = Path(__file__).resolve().parent.parent / "assets" / "campaign-intake.html"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    main()
