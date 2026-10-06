#!/usr/bin/env python3
"""Collapse a Commercetools-style variant-row export to one row per product.

The export pattern supported here uses a non-empty `key` on the first row of a
product and blank `key` values on subsequent variant rows. Product-level values
are taken from the first non-empty value encountered in the product block.
The output contains all original columns and keeps the first valid variants.key.
"""

import csv
import sys
from pathlib import Path


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def normalize(input_path: Path, output_path: Path) -> tuple[int, int]:
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            die("Input CSV has no header.")
        fieldnames = list(reader.fieldnames)
        if "key" not in fieldnames:
            die("Input CSV is missing required column: key")
        if "variants.key" not in fieldnames:
            die("Input CSV is missing required column: variants.key")

        products = []
        current = None
        source_rows = 0

        for raw in reader:
            source_rows += 1
            key = (raw.get("key") or "").strip()
            if key:
                if current is not None:
                    products.append(current)
                current = {name: (raw.get(name) or "") for name in fieldnames}
                current["key"] = key
            else:
                if current is None:
                    # Ignore leading blank/variant-only rows because they cannot be
                    # associated safely with a product.
                    continue
                # Fill missing product-level values only. Preserve the first value.
                for name in fieldnames:
                    value = raw.get(name) or ""
                    if not current.get(name) and value:
                        current[name] = value

            # `variants.key` must remain the first valid variant key in the block.
            if current is not None and not current.get("variants.key"):
                vkey = (raw.get("variants.key") or "").strip()
                if vkey:
                    current["variants.key"] = vkey

        if current is not None:
            products.append(current)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(products)

    return source_rows, len(products)


def main() -> None:
    if len(sys.argv) != 3:
        die("Usage: normalize_catalog.py INPUT.csv OUTPUT.csv")
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    if not input_path.exists():
        die(f"Input file not found: {input_path}")
    rows, products = normalize(input_path, output_path)
    print(f"Normalized {rows} source rows to {products} products: {output_path}")


if __name__ == "__main__":
    main()
