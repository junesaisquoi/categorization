#!/usr/bin/env python3
"""Works out which regular categories a product should have, and which of the ones it
already has are wrong.

Two entry points:
  derive_regular(tree, product, buying_label)  -> what the product should be in
  reconcile(tree, product, derived, mode)      -> what to add, keep and remove
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rules import (CONFIG, Tree, group_root, is_placement, resolve_gender, to_leaf)


@dataclass
class Derived:
    leaves: list = field(default_factory=list)
    primary: str | None = None
    primary_source: str | None = None
    gender: str = "men"
    gender_source: str | None = None
    denim: bool = False
    flags: list = field(default_factory=list)
    notes: list = field(default_factory=list)


def _uniq(seq):
    seen, out = set(), []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def derive_regular(tree: Tree, product: dict, buying_label: str = "") -> Derived:
    d = Derived()
    name = str(product.get("name.en") or "")
    d.gender, d.gender_source = resolve_gender(tree, name, product)
    g = d.gender
    n = f" {re.sub(r'[ ]+', ' ', name.lower().strip())} "
    nflat = re.sub(r"[,\u2019']", " ", n)
    nflat = re.sub(r"\s+", " ", nflat)
    b = str(buying_label or "").lower()
    keys: list = []

    # 1. category_main, the source of truth. It can hold several values.
    cm_raw = [to_leaf(x) for x in str(product.get("attributes.category_main") or "").split(";")]
    cm_raw = [x for x in cm_raw if x]
    other = "women-" if g == "men" else "men-"
    cm_all = []
    for k in cm_raw:
        if k.startswith(other):
            d.flags.append(f"category_main also lists {k}, which is the other department — ignored")
        else:
            cm_all.append(k)
    d.primary = cm_all[0] if cm_all else None
    d.primary_source = "category_main" if d.primary else None

    # 2. fallbacks, in order, each reported so a guess is never silent
    if not d.primary:
        existing = [x.strip() for x in str(product.get("categories") or "").split(";")
                    if x.strip() and x.strip() in tree.all
                    and not tree.is_sale(x.strip()) and not is_placement(x.strip())]
        leaves = sorted(tree.strip_parents(existing), key=lambda k: -len(tree.ancestors(k)))
        if leaves:
            d.primary, d.primary_source = leaves[0], "the product category already on the product"
    if not d.primary and b.strip():
        slug = re.sub(r"[^a-z0-9]+", "-", b.strip().lower()).strip("-")
        cand = next((k for k in (f"{g}-{slug}", slug) if k in tree.all), None)
        if not cand:
            cand = next((k for k in tree.all
                         if str(tree.name.get(k, "")).lower() == b.strip().lower()
                         and k.startswith(f"{g}-") and not tree.is_sale(k)), None)
        if cand:
            d.primary, d.primary_source = cand, "buying’s category label"
    if not d.primary:
        for token, cat in CONFIG["name_fallback"].items():
            if token in n and cat in tree.all:
                d.primary, d.primary_source = cat, f'the product name ("{token}")'
                break

    if d.primary:
        keys.extend([d.primary] + cm_all[1:])
        for k in [d.primary] + cm_all[1:]:
            keys.extend(CONFIG["accessory_mirror"].get(k, []))
        if d.primary_source != "category_main":
            d.flags.append(f"category_main missing, used {d.primary_source} instead, please check")
    else:
        d.flags.append("category_main missing and no fallback worked, left empty for review")

    is_acc = bool(d.primary) and (d.primary.startswith("accessories-")
                                  or d.primary.endswith("-gadgets"))
    material = str(product.get("attributes.main_material_description.en") or "").lower()
    cur_keys = [x.strip() for x in str(product.get("categories") or "").split(";") if x.strip()]

    # 3. denim, best evidence first
    if re.search(r"non[- ]denim", b):
        d.denim = False
    elif "denim" in b:
        d.denim = True
    elif "denim" in material:
        d.denim = True
    elif any(re.search(r"(^|-)denim(-|$)", k) for k in cur_keys):
        d.denim = True

    gr = group_root(d.primary) or (b.split(" ")[0].lower() if b else None)
    if d.denim and not is_acc:
        grp = ("bib" if re.search(r"bib|overall", f"{b} {d.primary or ''}")
               else "shorts" if gr == "shorts" or b.startswith("swim")
               else "pants" if gr == "pants"
               else "shirts" if gr == "shirts" or b.startswith("shirt jacs")
               else "jackets" if gr == "jackets" else None)
        if grp:
            keys.extend(CONFIG["denim_extra"].get(g, {}).get(grp, []))

    # 4. fit
    fit_group = None
    if gr not in CONFIG["no_fit_groups"] and not is_acc:
        fit_group = {"tshirts": "tshirts", "shirts": "shirts", "pants": "pants"}.get(gr)
    if fit_group:
        raw = str(product.get("attributes.fit") or "").strip()
        toks = [t.strip().replace("attropt_fit_", "") for t in raw.split(";") if t.strip()] \
            if raw and raw.lower() != "nan" else []
        if not toks:
            d.notes.append("fit missing in PIM")
        hit = False
        for t in toks:
            k = CONFIG["fit_map"].get((g, t, fit_group))
            if k:
                keys.append(k)
                hit = True
                if d.denim and k in CONFIG["fit_denim_mirror"]:
                    keys.append(CONFIG["fit_denim_mirror"][k])
        if toks and not hit:
            d.notes.append("no category for fit: " + ", ".join(toks))

    # 5. basic vs graphic — positive evidence only, never a default bucket
    typ = str(product.get("attributes.type") or "").lower()
    cm_tee = bool(re.search(r"(^|-)tshirts(-|$)", str(d.primary or ""))) \
        and not re.search(r"polo|rugby", str(d.primary or ""))
    if typ:
        is_tee = bool(re.search(r"filter_tshirts", typ)) \
            and not re.search(r"filter_shirts|filter_jackets", typ) and cm_tee
    else:
        is_tee = cm_tee
    if is_tee and not re.search(r"polo|rugby", f"{b} {n}"):
        basic_key, graphic_key = CONFIG["tshirt_style"][g]
        pat_vals = [x.strip().replace("attropt_pattern_", "")
                    for x in str(product.get("attributes.pattern") or "").lower().split(";")
                    if x.strip()]
        pat_graphic = any(v in CONFIG["graphic_pattern_values"] for v in pat_vals)
        name_graphic = any(t in n for t in CONFIG["tshirt_graphic_tokens"])
        name_basic = any(t in n for t in CONFIG["tshirt_basic_tokens"])
        if pat_graphic:
            keys.append(graphic_key)
        elif pat_vals:
            keys.append(basic_key)          # pattern set, and not a graphic one
        elif name_basic:
            keys.append(basic_key)          # a specific style name beats a generic hint
        elif name_graphic:
            keys.append(graphic_key)
        else:
            d.notes.append("pattern not set in PIM and the name is not conclusive, "
                           "neither basic nor graphic assigned")

    # 6. what the name says versus what PIM says — reported, never acted on
    if d.primary and d.primary_source == "category_main":
        now = group_root(d.primary) or ""
        for token, expect in CONFIG["name_vs_category"].items():
            if token in n or token in nflat:
                if now and now != expect:
                    d.flags.append(f'name says "{token}" but category_main puts it in {now}, '
                                   f"it may belong in {expect}")
                break

    # 7. additive style rules, then core collections
    for token, pair in CONFIG["name_additions"].items():
        if token in n or token in nflat:
            k = pair[1] if g == "women" else pair[0]
            if k:
                keys.append(k)
            else:
                d.flags.append(f'name says "{token}" but there is no {g} category for it')
    for token, pair in CONFIG["core_products"].items():
        if token in n or token in nflat:
            if is_acc:
                keys.extend([k for k in pair if k])
            else:
                k = pair[1] if g == "women" else pair[0]
                if k:
                    keys.append(k)

    # 8. validate against the live tree, then keep only the leaves
    valid = []
    for k in _uniq(keys):
        if k not in tree.all:
            d.flags.append(f"key not in tree: {k}")
            continue
        if k not in tree.active:
            d.flags.append(f"category switched off: {k}")
        valid.append(k)
    d.leaves = tree.strip_parents(valid)
    if not d.leaves:
        d.flags.append("nothing to assign, left empty for review")
    return d


def _type_of(key):
    g = group_root(key)
    return g.split("-")[0] if g else None


def reconcile(tree: Tree, product: dict, d: Derived, fix: str = "add",
              sale_mode: str = "desale"):
    """Turn the derived categories into add / keep / remove against what is there now.

    fix:       "add"     leave existing categories alone, only add what is missing
               "replace" remove anything that contradicts PIM (governed groups only)
    sale_mode: "desale"  a product coming back from sale loses its sale categories
               "skip"    leave sale products entirely alone
               "include" keep the sale categories alongside the regular ones
    """
    cur = [x.strip() for x in str(product.get("categories") or "").split(";") if x.strip()]
    sale_on = [k for k in cur if tree.is_sale(k)]
    flags = []

    if sale_mode == "skip" and sale_on:
        return {"current": cur, "add": [], "kept": cur, "removed": [], "final": cur,
                "changed": False,
                "flags": ["currently in sale — left untouched because of the sale setting"]}

    carry = [k for k in cur if not tree.is_sale(k)] if sale_mode == "desale" else list(cur)
    if sale_mode == "desale" and sale_on:
        flags.append("came back from sale: sale categories removed, regular ones assigned")

    if fix == "replace":
        derived_type = _type_of(d.primary or (d.leaves[0] if d.leaves else "")) or None

        def allowed_with(t):
            return any(t in pair and derived_type in pair
                       for pair in CONFIG["cross_group_allowed"])

        def in_group(key, grp):
            if grp.get("product_type"):
                if not derived_type:
                    return False
                t = _type_of(key)
                return bool(t) and t != derived_type and not allowed_with(t)
            if "members" in grp:
                return key in grp["members"]
            return bool(re.search(grp["pattern"], key))

        # a group only has authority when the rules actually reached a verdict in it
        active = [grp for grp in CONFIG["governed_groups"]
                  if (bool(derived_type) if grp.get("product_type")
                      else any(in_group(l, grp) for l in d.leaves))]

        def wrong(key):
            return any(in_group(key, grp) and key not in d.leaves for grp in active)

        carry = [k for k in carry if is_placement(k) or tree.is_sale(k) or not wrong(k)]

    target = tree.strip_parents(_uniq(carry + d.leaves))
    removed = [k for k in cur if k not in target]
    kept = [k for k in cur if k in target]
    add = [k for k in target if k not in kept]

    parents_only = [k for k in removed if any(k in tree.ancestors(t) for t in target)]
    contradictions = [k for k in removed if k not in parents_only and not tree.is_sale(k)]
    for k in contradictions:
        flags.append(f"correction: removed {k}, it contradicts " + ", ".join(d.leaves))
    if parents_only:
        flags.append("removed redundant parent " + ", ".join(parents_only)
                     + ", commercetools assigns it automatically")

    return {"current": cur, "add": add, "kept": kept, "removed": removed, "final": target,
            "changed": bool(add or removed), "flags": flags}
