---
name: category-builder
description: Work out which commercetools categories a Carhartt WIP product belongs in, from PIM attributes and the seasonal buying list, and produce the category upload CSV plus a review page. Use when asked to categorize a new season, add missing regular categories, take products out of sale after a campaign ends, move full-price products into sale, fix products sitting in the wrong category, check what is currently assigned, or explicitly open the standalone Category Builder UI. Replaces the Excel VBA categorization macro.
---

# Category Builder

## Choose the task first

Use the native Codex conversation as the default interface. If the user has not already chosen a
task, render the clickable launcher with the sibling workflow skill:

```bash
python3 ../begin-web-dmd-workflow/scripts/render_selector.py \
  --out <thread-visualization-root>/web-dmd-workflow-selector.html
```

Then show `::codex-inline-vis{file="web-dmd-workflow-selector.html"}` and stop. If inline
visualizations are unavailable, ask one compact fallback question:

> **What do you want to do?**
>
> **A. Add regular categories** — new season or missing assignments; keep existing categories
> **B. Correct category assignments** — remove categories that contradict PIM
> **C. Full price → Sale** — remove regular navigation and add campaign plus usual Sale categories
> **D. Sale → Full price** — remove Sale categories and restore regular navigation
> **E. Review only** — report issues without producing an upload file

Ask only the inputs needed for the selected task. Do not open a browser or send the user to HTML
unless they explicitly request the standalone/browser version.

Map the choices internally: A is `--fix add`, B is `--fix replace`, C uses the **Put products into
sale** workflow, D is `--sale desale`, and E is a report-only run with no upload file.

## Open the optional standalone UI

When the user explicitly asks for the standalone or browser interface, start the bundled
loopback-only app as a long-running process and give them its local URL:

```bash
python3 scripts/serve_ui.py --port 8765
```

Keep the process alive while they use it. If port 8765 is busy, choose another available high port.
The UI processes uploaded files in the browser. It loads its CSV/XLSX parsing libraries from a CDN,
but it does not upload the user's product data. Its first-step labels and order must match the native
Codex choices above. Use the command-line workflow below when Codex produces and validates the files.

## What this does

Works out a product's **regular** categories from PIM, compares them to what the product
has in commercetools now, and writes the upload file. It also reads buying's list to know
which products must not go online at all.

It never uploads anything. The person reviews the output and uploads it themselves.

## Collect the files

After the task is chosen, say in one sentence what will happen, then ask only for the files. Do not
present settings or a list of missing fields in the first response.

> I'll work out the categories from PIM and give you a CSV to upload plus a review page.
>
> **Please upload:**
>
> - [ ] **Commercetools category export** — the category tree, so I know which categories
>       exist and which are switched on
> - [ ] **Commercetools product export** — where every category decision comes from.
>       **Include unpublished products**, or carryovers look like they are missing.
>       Attach several files if published and unpublished come out separately.
> - [ ] **Buying's item list** — optional. It narrows the run to those products and tells
>       me which ones are Item OUT or Fotostudio-only.

Then inspect what arrived and ask only the next blocking question. Do not ask the user to choose the
task again.

For a sale-starting run, the buying-list discount column accepts values such as `-30%`,
`-40%`, `30%`, `40%`, and Excel's numeric equivalents (`-0.3`, `-0.4`). `NO DISCOUNT`
and `REPEAT NO DISCOUNT` rows are deliberately left unchanged and omitted from the sale
upload. Auto-detect a column named `MSS` as the discount column.

Every discounted campaign item belongs in two parallel trees: the selected campaign tree
and the usual Sale tree. For example, a 30%-off men's trouser in Mid Season Sale receives
both `men-mid-season-sale-30` and `men-sale-30`, plus the matching product-type categories
under both roots. The `-30` key is the category displayed as **30% off**; these are not two
separate categories within one tree. Apply the same dual-tree rule to every sale campaign.

Ask about new arrivals or a featured slot only if the person mentions a campaign or a drop.

## Run it

```bash
python3 scripts/build_categories.py CATEGORIES.csv PRODUCTS.csv [MORE_PRODUCTS.csv ...] \
  --items BUYING.xlsx \
  --fix add|replace --sale desale|skip|include \
  --also-add new-arrivals --new-arrivals-by YYYY-MM-DD \
  --out ./output
```

The key column in buying's list is detected by testing which column's values match product
keys in the export. Pass `--key-column` only to override it.

Outputs into `--out`:

| File | What it is |
|---|---|
| `categories.csv` | the complete final category set per product |
| `rollback.csv` | the current state, same shape, to undo |
| `review.html` | grouped and expandable, open in a browser |
| `excluded.csv` | products buying said to leave out, with the reason |

Return all of them. Summarize the important counts and warnings directly in Codex. Describe
`review.html` as an optional expanded standalone review, not as the primary interface.

## Tell them how to upload it

The upload is one pass, not two:

> In the commercetools importer set **List's update behaviour → Categories → Replace**,
> then upload `categories.csv` on its own. It holds the complete final set for each
> product, so anything not in it is removed in the same pass. Leave Variants, Images,
> Prices and Assets on Merge.

Never suggest the old `[DELETE]` two-pass flow. It leaves products invisible between the
two uploads, and Replace does the same job in one.

## The rules that must not be softened

- A product is never written with an empty category set. That would remove it from the site.
- The tool only removes a category belonging to a **governed group**: a set it can determine
  completely from one PIM attribute. Everything else is left alone. See
  `references/how-it-decides.md`.
- Featured slots, new arrivals, core products and collaborations are never removed.
- Sale and regular are mutually exclusive. A discounted product leaves regular navigation,
  but can sit in both its campaign-specific Sale tree and the usual Sale tree.
- Buying's instructions win: Item OUT, nothing ordered, and single-piece Fotostudio samples
  are left out of every upload file.
- New arrivals never go to a product that is a repeat style in a repeat colour.

If the person asks to bypass one of these, say what would break rather than doing it.

## Report back

Before the file links, create the compact result panel described by
`../begin-web-dmd-workflow/SKILL.md` using the real run counts, Sale status, and decision warnings. Show
`::codex-inline-vis{file="web-dmd-results.html"}`. If inline visualizations are unavailable, use the
same concise counts and warnings as text.

Render the panel from the category skill directory with the explicit sibling path:

```bash
python3 ../begin-web-dmd-workflow/scripts/render_summary.py \
  --input <run-output>/codex-summary.json \
  --out <thread-visualization-root>/web-dmd-results.html
```

Give the counts, then the things that need a decision. Keep it short:

> 2,144 products. **1,519 ready to upload**, 349 left out on buying's instructions,
> 153 worth a look, 16 currently in sale.
>
> The 16 in sale need a decision: leave them, or take them out of sale in the same run.
> An expanded standalone review is also available in `review.html`.

Always surface: products in sale, products buying excluded, and anything where the rules
guessed rather than read PIM. Do not bury these in a total.

## Each season

Delivery drop codes change every season. Buying publishes the dates with the list, for
example `SS27 D1 : 01.01.2027`. Update `delivery_windows` in `scripts/rules.py` before the
first run. If a code is unrecognised, the run reports it rather than silently dropping
products out of new arrivals.

## Check the rules still hold

After any change to `rules.py` or `derive.py`:

```bash
python3 scripts/test_invariants.py CATEGORIES.csv PRODUCTS.csv
```

These are properties that must hold for every product whatever the rules say. If one
fails, the change is wrong, not the test.
