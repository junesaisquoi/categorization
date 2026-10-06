---
name: campaign-product-picker
description: Build and visually QA validated Carhartt WIP campaign product selections and date-safe Commercetools import files from product/category exports, Basecamp briefs, optional delivery lists, and storefront screenshots. Use when asked to pick campaign products, create Men/Women featured categories, curate seasonal assortments, mix eligible online products across seasons or deliveries for a stronger edit, exclude Sale or recently featured items, control temporary date-based hero ordering, prevent spreadsheet date conversion, review a live campaign grid, improve visual product mix, or generate campaign review/import files.
---

# Campaign Product Picker

## Start the campaign task

Read `references/source-intake.md` and follow its staged intake exactly.

When the campaign starts from the Web DMD launcher and the user has not supplied campaign details,
show the visual campaign intake before requesting uploads. Locate the thread-scoped
`.codex/visualizations/...` writable root from the environment context, then run:

```bash
python3 scripts/render_intake.py \
  --out <thread-visualization-root>/campaign-product-picker-intake.html
```

Respond with one short orientation sentence, the inline directive, and nothing else:

```text
Set up the campaign below; everything is optional until the source material is attached.

::codex-inline-vis{file="campaign-product-picker-intake.html"}
```

The form sends a follow-up message containing `The visual campaign form has been submitted`. On
that follow-up, do not render the form again. Preserve any submitted values, then ask only for the
three source bundles: two Commercetools CSV exports, the campaign planning material, and the
optional same-delivery list. If the user already supplied details or files directly, skip the form
and continue the staged intake. Do not dump all missing fields or setup choices at once.

After each upload, inspect the files, show a compact checkbox status, and ask only the next blocking question. Do not ask for information already present in the conversation, Basecamp material or attachments.

Require the category export for the fully validated workflow. If it is unavailable, proceed only after the user explicitly accepts a reduced-check run. Explain that Sale hierarchy and recent-two campaign exclusions cannot then be fully verified, skip candidate-context generation, and build without `CONTEXT.json`.

## Run the workflow

1. Complete the staged source intake. Read the canonical live date from the SharePoint marketing
   plan when available, then use the current Basecamp campaign for destinations, seasonal intent,
   hero order and confirmation. Use the Basecamp archive for completed-campaign history.
2. Normalize continuation-style variant rows when needed.
3. Prepare candidates and rule context from the product/category exports.
4. Read `references/selection-guide.md` before curation.
5. Curate the requested selections and write `selection.json`.
6. Build and validate the review and direct-import files.
7. Read `references/date-safe-handoff.md` and create the Excel-safe review workbook and sealed import ZIP.
8. Return the review workbook, raw import CSV, and sealed import ZIP with a concise validation summary and all warnings.
9. After the import is checked online, read `references/storefront-visual-qa.md` and run the screenshot review and approval loop. Regenerate the files when changes are approved.

Before the download links, create the compact result panel described by
`../begin-web-dmd-workflow/SKILL.md`. Use up to three real metrics such as destination count, selected
products and date overrides; include every validation warning. Add a `handoff` array with exactly
two items for campaign runs: `REVIEW.xlsx · Review file` with kind `review`, and
`CT Import ZIP · Upload package` with kind `upload`. The upload description must say to extract a
fresh CSV and upload it directly without opening or resaving it in spreadsheet software. Show
`::codex-inline-vis{file="web-dmd-results.html"}`. If inline visualizations are unavailable, return
the same summary as concise text.

Render that panel from the campaign skill directory with the explicit sibling path:

```bash
python3 ../begin-web-dmd-workflow/scripts/render_summary.py \
  --input <run-output>/codex-summary.json \
  --out <thread-visualization-root>/web-dmd-results.html
```

Do not begin final curation while required inputs are missing unless the user explicitly accepts the documented reduced-check run.

## Prepare candidates

Normalize a continuation-row catalog when needed:

```bash
python3 scripts/normalize_catalog.py PRODUCTS.csv NORMALIZED.csv
```

Generate candidate flags and validation context:

```bash
python3 scripts/prepare_candidates.py PRODUCTS.csv CATEGORIES.csv CANDIDATES.csv \
  --context-json CONTEXT.json \
  --destinations men-featured-XX,women-featured-XX \
  --delivery-list DELIVERY_LIST.csv
```

Omit `--delivery-list` when none is supplied.

## Enforce campaign rules

Apply these non-negotiable rules; use `references/selection-guide.md` for detailed selection guidance:

- Reject every product assigned to a Sale category or its descendants. Friends & Family and app early access count as Sale: they are price-reduced windows, and a discounted product must not appear in a featured slot.
- Reject products from the two most recent prior featured campaigns for the corresponding audience.
- Treat the SharePoint marketing-plan date as canonical. If Basecamp documents a different date,
  stop and surface both dates for confirmation rather than silently choosing one.
- Require selected products to be currently online.
- Require every auto-curated product to have at least one regular category for its destination
  audience. Historical `men-featured-*` / `women-featured-*` membership does not prove regular
  audience eligibility. A mismatched explicit hero or must-include may proceed only as a visible
  `REVIEW_REQUIRED` exception in the human workbook; it never bypasses Sale, recency or online rules.
- Treat same-delivery products as a priority pool, not a whitelist.
- Add eligible current-online products from other seasons or deliveries when they strengthen the
  campaign edit through better colour, silhouette, product-type, gender or styling balance. Keep
  the campaign story and live-date seasonality coherent; cross-season or cross-delivery status is
  not itself a reason to exclude a product.
- Treat older featured history as a soft negative.
- Anchor seasonality to the campaign live date and market, then let an explicit campaign story override the calendar.
- Default to exactly 48 products per destination because one storefront grid page contains 48 items. Treat any other count as a warning unless the user requested a different target.
- Avoid cross-audience reuse when it would produce conflicting product-level date values.
- Consolidate a product shared by multiple selections into one import row with semicolon-separated destination categories. Never emit multiple direct-import rows for the same product key because the second update can fail with a Commercetools concurrent-modification error.

If a requested hero violates a hard rule, stop and surface the conflict.

## Control temporary date sorting

Ask the plain-language A/B/C question from `references/source-intake.md` only after the source files and hero order are known. Map the answer internally:

- A / hero products only -> `hero_only`.
- B / heroes plus an approved post-hero mix -> `hero_and_priority`.
- C / no date changes -> `none`.

For ranked products, set `attributes.firstPublishedDate` and `attributes.new_arrivals_date` to the same value, beginning with the campaign live date and subtracting one calendar day per rank. Preserve both exported values exactly for all unranked products. Report possible interleaving; do not broaden the override scope merely to remove a warning.

## Write the selection plan

Use this shape:

```json
{
  "campaign_live_date": "2026-09-26",
  "date_sort_mode": "hero_only",
  "target_min": 48,
  "target_max": 48,
  "selections": [
    {
      "category": "men-featured-21",
      "keys": ["PRODUCT_1", "PRODUCT_2"],
      "must_include": ["PRODUCT_1"],
      "hero_keys": ["PRODUCT_1", "PRODUCT_2"],
      "date_priority_keys": []
    }
  ]
}
```

Keep `hero_keys` and `date_priority_keys` ordered. Use `date_priority_keys` only with `hero_and_priority`. Override `target_min` and `target_max` globally or per selection only when the user requests a different count.

## Build and return outputs

Run:

```bash
python3 scripts/build_import.py PRODUCTS.csv selection.json REVIEW.csv CONTEXT.json
```

Omit `CONTEXT.json` only for an explicitly accepted reduced-check run.

Return:

- `REVIEW.xlsx`, the human review file. Store both date columns as literal text displayed in `YYYY-MM-DD` format.
- `REVIEW.xlsx` must include an **Audience Check** worksheet. Auto-curated mismatches block file
  generation. Put explicit hero/must-include exceptions first and highlight them for human review.
- `REVIEW.csv`, the source used to build the review workbook.
- `REVIEW_CT_Import.csv`, the machine import file containing only `key`, `variants.key`, `categories`, `attributes.firstPublishedDate`, and `attributes.new_arrivals_date`.
- `REVIEW_CT_Import_UPLOAD.zip`, containing an untouched copy of the machine import CSV.

Require exactly one row per product key in both files. Join multiple destination categories with `;`. Require every populated date value to use `YYYY-MM-DD`; stop before writing outputs when a preserved source date uses another format.

Never use apostrophe-prefixed dates or spreadsheet formulas such as `="2026-09-29"` in the CT import CSV; Commercetools would receive those extra characters. Treat the CSV as a machine-only artifact. Tell the user to review every non-`PASS` row on the `.xlsx` **Audience Check** worksheet, then extract and upload the CSV from the ZIP without opening or resaving it in Excel or Google Sheets.

Include counts per destination, date-override mode/count, delivery-priority/fallback counts when context is available, Audience Check pass/review/not-checked counts, and every warning or reduced-check limitation.

Do not mark the campaign workflow complete until the user either approves the storefront visual QA or explicitly skips it. Preserve the approved hero order, show proposed additions/removals and post-hero ordering before applying them, and document the final visual changes.
