#!/usr/bin/env python3
"""Validate selected product keys and build campaign review + Commercetools import CSVs.

Usage:
  python build_import.py SOURCE.csv selection.json OUTPUT.csv [CONTEXT.json]

Review output columns:
  key,product_name,variants.key,categories,date_sort_rank,date_sort_action,
  attributes.firstPublishedDate,attributes.new_arrivals_date

Direct CT import output is written beside it as <OUTPUT_STEM>_CT_Import.csv with:
  key,variants.key,categories,attributes.firstPublishedDate,attributes.new_arrivals_date

Both outputs contain one row per product key. When a product is selected for
multiple destinations, its categories are joined with semicolons so
Commercetools updates the product only once.

selection.json supports:
{
  "campaign_live_date": "2026-09-26",
  "date_sort_mode": "hero_only",
  "selections": [
    {
      "category": "men-featured-21",
      "keys": ["..."],
      "must_include": ["..."],
      "hero_keys": ["..."],
      "date_priority_keys": ["..."]
    }
  ]
}

Allowed date_sort_mode values:
- hero_only
- hero_and_priority
- none

For override items, both date attributes receive the same generated YYYY-MM-DD value,
starting at campaign_live_date and decrementing by one calendar day per ranked item.
All other selected products preserve the exact exported date values.
"""

import csv
import json
import sys
import zipfile
from collections import OrderedDict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

DATE_FIRST = "attributes.firstPublishedDate"
DATE_NEW = "attributes.new_arrivals_date"
VALID_DATE_MODES = {"hero_only", "hero_and_priority", "none"}


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def pick_product_name(row: dict) -> str:
    for field in (
        "product_name",
        "name.en",
        "attributes.productTitle.en",
        "attributes.item_name_userfriendly.en",
        "attributes.description_long_navision.en",
    ):
        value = (row.get(field) or "").strip()
        if value:
            return value
    return ""


def load_catalog(path: Path) -> OrderedDict:
    """Return product key -> product-level data plus ordered unique variants.key values."""
    catalog = OrderedDict()
    current_key = None

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            die("Source CSV has no header.")
        for required in ("key", "variants.key", DATE_FIRST, DATE_NEW):
            if required not in reader.fieldnames:
                die(f"Source CSV is missing required column: {required}")

        for row in reader:
            key = (row.get("key") or "").strip()
            if key:
                current_key = key
                catalog.setdefault(
                    current_key,
                    {
                        "variants": [],
                        "product_name": "",
                        DATE_FIRST: row.get(DATE_FIRST, ""),
                        DATE_NEW: row.get(DATE_NEW, ""),
                    },
                )
                if not catalog[current_key]["product_name"]:
                    catalog[current_key]["product_name"] = pick_product_name(row)
            elif current_key is None:
                continue

            item = catalog[current_key]
            if not item["product_name"]:
                item["product_name"] = pick_product_name(row)
            # Preserve the first non-empty product-level value if the first product row was blank.
            if not item.get(DATE_FIRST) and row.get(DATE_FIRST):
                item[DATE_FIRST] = row.get(DATE_FIRST, "")
            if not item.get(DATE_NEW) and row.get(DATE_NEW):
                item[DATE_NEW] = row.get(DATE_NEW, "")

            vkey = (row.get("variants.key") or "").strip()
            if vkey and vkey not in item["variants"]:
                item["variants"].append(vkey)

    return catalog


def load_json(path: Path, label: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        die(f"Could not read {label}: {exc}")


def load_plan(path: Path) -> dict:
    data = load_json(path, "selection JSON")
    selections = data.get("selections") if isinstance(data, dict) else None
    if not isinstance(selections, list) or not selections:
        die("selection.json must contain a non-empty 'selections' array.")
    return data


def audience_for_category(category: str) -> Optional[str]:
    c = category.lower()
    if c.startswith("men-"):
        return "men"
    if c.startswith("women-"):
        return "women"
    return None


def import_output_path(review_path: Path) -> Path:
    suffix = review_path.suffix or ".csv"
    return review_path.with_name(f"{review_path.stem}_CT_Import{suffix}")


def import_zip_path(import_path: Path) -> Path:
    return import_path.with_name(f"{import_path.stem}_UPLOAD.zip")


def audience_check_output_path(review_path: Path) -> Path:
    suffix = review_path.suffix or ".csv"
    return review_path.with_name(f"{review_path.stem}_Audience_Check{suffix}")


def parse_iso_date(value: str, label: str) -> date:
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        die(f"{label} must use YYYY-MM-DD format; got {text!r}")


def try_parse_iso_date(value: str):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def ordered_unique(values) -> list[str]:
    result = []
    seen = set()
    for raw in values or []:
        key = str(raw).strip()
        if key and key not in seen:
            seen.add(key)
            result.append(key)
    return result


def consolidate_product_rows(rows: list[dict]) -> list[dict]:
    """Return one row per product, joining destination categories in plan order."""
    consolidated = OrderedDict()
    for row in rows:
        key = row["key"]
        if key not in consolidated:
            consolidated[key] = dict(row)
            continue

        existing = consolidated[key]
        if existing["variants.key"] != row["variants.key"]:
            die(f"Product {key} resolved to conflicting variant keys across selections.")
        if (existing[DATE_FIRST], existing[DATE_NEW]) != (row[DATE_FIRST], row[DATE_NEW]):
            die(f"Product {key} resolved to conflicting date values across selections.")

        categories = ordered_unique(
            str(existing["categories"]).split(";") + str(row["categories"]).split(";")
        )
        existing["categories"] = ";".join(categories)

        ranks = ordered_unique(
            str(existing["date_sort_rank"]).split(";") + str(row["date_sort_rank"]).split(";")
        )
        existing["date_sort_rank"] = ";".join(ranks)
        if row["date_sort_action"] == "override":
            existing["date_sort_action"] = "override"

    return list(consolidated.values())


def main() -> None:
    if len(sys.argv) not in (4, 5):
        die("Usage: build_import.py SOURCE.csv selection.json OUTPUT.csv [CONTEXT.json]")

    source_path = Path(sys.argv[1])
    plan_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    context_path = Path(sys.argv[4]) if len(sys.argv) == 5 else None

    for path, label in ((source_path, "Source CSV"), (plan_path, "Selection JSON")):
        if not path.exists():
            die(f"{label} not found: {path}")
    if context_path and not context_path.exists():
        die(f"Context JSON not found: {context_path}")

    catalog = load_catalog(source_path)
    plan_data = load_plan(plan_path)
    plan = plan_data["selections"]
    context = load_json(context_path, "context JSON") if context_path else None
    if context is not None and not isinstance(context, dict):
        die("context JSON must contain an object.")

    global_mode = str(plan_data.get("date_sort_mode") or "hero_only").strip().lower()
    if global_mode not in VALID_DATE_MODES:
        die(f"date_sort_mode must be one of {sorted(VALID_DATE_MODES)}; got {global_mode!r}")

    global_live_raw = str(plan_data.get("campaign_live_date") or "").strip()
    global_live = None
    if global_mode != "none":
        if not global_live_raw:
            die("campaign_live_date is required when date_sort_mode is not 'none'.")
        global_live = parse_iso_date(global_live_raw, "campaign_live_date")

    sale_keys = set()
    recent_two = {"men": set(), "women": set()}
    delivery_keys = set()
    online_keys = set()
    regular_audience_categories = {"men": {}, "women": {}}
    audience_validation_available = False
    has_delivery_pool = False
    destination_keys = set()
    if context:
        destination_keys = set(context.get("destinations") or [])
        hard = context.get("hard_exclusions") or {}
        sale_keys = set(hard.get("sale_keys") or [])
        recent_raw = hard.get("recent_two_keys") or {}
        for aud in ("men", "women"):
            recent_two[aud] = set(recent_raw.get(aud) or [])
        priority = context.get("priority") or {}
        delivery_keys = set(priority.get("delivery_list_keys") or [])
        has_delivery_pool = bool(delivery_keys)
        eligibility = context.get("eligibility") or {}
        online_keys = set(eligibility.get("online_now_keys") or [])
        regular_raw = eligibility.get("regular_audience_categories")
        if isinstance(regular_raw, dict):
            audience_validation_available = True
            for aud in ("men", "women"):
                mapping = regular_raw.get(aud) or {}
                if isinstance(mapping, dict):
                    regular_audience_categories[aud] = {
                        str(key): ordered_unique(values if isinstance(values, list) else [])
                        for key, values in mapping.items()
                    }

    rows = []
    audience_rows = []
    errors = []
    summary = []
    warnings = []
    if not audience_validation_available:
        warnings.append(
            "Audience assignment validation was not available in reduced-check or legacy-context mode; "
            "review every row in the Audience Check sheet."
        )
    product_override_dates = {}
    product_effective_dates = {}
    seen_categories = set()

    for idx, selection in enumerate(plan, start=1):
        if not isinstance(selection, dict):
            errors.append(f"Selection {idx} must be an object.")
            continue

        category = str(selection.get("category") or "").strip()
        keys = selection.get("keys")
        must_include = selection.get("must_include", [])

        if not category:
            errors.append(f"Selection {idx} has no category.")
            continue
        if category in seen_categories:
            errors.append(f"Duplicate destination category: {category}")
        seen_categories.add(category)
        if destination_keys and category not in destination_keys:
            errors.append(f"{category}: destination is not present in the prepared candidate context.")
        if not isinstance(keys, list) or not keys:
            errors.append(f"Selection {idx} ({category}) has no product keys.")
            continue
        if not isinstance(must_include, list):
            errors.append(f"Selection {idx} ({category}) must_include must be an array.")
            continue

        selected = ordered_unique(keys)
        seen = set(selected)
        must_ordered = ordered_unique(must_include)
        must_set = set(must_ordered)

        raw_hero_keys = selection.get("hero_keys", [])
        raw_priority_keys = selection.get("date_priority_keys", [])
        if not isinstance(raw_hero_keys, list):
            errors.append(f"{category}: hero_keys must be an array.")
            raw_hero_keys = []
        if not isinstance(raw_priority_keys, list):
            errors.append(f"{category}: date_priority_keys must be an array.")
            raw_priority_keys = []

        hero_keys = ordered_unique(raw_hero_keys)
        if not hero_keys:
            hero_keys = list(must_ordered)
        hero_set = set(hero_keys)
        priority_keys = ordered_unique(raw_priority_keys)
        priority_set = set(priority_keys)
        explicit_campaign_keys = hero_set | must_set

        missing = [key for key in selected if key not in catalog]
        missing_variants = [key for key in selected if key in catalog and not catalog[key]["variants"]]
        missing_must = [key for key in must_ordered if key not in seen]

        if missing:
            errors.append(f"{category}: unknown product keys: {', '.join(missing)}")
        if missing_variants:
            errors.append(f"{category}: no variants.key found for: {', '.join(missing_variants)}")
        if missing_must:
            errors.append(f"{category}: missing must-include keys from selection: {', '.join(missing_must)}")

        target_min = selection.get("target_min", plan_data.get("target_min", 48))
        target_max = selection.get("target_max", plan_data.get("target_max", 48))
        if not isinstance(target_min, int) or not isinstance(target_max, int) or target_min < 1 or target_max < target_min:
            errors.append(f"{category}: target_min/target_max must be positive integers with target_min <= target_max.")
        elif not target_min <= len(selected) <= target_max:
            warnings.append(
                f"{category}: selection has {len(selected)} products; target range is {target_min}-{target_max}."
            )

        if context:
            sale_hits = [key for key in selected if key in sale_keys]
            if sale_hits:
                errors.append(f"{category}: sale hard-no products selected: {', '.join(sale_hits)}")

            audience = audience_for_category(category)
            if audience:
                recent_hits = [key for key in selected if key in recent_two[audience]]
                if recent_hits:
                    errors.append(
                        f"{category}: products from the two most recent prior {audience} featured campaigns selected: "
                        + ", ".join(recent_hits)
                    )

            offline_hits = [key for key in selected if key not in online_keys]
            if offline_hits:
                errors.append(f"{category}: products not in the current-online pool: {', '.join(offline_hits)}")

            pool_invalid = []
            for key in selected:
                if key in delivery_keys or key in online_keys:
                    continue
                pool_invalid.append(key)
            if pool_invalid:
                pool_label = "delivery priority or current-online pool" if has_delivery_pool else "current-online pool"
                errors.append(f"{category}: products outside the {pool_label}: {', '.join(pool_invalid)}")

        audience = audience_for_category(category)
        if audience:
            other_audience = "women" if audience == "men" else "men"
            review_required = []
            blocking_mismatches = []
            for key in selected:
                if key in hero_set:
                    role = "hero"
                elif key in must_set:
                    role = "must_include"
                elif key in priority_set:
                    role = "date_priority"
                else:
                    role = "curated"

                destination_evidence = regular_audience_categories[audience].get(key, [])
                other_evidence = regular_audience_categories[other_audience].get(key, [])
                if not audience_validation_available:
                    verdict = "NOT_CHECKED_REDUCED"
                    human_check = "Verify the product has a regular destination-audience category before upload."
                elif destination_evidence:
                    verdict = "PASS"
                    human_check = ""
                elif key in explicit_campaign_keys:
                    verdict = "REVIEW_REQUIRED"
                    human_check = "Confirm this explicit cross-audience hero or must-include is intentional before upload."
                    review_required.append(key)
                else:
                    verdict = "BLOCK"
                    human_check = "Replace or recategorize this auto-selected product before rebuilding."
                    blocking_mismatches.append(key)

                audience_rows.append({
                    "destination": category,
                    "key": key,
                    "product_name": catalog.get(key, {}).get("product_name", "") or key,
                    "selection_role": role,
                    "audience_check": verdict,
                    "regular_destination_categories": ";".join(destination_evidence),
                    "regular_other_audience_categories": ";".join(other_evidence),
                    "human_check": human_check,
                })

            if blocking_mismatches:
                errors.append(
                    f"{category}: auto-selected products lack a regular {audience.title()} category "
                    f"(featured history does not count): {', '.join(blocking_mismatches)}"
                )
            if review_required:
                warnings.append(
                    f"{category}: {len(review_required)} explicit hero/must-include product(s) lack a regular "
                    f"{audience.title()} category and require human confirmation in the Audience Check sheet: "
                    + ", ".join(review_required)
                )
        else:
            warnings.append(f"{category}: destination audience could not be inferred; audience validation was not run.")

        mode = str(selection.get("date_sort_mode") or global_mode).strip().lower()
        if mode not in VALID_DATE_MODES:
            errors.append(f"{category}: invalid date_sort_mode {mode!r}")
            mode = "none"

        live_raw = str(selection.get("campaign_live_date") or global_live_raw).strip()
        live_date = None
        if mode != "none":
            if not live_raw:
                errors.append(f"{category}: campaign_live_date is required for date_sort_mode={mode}")
            else:
                try:
                    live_date = datetime.strptime(live_raw, "%Y-%m-%d").date()
                except ValueError:
                    errors.append(f"{category}: campaign_live_date must be YYYY-MM-DD; got {live_raw!r}")

        override_order = []
        if mode in {"hero_only", "hero_and_priority"}:
            override_order.extend(hero_keys)
        if mode == "hero_and_priority":
            for key in priority_keys:
                if key not in override_order:
                    override_order.append(key)

        missing_override = [key for key in override_order if key not in seen]
        if missing_override:
            errors.append(
                f"{category}: date-ranked keys must also be present in selection keys: {', '.join(missing_override)}"
            )

        override_info = {}
        if live_date:
            for rank, key in enumerate(override_order, start=1):
                assigned = (live_date - timedelta(days=rank - 1)).isoformat()
                if key in product_override_dates and product_override_dates[key] != assigned:
                    errors.append(
                        f"{category}: product {key} would receive conflicting product-level date overrides "
                        f"({product_override_dates[key]} vs {assigned}) across selections"
                    )
                else:
                    product_override_dates[key] = assigned
                override_info[key] = {"rank": rank, "date": assigned}

        # Warn if preserved source dates may interleave with the ranked block.
        if override_info:
            lowest_assigned = min(parse_iso_date(v["date"], "assigned date") for v in override_info.values())
            interleaving = []
            for key in selected:
                if key in override_info or key not in catalog:
                    continue
                source_dates = [
                    try_parse_iso_date(catalog[key].get(DATE_FIRST, "")),
                    try_parse_iso_date(catalog[key].get(DATE_NEW, "")),
                ]
                if any(d is not None and d >= lowest_assigned for d in source_dates):
                    interleaving.append(key)
            if interleaving:
                warnings.append(
                    f"{category}: {len(interleaving)} preserved product(s) have source date(s) on/after "
                    f"{lowest_assigned.isoformat()} and may interleave with the intended ranked block: "
                    + ", ".join(interleaving[:12])
                    + (" ..." if len(interleaving) > 12 else "")
                )

        for key in selected:
            if key not in catalog or not catalog[key]["variants"]:
                continue
            info = override_info.get(key)
            if info:
                first_date = info["date"]
                new_date = info["date"]
                rank_value = str(info["rank"])
                action = "override"
            else:
                first_date = catalog[key].get(DATE_FIRST, "")
                new_date = catalog[key].get(DATE_NEW, "")
                rank_value = ""
                action = "preserve"

            effective_dates = (first_date, new_date)
            previous_dates = product_effective_dates.get(key)
            if previous_dates is not None and previous_dates != effective_dates:
                errors.append(
                    f"{category}: product {key} would receive conflicting product-level date values "
                    f"{previous_dates} vs {effective_dates} across selections"
                )
            else:
                product_effective_dates[key] = effective_dates

            rows.append({
                "key": key,
                "product_name": catalog[key]["product_name"] or key,
                "variants.key": catalog[key]["variants"][0],
                "categories": category,
                "date_sort_rank": rank_value,
                "date_sort_action": action,
                DATE_FIRST: first_date,
                DATE_NEW: new_date,
            })

        priority_count = sum(1 for key in selected if key in delivery_keys) if context else 0
        online_fallback_count = sum(1 for key in selected if key in online_keys and key not in delivery_keys) if context else 0
        summary.append((category, len(selected), len(override_info), priority_count, online_fallback_count, mode))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)

    for key, (first_date, new_date) in product_effective_dates.items():
        for field, value in ((DATE_FIRST, first_date), (DATE_NEW, new_date)):
            text = str(value or "").strip()
            if text and try_parse_iso_date(text) is None:
                errors.append(
                    f"Product {key}: {field} must be blank or use YYYY-MM-DD format; got {text!r}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)

    pair_seen = set()
    for row in rows:
        pair = (row["key"], row["categories"])
        if pair in pair_seen:
            die(f"Duplicate product/category pair generated: {pair[0]} / {pair[1]}")
        pair_seen.add(pair)

    consolidated_rows = consolidate_product_rows(rows)
    if len({row["key"] for row in consolidated_rows}) != len(consolidated_rows):
        die("Consolidation failed to produce one row per product key.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    review_fields = [
        "key",
        "product_name",
        "variants.key",
        "categories",
        "date_sort_rank",
        "date_sort_action",
        DATE_FIRST,
        DATE_NEW,
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=review_fields)
        writer.writeheader()
        writer.writerows(consolidated_rows)

    audience_path = audience_check_output_path(output_path)
    audience_fields = [
        "destination",
        "key",
        "product_name",
        "selection_role",
        "audience_check",
        "regular_destination_categories",
        "regular_other_audience_categories",
        "human_check",
    ]
    verdict_order = {"REVIEW_REQUIRED": 0, "NOT_CHECKED_REDUCED": 1, "PASS": 2}
    audience_rows.sort(
        key=lambda row: (verdict_order.get(row["audience_check"], 9), row["destination"], row["key"])
    )
    with audience_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=audience_fields)
        writer.writeheader()
        writer.writerows(audience_rows)

    ct_path = import_output_path(output_path)
    ct_fields = ["key", "variants.key", "categories", DATE_FIRST, DATE_NEW]
    with ct_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ct_fields)
        writer.writeheader()
        for row in consolidated_rows:
            writer.writerow({field: row[field] for field in ct_fields})

    zip_path = import_zip_path(ct_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(ct_path, arcname=ct_path.name)

    shared_count = len(rows) - len(consolidated_rows)
    print(f"Wrote {len(consolidated_rows)} review rows: {output_path}")
    print(f"Wrote audience review rows: {audience_path}")
    print(f"Wrote direct CT import file: {ct_path}")
    print(f"Wrote sealed CT upload package: {zip_path}")
    for category, count, override_count, priority_count, online_fallback_count, mode in summary:
        details = f"{override_count} date override(s), mode={mode}"
        if context:
            details += f", {priority_count} delivery-priority, {online_fallback_count} online fallback"
        print(f"- {category}: {count} products ({details})")
    print("Validation passed: keys exist, variant keys belong to products, must-includes are present, and the direct import contains one row per product key.")
    if shared_count:
        print(f"Shared-product handling passed: consolidated {shared_count} repeated selection row(s) into semicolon-separated destination categories.")
    print("Date handling passed: every populated output date uses YYYY-MM-DD; ranked items use sequential campaign dates; every unranked selected item preserves its exported date values.")
    audience_counts = {
        verdict: sum(1 for row in audience_rows if row["audience_check"] == verdict)
        for verdict in ("PASS", "REVIEW_REQUIRED", "NOT_CHECKED_REDUCED")
    }
    print(
        "Audience validation: "
        f"{audience_counts['PASS']} pass, {audience_counts['REVIEW_REQUIRED']} require human review, "
        f"{audience_counts['NOT_CHECKED_REDUCED']} not checked in reduced mode."
    )
    print("Handoff: review the Audience Check worksheet in the Excel-safe workbook before upload. Then extract the ZIP and upload its CSV without opening or resaving it in spreadsheet software.")
    if context:
        print("Campaign rules passed: no Sale items, no recent-two featured repeats, auto-selected products match the destination audience, and products are in the allowed candidate pool.")
    for warning in warnings:
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    main()
