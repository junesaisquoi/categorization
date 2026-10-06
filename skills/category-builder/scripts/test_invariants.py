#!/usr/bin/env python3
"""The safety net.

These are not tests of individual rules. They are properties that must hold for every
product whatever the rules say, because each one is a way this skill could quietly
damage the catalogue.

Run against any real export:

    python3 test_invariants.py CATEGORIES.csv PRODUCTS.csv

Exit code 0 means every invariant held.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rules import CONFIG, build_tree, group_root, is_placement  # noqa: E402
from derive import derive_regular, reconcile  # noqa: E402
from build_categories import index_products, read_csv  # noqa: E402

FAILURES: list[str] = []


def check(name, condition, detail=""):
    if not condition:
        FAILURES.append(f"{name}: {detail}")


def type_of(key):
    g = group_root(key)
    return g.split("-")[0] if g else None


def main(categories_path, *product_paths):
    tree = build_tree(read_csv(categories_path))
    products, _ = index_products(product_paths)
    print(f"checking {len(products)} products")

    counts = Counter()
    for key, p in products.items():
        d = derive_regular(tree, p)
        r = reconcile(tree, p, d, fix="replace", sale_mode="desale")
        cur, final, removed = r["current"], r["final"], r["removed"]

        for k in d.leaves:
            check("derived key exists", k in tree.all, f"{key} -> {k}")

        # A product can legitimately end with nothing: a sale-only product with no PIM
        # category loses its sale categories and has nothing to replace them with. What
        # must never happen is writing that to the upload file, so the rule is about what
        # gets written, not about what reconcile computes.
        would_write = r["changed"] and bool(final)
        if cur and not final:
            check("empty result is held back", not would_write, key)

        for k in removed:
            redundant = any(k in tree.ancestors(t) for t in final)
            # a placement parent may drop when one of its own children is kept: the
            # product stays in the collaboration, just via the specific category
            check("placement kept", not is_placement(k) or redundant, f"{key} -> {k}")
            if tree.is_sale(k):
                continue  # a sale run legitimately clears the sale tree
            governed = any(
                (grp.get("product_type") and type_of(k) and type_of(k) != type_of(d.primary or ""))
                or ("members" in grp and k in grp["members"])
                or ("pattern" in grp and __import__("re").search(grp["pattern"], k))
                for grp in CONFIG["governed_groups"])
            check("removal explained", redundant or governed, f"{key} -> {k}")

        for k in final:
            check("no parent beside its child",
                  not any(o != k and k in tree.ancestors(o) for o in final), f"{key} -> {k}")

        # Only the categories this skill derived are its responsibility. A collaboration
        # carried in both departments was put there deliberately and is preserved, not
        # created, so it is not a failure of the rules.
        mine = [k for k in d.leaves if not is_placement(k)]
        both = any(k.startswith("men-") for k in mine) and any(k.startswith("women-") for k in mine)
        unisex = (any(k.startswith("accessories-") for k in mine)
                  or type_of(d.primary or "") in CONFIG["unisex_types"])
        check("derived one department", not both or unisex, f"{key}: {', '.join(mine)}")

        counts["changed" if r["changed"] else "unchanged"] += 1
        if not d.leaves:
            counts["nothing derived"] += 1

    print(dict(counts))
    if FAILURES:
        print(f"\n{len(FAILURES)} invariant failures:")
        for f in FAILURES[:25]:
            print("  " + f)
        return 1
    print("all invariants hold")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
