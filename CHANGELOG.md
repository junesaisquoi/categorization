# Changelog

## Unreleased

- Added a visual campaign intake that opens directly from the plugin launcher, with optional brief
  fields, a source-file checklist, and clear review-versus-upload date-safety guidance.
- Added optional review/upload handoff cards to the native result panel so campaign reviewers know
  which workbook to open and which import package to keep untouched.
- Added regular-audience validation to campaign builds. Auto-curated Men/Women mismatches now
  stop output generation, while explicit cross-audience heroes and must-includes are highlighted
  for confirmation on a mandatory Audience Check worksheet.
- Renamed the launcher's internal sort key so Web DMD Workflow appears first in the skill list.
- Clarified that campaign assortments may include eligible current-online products from other
  seasons or deliveries when they improve the overall mix.

## 0.3.2 — 2026-09-30 — SharePoint intake clarification

- Clarified that a direct SharePoint marketing-plan URL is sufficient when it opens in the user's
  authenticated browser session and their account has permission.
- Added `.xlsx` export fallback guidance when the link cannot be accessed.
- Explicitly requires each team member to use their own authorized SharePoint access.

## 0.3.2 — 2026-09-30 — Native interactive launcher

- Added a clickable in-conversation workflow launcher with six routed Web DMD tasks.
- Added a reusable compact results panel for category and campaign runs.
- Made the launcher the plugin's default **Try now** experience.
- Kept the standalone Category Builder HTML workspace as the optional full-review surface.

## 0.3.2 — 2026-09-30 — Unified workflow entry

- Made the native Codex conversation the default Category Builder experience.
- Added a first-step task selector for campaign, regular category, correction, Sale, de-Sale, and review workflows.
- Kept the loopback HTML tool as an explicit standalone option.
- Split the standalone UI's combined assignment card into separate **Add regular categories** and **Correct category assignments** choices.
- Aligned the plugin and skill launch prompts with the same task names and routing.

## 0.3.2 — 2026-09-29

- Added campaign source precedence: SharePoint marketing plan for canonical go-live dates,
  current Basecamp for briefs, and the Basecamp recording archive for completed-campaign history.
- Documented secure Basecamp-session handling without embedding shared credentials in the plugin.
- Replaced the shared hierarchy plugin icon with the CWIP mark and added distinct UI icons for
  Category Builder (padded hierarchy) and Campaign Product Picker (campaign megaphone).
- Refined the icon crops after UI review: removed the CWIP wordmark and increased the Category
  Builder artwork to a balanced, readable size.
- Changed the corrected icon filenames to invalidate persistent Codex UI image caches.
- Fixed Excel percentage parsing so `-30%`/`-40%` (stored as `-0.3`/`-0.4`) resolve to
  the `-30`/`-40` category keys instead of an invalid `0%` category.
- Added `MSS` discount-column auto-detection and explicit exclusion of `NO DISCOUNT` and
  `REPEAT NO DISCOUNT` rows from sale uploads.
- Sale campaigns now assign every discounted product to both the campaign-specific tree
  and the usual Sale tree, including the matching discount and product-type categories.

## 0.3.1 — 2026-09-28

- Added the interactive Category Builder browser UI as a bundled plugin asset with a loopback-only
  launcher.
- Fixed the Sale campaign selector resetting to its first option.
- Fixed stale run-plan text after changing Sale inclusion or Add/Replace behavior.
- Removed the legacy two-pass `[DELETE]` upload option; the UI now exposes only the safer one-pass
  Categories = Replace flow.

## 0.3.0 — 2026-09-28

- **Campaign picker updated**: date-safe spreadsheet handoff (`REVIEW.xlsx` as text-typed
  dates alongside a raw ISO import CSV), storefront visual QA as a standard step, and a
  review workbook builder.
- **Sale alignment re-applied.** The update reintroduced the narrow `(^|-)sale($|-)` match,
  which misses the 62 Friends & Family and app early access categories. `SALE_MARKERS` is
  restored and now also drives the inline per-product check further down the file, which
  had its own copy of the pattern.

  **This is the second time this fix has been lost in an update.** Until the two skills
  share a library, check `sale_category_set` after every picker change:

  ```bash
  python3 -c "import importlib.util,sys;spec=importlib.util.spec_from_file_location('pc','skills/campaign-product-picker/scripts/prepare_candidates.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);print(m.SALE_MARKERS)"
  ```

  It must print `('sale', 'friends-family', 'early-access')`.

## 0.2.0 — 2026-09-26

**New skill: `category-builder`.** Works out commercetools categories from PIM attributes
and buying's list, replacing the Excel VBA categorization macro.

- Categories derived from `attributes.category_main`, not product-name keywords
- Every key validated against the live tree before it is written
- **Governed groups**: the tool only removes a category from a set it can determine
  completely from one PIM attribute
- Only leaf categories are assigned; commercetools adds the parents
- Buying's list honoured: Item OUT, nothing ordered, single-piece Fotostudio samples,
  repeat versus new, delivery dates and drop codes
- One-pass upload using **Categories = Replace**
- `scripts/test_invariants.py` checks seven properties across the whole catalogue;
  verified against 33,036 products

## 0.1.1 — 2026-09-26

- **Sale exclusion now covers Friends & Family and app early access.** The rule matched
  only keys or names containing the word "sale", so 62 discount categories were invisible
  to it. No published product was exposed at the time, because every affected product also
  carried a real sale category and the keys happened to contain "sale"
  (`winter-sale-friends-family-men-30`). That was a coincidence of naming, not a safeguard.
- `SALE_MARKERS` in `prepare_candidates.py` is now identical to the list in
  `category-builder/scripts/rules.py`. **If you change one, change the other.**

## 0.1.0

- Initial campaign product picker: staged source intake, eligibility and freshness checks,
  hero date sequencing, review and Commercetools import CSVs.
