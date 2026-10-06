#!/usr/bin/env python3
"""Turn commercetools exports plus buying's list into category upload files.

  python3 build_categories.py CATEGORIES.csv PRODUCTS.csv [more PRODUCTS.csv ...] \
      --items SS27_Buying.xlsx --key-column X_X_X \
      --mode assign --fix add --sale desale \
      --also-add new-arrivals --new-arrivals-by 2026-11-01 \
      --out ./output

Writes into --out:
  categories.csv       key + the final category set          (upload with Categories = Replace)
  rollback.csv         the current state, same shape         (upload the same way to undo)
  review.html          grouped, expandable, open in a browser
  excluded.csv         products buying said to leave out, with the reason  (if any)

Nothing is uploaded anywhere. Every file is written locally.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rules import CONFIG, build_tree, is_placement, parse_date  # noqa: E402
from derive import derive_regular, reconcile  # noqa: E402


# --- reading ------------------------------------------------------------------
def flatten(name):
    """Header cells often contain line breaks: 'Earliest\\nDel. Date\\n(SS27)'."""
    return re.sub(r"\s+", " ", str(name or "")).strip()


def unwrap(value):
    """Some exports wrap every cell as ="value"."""
    s = str(value or "").lstrip("\ufeff").strip()
    m = re.match(r'^=\s*"(.*)"$', s, re.S)
    return m.group(1).replace('""', '"') if m else s


def iter_csv(path):
    """Stream the rows. Product exports run to hundreds of thousands of lines, so nothing
    holds the whole file in memory."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return
        wrapped = any(re.match(r'^=\s*"', str(k or "")) for k in reader.fieldnames)
        names = [flatten(unwrap(k) if wrapped else k) for k in reader.fieldnames]
        for row in reader:
            values = (row.get(k) for k in reader.fieldnames)
            yield dict(zip(names, (unwrap(v) if wrapped else v for v in values)))


def read_csv(path):
    return list(iter_csv(path))


def read_items(path):
    """Buying's list. Reads .xlsx including which rows are shaded red."""
    p = Path(path)
    if p.suffix.lower() in (".csv", ".txt"):
        return read_csv(p), 0
    try:
        from openpyxl import load_workbook
    except ImportError:
        sys.exit("Reading .xlsx needs openpyxl:  pip install openpyxl\n"
                 "Or save buying's file as CSV, which loses the red-row marking.")
    ws = load_workbook(p, data_only=True).active
    header = [flatten(c.value) for c in ws[1]]
    rows, red_count = [], 0
    for r in ws.iter_rows(min_row=2):
        if all(c.value in (None, "") for c in r):
            continue
        row = {header[i]: c.value for i, c in enumerate(r) if i < len(header)}
        red = False
        for c in r[:6]:
            rgb = getattr(getattr(c.fill, "fgColor", None), "rgb", None)
            if rgb and str(rgb).upper().endswith("FF0000"):
                red = True
                break
        if red:
            red_count += 1
        row["__row_is_red"] = red
        rows.append(row)
    return rows, red_count


KEEP_COLUMNS = ("key", "name.en", "categories", "published", "attributes.category_main",
                "attributes.type", "attributes.fit", "attributes.pattern",
                "attributes.gender_product", "attributes.gender_userfriendly",
                "attributes.main_material_description.en")


def index_products(files):
    """Merge several exports. A commercetools export repeats the key only on a product's
    first row, so carry it down before merging, then keep the first row per product."""
    by, dupes = {}, 0
    for path in files:
        last = None
        seen_here = set()
        for r in iter_csv(path):
            k = str(r.get("key") or "").strip()
            if k:
                last = k
            else:
                k = last
            if not k:
                continue
            if k in by:
                # variant rows repeat the key within one file; only count a product that
                # an earlier file already covered
                if k not in seen_here:
                    dupes += 1
                seen_here.add(k)
                continue
            seen_here.add(k)
            by[k] = {c: r.get(c, "") for c in KEEP_COLUMNS if c in r} | {"key": k}
    return by, dupes


# --- buying's instructions ----------------------------------------------------
COMMENT_PATTERNS = (r"not to be sold online", r"don.?t publish", r"do not publish",
                    r"do not categori", r"\bitem out\b", r"cancelled", r"canceled",
                    r"not produced")


def find_col(cols, pattern):
    return next((c for c in cols if re.search(pattern, c, re.I)), None)


def find_cols(cols, pattern):
    return [c for c in cols if re.search(pattern, c, re.I)]


def exclusion_reason(row, cols):
    """Why buying says this product must not go online, or None."""
    if row.get("__row_is_red"):
        return "struck out in red by buying, not being produced"
    comment_col = find_col(cols, r"comment|note|bemerk")
    if comment_col:
        text = str(row.get(comment_col) or "")
        if text and any(re.search(p, text, re.I) for p in COMMENT_PATTERNS):
            return f"buying's comment says it should not be published ({text.strip()[:60]})"
    qty_cols = find_cols(cols, r"^(ws|rt|ec)$|quantit|menge|ordered")
    if qty_cols:
        nums = []
        for c in qty_cols:
            try:
                nums.append(float(re.sub(r"[^\d.-]", "", str(row.get(c) or ""))))
            except ValueError:
                nums.append(None)
        real = [n for n in nums if n is not None]
        if real and all(n == 0 for n in real):
            return "nothing ordered on any channel, the style is out"
        ec = find_col(qty_cols, r"^ec$")
        if ec:
            try:
                q = float(re.sub(r"[^\d.-]", "", str(row.get(ec) or "")))
                if q < 2:
                    return f"only {q:g} piece ordered, a Fotostudio sample rather than a sellable product"
            except ValueError:
                pass
    return None


def is_carryover(row, cols):
    """True when buying marks the style AND the colour as a repeat."""
    cc = find_cols(cols, r"new ?/? ?repeat|repeat|carry.?over")
    vals = [str(row.get(c) or "").strip().lower() for c in cc]
    vals = [v for v in vals if v]
    return bool(vals) and all(v == "repeat" for v in vals)


# --- review page --------------------------------------------------------------
BUCKETS = {
    "onsale": ("Currently in sale",
               "Still in sale categories. Look at what they carry, then decide."),
    "excluded": ("Left out on buying's instructions",
                 "Not in any upload file. Check the reason on each row."),
    "empty": ("Nothing to assign",
              "No categories could be worked out. Held back so they cannot be emptied on site."),
    "check": ("Assigned, worth a look",
              "Categories were produced, but something in the row needs a human eye."),
    "clean": ("Ready to upload", "Derived cleanly, nothing flagged."),
    "nochange": ("No change needed", "Already correct. Not in the upload file."),
    "notyet": ("Not in the product export",
               "Usually a style that has not landed yet, or an export filtered to published products."),
}
ORDER = ["onsale", "excluded", "empty", "check", "clean", "nochange", "notyet"]


def bucket_of(row):
    if row["bucket"]:
        return row["bucket"]
    if row["changed"] and not row["final"]:
        return "empty"
    if row["flags"]:
        return "check"
    return "clean" if row["changed"] else "nochange"


def write_review(path, rows, summary):
    def esc(s):
        return html.escape(str(s or ""))

    groups = defaultdict(list)
    for r in rows:
        groups[bucket_of(r)].append(r)

    body = []
    for b in ORDER:
        rs = groups.get(b)
        if not rs:
            continue
        title, note = BUCKETS[b]
        body.append(f'<section class="grp {b}"><h2>{esc(title)} <span>{len(rs)}</span></h2>'
                    f'<p class="note">{esc(note)}</p>')
        # collapse rows that say the same thing
        pats = defaultdict(list)
        for r in rs:
            pats[(tuple(r["removed"]), tuple(r["add"]), tuple(r["flags"]))].append(r)
        for (removed, add, flags), items in sorted(pats.items(), key=lambda kv: -len(kv[1])):
            chips = "".join(f'<span class="cat rm">{esc(k)}</span>' for k in removed) + \
                    "".join(f'<span class="cat add">{esc(k)}</span>' for k in add)
            first = items[0]
            head = (f'{esc(first["key"])} <span class="nm">{esc(first["name"])}</span>'
                    if len(items) == 1 else f'{len(items)} products')
            lis = "".join(f'<div class="it"><b>{esc(i["key"])}</b> {esc(i["name"])}</div>'
                          for i in items[:40])
            more = (f'<div class="more">{len(items) - 40} more, all in categories.csv</div>'
                    if len(items) > 40 else "")
            fl = "".join(f'<div class="fl">{esc(f)}</div>' for f in flags)
            body.append(f'<details><summary><span class="n">{len(items)}</span>'
                        f'<span class="bd"><span class="chips">{chips or "<i>no change</i>"}</span>'
                        f'<span class="meta">{head}</span>{fl}</span></summary>'
                        f'<div class="items">{lis}{more}</div></details>')
        body.append("</section>")

    counts = "".join(f'<div class="c"><b>{v}</b><span>{esc(k)}</span></div>'
                     for k, v in summary.items())
    Path(path).write_text(f"""<!doctype html><meta charset="utf-8">
<title>Category review</title>
<style>
:root{{--ink:#171614;--g1:#f6f5f3;--g2:#e5e3df;--g3:#9b978f;--g4:#5d5a54;
--stop:#f2ddd8;--stopi:#8c3f2e;--hold:#f7e7cf;--holdi:#8a5a1d;--look:#f7f0cf;--looki:#7a641a;
--good:#dcebdd;--goodi:#33613c;--calm:#dde6ef;--calmi:#3a5670;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
body{{margin:0;font:14px/1.5 system-ui,-apple-system,"Segoe UI",Helvetica,sans-serif;color:var(--ink)}}
.w{{max-width:1100px;margin:0 auto;padding:0 26px 90px}}
header{{border-bottom:1px solid var(--ink);padding:32px 0 14px}}
h1{{font-size:24px;margin:0;letter-spacing:-.02em}}
.sub{{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--g4);margin-top:8px}}
.counts{{display:flex;flex-wrap:wrap;border:1px solid var(--ink);margin:26px 0}}
.c{{flex:1;min-width:110px;padding:14px 20px;border-right:1px solid var(--g2)}}
.c:last-child{{border-right:none}}
.c b{{font-family:var(--mono);font-size:24px;display:block;letter-spacing:-.03em}}
.c span{{font-family:var(--mono);font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--g4)}}
.grp h2{{font-size:14px;margin:0;display:flex;gap:9px;align-items:baseline}}
.grp h2 span{{font-family:var(--mono);font-size:12px;color:var(--g4)}}
.grp{{padding:13px 15px;margin-top:26px;background:var(--g1);border-left:3px solid var(--g3)}}
.grp .note{{font-size:12px;color:var(--g4);margin:5px 0 0;max-width:70ch}}
.onsale,.excluded{{background:var(--hold);border-left-color:var(--holdi)}}
.onsale h2,.excluded h2{{color:var(--holdi)}}
.empty{{background:var(--stop);border-left-color:var(--stopi)}} .empty h2{{color:var(--stopi)}}
.check{{background:var(--look);border-left-color:var(--looki)}} .check h2{{color:var(--looki)}}
.clean{{background:var(--good);border-left-color:var(--goodi)}} .clean h2{{color:var(--goodi)}}
.nochange,.notyet{{background:var(--calm);border-left-color:var(--calmi)}}
.nochange h2,.notyet h2{{color:var(--calmi)}}
details{{border-bottom:1px solid var(--g2)}}
summary{{display:grid;grid-template-columns:46px 1fr;gap:12px;padding:11px 4px;cursor:pointer;list-style:none}}
summary::-webkit-details-marker{{display:none}}
summary:hover{{background:var(--g1)}}
.n{{font-family:var(--mono);font-size:15px;letter-spacing:-.02em;color:var(--g4)}}
.chips{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:5px}}
.cat{{font-family:var(--mono);font-size:11px;padding:2px 8px;border:1px solid var(--g2);border-radius:2px}}
.cat.rm{{background:var(--stop);border-color:#e6c7c0;color:var(--stopi);text-decoration:line-through}}
.cat.add{{background:var(--good);border-color:#bcd6be;color:var(--goodi)}}
.meta{{font-family:var(--mono);font-size:11.5px;color:var(--g4)}}
.meta .nm{{font-family:inherit;font-size:12.5px}}
.fl{{margin-top:7px;font-size:11px;color:var(--looki);background:var(--look);
border-left:2px solid var(--looki);padding:5px 9px;border-radius:0 2px 2px 0}}
.items{{padding:2px 4px 14px 58px}}
.it{{font-size:12px;padding:3px 0;color:var(--g4)}}
.it b{{font-family:var(--mono);font-size:11.5px;color:var(--ink)}}
.more{{font-family:var(--mono);font-size:11px;color:var(--g3);padding-top:7px}}
</style>
<div class="w">
<header><h1>Category review</h1>
<div class="sub">{esc(date.today().isoformat())} &nbsp;/&nbsp; check this before uploading categories.csv</div></header>
<div class="counts">{counts}</div>
{''.join(body)}
</div>""", encoding="utf-8")


# --- main ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("categories", help="commercetools category export")
    ap.add_argument("products", nargs="+", help="one or more commercetools product exports")
    ap.add_argument("--items", help="buying's item list (.xlsx or .csv); narrows the run")
    ap.add_argument("--key-column", help="the column in the item list holding the product key")
    ap.add_argument("--fix", choices=["add", "replace"], default="add",
                    help="add: only add what is missing. replace: also remove what contradicts PIM")
    ap.add_argument("--sale", choices=["desale", "skip", "include"], default="desale",
                    help="what to do with products currently in sale categories")
    ap.add_argument("--also-add", default="",
                    help="comma separated: new-arrivals, or a category key such as men-featured-21")
    ap.add_argument("--new-arrivals-by", help="YYYY-MM-DD; only items delivering by then count")
    ap.add_argument("--out", default="./output")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tree = build_tree(read_csv(args.categories))
    products, dupes = index_products(args.products)

    published_only = None
    pub_vals = {str(r.get("published", "")).strip().lower() for r in products.values()}
    if pub_vals and pub_vals <= {"true"}:
        published_only = True

    items, red_count = ([], 0)
    item_cols = []
    if args.items:
        items, red_count = read_items(args.items)
        item_cols = [c for c in (items[0].keys() if items else []) if not c.startswith("__")]

    # which products to work on
    key_col = args.key_column
    if items and not key_col:
        best, best_rate = None, 0.0
        for c in item_cols:
            vals = [str(r.get(c) or "").strip() for r in items[:300]]
            vals = [v for v in vals if v]
            if not vals:
                continue
            rate = sum(v in products for v in vals) / len(vals)
            if rate > best_rate:
                best, best_rate = c, rate
        key_col = best
        print(f"key column: {key_col} ({best_rate:.0%} of rows match a product)")

    targets, excluded = [], []
    if items:
        name_col = find_col(item_cols, r"description|name|item") or key_col
        buy_col = find_col(item_cols, r"^category$|waregroup")
        deliv_col = find_col(item_cols, r"deliver|del\. ?date|earliest|liefer|eta")
        seen = {}
        for r in items:
            key = str(r.get(key_col) or "").strip()
            if not key:
                continue
            why = exclusion_reason(r, item_cols)
            if why:
                excluded.append({"key": key, "product": r.get(name_col, ""), "reason": why})
                continue
            if key in seen:  # one row per drop: the earliest delivery wins
                if deliv_col:
                    a, b = parse_date(seen[key].get(deliv_col)), parse_date(r.get(deliv_col))
                    if b and (not a or b < a):
                        seen[key] = r
                continue
            seen[key] = r
        for key, r in seen.items():
            targets.append({"key": key, "name": r.get(name_col, ""),
                            "buying": r.get(buy_col, "") if buy_col else "", "src": r,
                            "deliv": deliv_col})
    else:
        for key, p in products.items():
            targets.append({"key": key, "name": p.get("name.en", ""), "buying": "",
                            "src": None, "deliv": None})

    extras = [x.strip() for x in args.also_add.split(",") if x.strip()]
    cutoff = parse_date(args.new_arrivals_by) if args.new_arrivals_by else None

    rows = []
    for t in targets:
        prod = products.get(t["key"])
        if not prod:
            rows.append({"key": t["key"], "name": t["name"], "current": [], "add": [], "kept": [],
                         "removed": [], "final": [], "changed": False, "bucket": "notyet",
                         "flags": ["not in the product export" + (
                             " — it only covers published products, so this may exist but be unpublished"
                             if published_only else "")]})
            continue

        d = derive_regular(tree, prod, t["buying"])
        leaves = list(d.leaves)

        # extras: new arrivals and featured slots are chosen per run, never derived
        if extras and leaves:
            eligible, why = True, None
            if t["src"] and is_carryover(t["src"], item_cols):
                eligible, why = False, "a repeat style in a repeat colour, so not a new arrival"
            elif cutoff and t.get("deliv") and t["src"]:
                dd = parse_date(t["src"].get(t["deliv"]))
                if not dd:
                    eligible, why = False, "no readable delivery date, extras not applied"
                elif dd > cutoff:
                    eligible, why = False, f"delivers {dd.isoformat()}, after the cutoff"
            if why:
                d.notes.append(why)
            if eligible:
                is_acc = bool(d.primary) and (d.primary.startswith("accessories-")
                                              or d.primary.endswith("-gadgets"))
                for x in extras:
                    if x == "new-arrivals":
                        want = (["accessories-new", "men-new", "women-new"] if is_acc
                                else [f"{d.gender}-new"])
                        leaves += [k for k in want if k in tree.all]
                    elif x in tree.all:
                        leaves.append(x)
                    else:
                        d.flags.append(f"category to also add does not exist: {x}")
                d.leaves = tree.strip_parents(list(dict.fromkeys(leaves)))

        rec = reconcile(tree, prod, d, fix=args.fix, sale_mode=args.sale)
        bucket = "onsale" if any(f.startswith("currently in sale") for f in rec["flags"]) else None
        rows.append({"key": t["key"], "name": t["name"] or prod.get("name.en", ""),
                     "current": rec["current"], "add": rec["add"], "kept": rec["kept"],
                     "removed": rec["removed"], "final": rec["final"],
                     "changed": rec["changed"], "bucket": bucket,
                     "flags": d.flags + rec["flags"], "notes": d.notes})

    for e in excluded:
        rows.append({"key": e["key"], "name": e["product"], "current": [], "add": [], "kept": [],
                     "removed": [], "final": [], "changed": False, "bucket": "excluded",
                     "flags": [e["reason"]], "notes": []})

    # never write a product whose final set is empty: that would strip it from the site
    safe = [r for r in rows if r["changed"] and r["final"] and r["bucket"] is None]

    with open(out / "categories.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["key", "categories"])
        for r in safe:
            w.writerow([r["key"], ";".join(r["final"])])
    with open(out / "rollback.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["key", "categories"])
        for r in rows:
            if r["current"]:
                w.writerow([r["key"], ";".join(r["current"])])
    if excluded:
        with open(out / "excluded.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["key", "product", "reason"]); w.writeheader()
            w.writerows(excluded)

    summary = {"products": len(rows), "to upload": len(safe),
               "categories added": sum(len(r["add"]) for r in rows),
               "removed": sum(len(r["removed"]) for r in rows),
               "need a look": sum(1 for r in rows if r["flags"] and r["bucket"] is None)}
    if excluded:
        summary["left out by buying"] = len(excluded)
    write_review(out / "review.html", rows, summary)

    print(json.dumps({
        **summary,
        "product_exports_merged": len(args.products),
        "duplicate_products_skipped": dupes,
        "export_is_published_only": bool(published_only),
        "red_rows_in_item_list": red_count,
        "exclusion_reasons": dict(Counter(e["reason"].split(" (")[0] for e in excluded)),
        "files": [str(out / n) for n in
                  ["categories.csv", "rollback.csv", "review.html"] + (["excluded.csv"] if excluded else [])],
    }, indent=2))


if __name__ == "__main__":
    main()
