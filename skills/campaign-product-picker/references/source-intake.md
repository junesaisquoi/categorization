# Source intake

## Interaction model

Use a staged intake. Do not present every missing field and decision in the first response.

When launched from the plugin without existing campaign details, first show the visual intake
defined in `../SKILL.md`. Treat every field in that form as optional and do not ask the user to
re-enter information that can be read from the campaign sources. After the form follow-up, begin
the source-upload stage below. When the user starts with details or attachments already present,
skip the form and inspect what is available.

1. Ask for the source uploads.
2. Inspect everything supplied and extract values already present.
3. Show a compact status checklist.
4. Ask only the next blocking question.
5. Repeat until ready.

Ask one question per turn unless two values naturally belong together, such as the Men and Women destination keys. Never repeat received items.

## First response

After the visual form is submitted—or immediately when the form is skipped—keep the introduction
to one sentence, then request these source bundles:

> I’ll turn the campaign material into a 48-product selection per destination and produce review plus Commercetools import CSVs.
>
> **Please start by uploading:**
>
> - [ ] **Commercetools exports — 2 CSV files**
>   - **Products CSV:** export the full relevant assortment with the filter `published = Yes`.
>   - **Categories CSV:** export the category hierarchy. This is a separate Categories export, not the product list.
> - [ ] **Campaign planning material** — the current Basecamp campaign post/material plus the
>   SharePoint e-Com Marketing Plan when available.
>   - **SharePoint:** paste the direct workbook URL. The URL alone is enough when it opens in the
>     user's signed-in browser and their account has permission. If access fails, upload an `.xlsx`
>     export instead; there is no need to retype the dates.
>   - **Basecamp:** paste the current campaign URL or attach/export its post and files.
>   Basecamp supplies copy, assets, hero order and destinations; the marketing plan supplies the
>   canonical go-live date.
> - [ ] **Same-delivery item list — optional** — usually found in the campaign plan or seasonal item file linked from Basecamp.
>
> Once these are attached, I’ll check them and ask only for the next missing detail.

Do not present date-sort choices, seasonality questions, previous-campaign questions, or a long missing-fields list in the first response.

## Commercetools exports

Treat the two CSVs as one upload group but explain that they are different CT exports.

### Products CSV

Require the full relevant assortment filtered to `published = Yes`, not only campaign candidates or the same delivery.

Require:
- `key`
- `variants.key`
- `categories`
- `attributes.firstPublishedDate`
- `attributes.new_arrivals_date`

Strongly prefer the normal merchandising and eligibility columns for:
- product name/title;
- B2C visibility and Item OUT status;
- main category and gender;
- material/fabric, color, pattern and fit;
- current season, details and descriptions.

Use the product export to build the candidate pool, preserve original dates for untouched items, and supply valid product and variant keys.

### Categories CSV

Require for full validation:
- `key`
- `parent.key`
- `orderHint`
- category name;
- `custom.fields.active` when available.

Use it to resolve the Sale hierarchy and automatically detect the two most recent actually-run Men and Women featured campaigns. Do not ask the user for previous featured-category keys during normal intake. Ask for confirmation only if automatic detection is ambiguous, and show the candidate keys that need confirmation.

If the Categories CSV is unavailable, explain that Sale hierarchy and recent-two exclusions cannot be fully verified. Proceed only after the user explicitly accepts a reduced-check run.

## Campaign date and history sources

Use these team sources when browser or connector access is available:

- **Canonical go-live calendar:** `2026 e-Com Marketing Plan.xlsx` in SharePoint. Read the `Plan`
  calendar and match the campaign name or delivery label to its dated row.
- **Current campaign brief:** the active Basecamp campaign post or to-do set.
- **Completed campaign history:**
  `https://3.basecamp.com/3294670/buckets/20399786/recordings/3376203915/archive`.
  Use this archive for completed-campaign dates, prior hero material and campaign context; do not
  mistake an archived date for the current campaign's date.

Date precedence is: SharePoint marketing plan, then Basecamp confirmation. When both sources have
a date and they disagree, surface both values and stop for confirmation. Do not silently override
one with the other.

For the SharePoint marketing plan, a direct workbook URL is the preferred input and is sufficient
when it opens through the user's own authenticated browser session or an approved connected
SharePoint account. Every team member must have their own permission to the workbook. Never request
or reuse another person's credentials. If the URL cannot be opened because of sign-in, permissions
or connection availability, ask for an `.xlsx` export of the workbook; a copy of the `Plan` sheet
is sufficient when it preserves the campaign names and dated columns.

If SharePoint or Basecamp is not connected, ask the user to attach, download or paste the relevant
material. Do not claim direct access. A SharePoint workbook export is acceptable and preferable to
manually retyping dates.

Use an already authenticated team Basecamp browser session when available. Never write Basecamp
usernames, passwords or verification codes into `SKILL.md`, plugin assets, source control, review
files or distributable ZIPs. Authentication secrets belong in the company's approved password
manager or browser credential store. If Basecamp requests a one-time verification code, pause and
ask the user for that code; never attempt to bypass the verification step.

## Basecamp campaign material

Treat the Basecamp post and its attachments as one campaign bundle. Extract:
- campaign/featured-category name and approved copy;
- Men/Women hero product keys and their intended display order;
- campaign and hero images;
- styling, palette, material and product-type direction;
- exclusions or must-includes;
- destination category keys when documented;
- campaign live date when documented, as a confirmation of the SharePoint plan;
- seasonal intent when documented.

Use the archive only for prior completed campaigns. Use the current Basecamp campaign for the live
brief. If Basecamp is not connected, ask the user to attach, download or paste the material. Do not
claim direct access.

## Same-delivery list

Treat the same-delivery/drop item list as preferred, not required. Describe it as the item list usually found in the campaign plan or seasonal file linked from Basecamp. Use it as a priority pool, not a whitelist. The final edit may include eligible current-online products from other deliveries or seasons when they improve the campaign's colour, silhouette, product-type, gender or styling mix.

If it is absent, continue from the full published product assortment and state later that delivery priority was unavailable.

## Progressive status checklist

After inspecting uploads, show only a compact status block:

> **Campaign setup**
> - [x] CT Products CSV — received
> - [x] CT Categories CSV — received
> - [x] Basecamp campaign material — received
> - [ ] Same-delivery list — optional
>
> **Detected**
> - Live date: `2026-09-26`
> - Destinations: Men found; Women missing
> - Hero order: found
> - Seasonal direction: Autumn / fewer shorts
> - Date handling: not chosen yet
>
> **Next question:** What is the Women destination category key?

Use `[x]`, `[ ]`, and short values. Do not prefix every line with “Missing — required.”

## Ask missing questions in order

After inspecting the sources, ask only the first unresolved item in this order:

1. **Campaign live date** — ask for `YYYY-MM-DD` only when not found in either the SharePoint plan
   or the current Basecamp material.
2. **Destination category keys** — ask for Men and Women together when both are missing.
3. **Hero order** — ask whether the Basecamp hero list is already in exact display order only when unclear.
4. **Seasonal intent** — infer from the live date, market and Basecamp story. Ask only when ambiguous. Use plain examples such as “Autumn: fewer shorts and swim; more trousers, long sleeves and layers.”
5. **Date handling** — ask after the campaign sources and hero order are known.

## Explain date handling plainly

Introduce the actual export attributes and their effect:

> The storefront currently uses `attributes.firstPublishedDate` and `attributes.new_arrivals_date` for temporary product ordering. Which products may I update?
>
> **A. Hero products only — recommended**  
> Apply sequential dates to the ordered Basecamp hero products only. Every other selected product keeps both exported dates unchanged.
>
> **B. Heroes plus an approved post-hero mix**  
> Rank the heroes first, then an ordered set of products chosen to improve the campaign grid’s color and product-type mix. I’ll show these product keys and their order for approval before the import is finalized. They will appear directly after the heroes; all remaining products keep their exported dates.
>
> **C. No date changes**  
> Preserve both exported date attributes for every selected product.

Explain once that these are product-level attributes and may affect other storefront placements. Do not use internal mode names such as `hero_only` in the user-facing question. Map A/B/C internally to `hero_only`, `hero_and_priority`, and `none`.

## Optional overrides

Accept special must-includes, a different product-count target, explicit seasonality exceptions, or a user-specified ordered post-hero mix. Never allow an override to bypass the Sale exclusion silently.
