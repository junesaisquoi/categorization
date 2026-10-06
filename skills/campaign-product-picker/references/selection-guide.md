# Campaign selection guide

## Core priority

Build a coherent campaign edit rather than a mechanical category mix. Use this hierarchy:

1. Ordered hero/must-include products that pass hard exclusions.
2. Strong eligible products from the same delivery/drop.
3. Other current-online eligible products when same-delivery items are visually weak, seasonally unsuitable, repetitive, or insufficient.
4. Prefer fresh products over older featured-history products when the options are otherwise comparable.

## Mix beyond the same delivery

The delivery/drop list sets the starting priority; it does not define the full assortment. Select
eligible current-online products from other deliveries or seasons when they create a stronger and
more complete campaign grid—for example by improving colour flow, silhouette variety, product-type
coverage, gender balance, layering or styling combinations.

Judge these additions by story fit and seasonality at the campaign live date. Do not add unrelated
products merely to reach 48 items, and never relax Sale, current-online or recent-two-campaign hard
exclusions. Report the final count of same-delivery products and other-online additions in the
review summary.

## Hard exclusions

### Sale
Any Sale-category membership is an absolute hard no. Use both the product `categories` field and the category hierarchy/descendants.

### Two most recent featured campaigns
For each audience, exclude products used in the two most recent actually-run featured categories. Detect recency from direct `men-featured` / `women-featured` children with real product membership and lowest numeric `orderHint`, excluding the new destination and inactive/empty placeholders. Explicit user-provided prior keys override the heuristic.

Older featured membership is a soft freshness signal only.

## Current-online eligibility

Use product-level signals first:
- `published`
- `attributes.main_visible_flag_b2c`
- `attributes.main_item_out`

Supporting variant signals may include:
- `attributes.visible_flag_b2c`
- `attributes.item_out`
- `attributes.published`

If the supplied export is explicitly the complete published/online assortment, presence in the export can be the baseline unless a field contradicts it.

## Story-fit fields

Use fields together rather than keyword-matching one attribute:
- `name.en`
- `attributes.productTitle.en`
- `attributes.item_name_userfriendly.en`
- `attributes.category_main`
- `attributes.gender_userfriendly`
- `attributes.gender_product`
- `attributes.main_material_description.en`
- `attributes.filtermaterial`
- `attributes.material`
- `attributes.fabric.en`
- `attributes.color_description.en`
- `attributes.filtercolor`
- `attributes.marketing_color_finish`
- `attributes.pattern`
- `attributes.fit`
- `attributes.details.en`
- `attributes.product_item_description.en`
- `attributes.description_long_navision.en`
- `attributes.current_season`

Use attached campaign imagery for palette, silhouette, layering, texture, and product-type cues.

## Audience handling

Use actual category assignments as the strongest storefront signal. Gender attributes are supporting information. Unisex products can be valid for Men or Women when legitimately categorized there.

For automated curation, require an assigned regular category inside the destination audience tree.
Exclude the entire `men-featured` / `women-featured` subtree and every Sale subtree from this
evidence. A product used in an older Women featured campaign is not thereby a regular Women
product, and the same rule applies to Men.

Block file generation when an auto-curated product lacks regular destination-audience evidence.
An explicit `hero_keys` or `must_include` item may remain because the campaign brief can
intentionally cross audiences, but mark it `REVIEW_REQUIRED` and list it first on the workbook's
**Audience Check** worksheet. Date-priority status alone is not an exception. Audience exceptions
never bypass Sale, recent-two-campaign or current-online rules.

When date-based sort overrides are active, avoid using the same product in multiple selections if those selections would require different product-level dates.

When the same product is valid for multiple selections with the same effective dates, keep it in both selections but emit one review/import row. Join the destination category keys with semicolons, for example `men-featured-9;women-featured-9`. Never emit the same product key twice in the direct import because sequential updates can trigger a Commercetools concurrent-modification error.

## Seasonality

Anchor seasonality to the **campaign live date**, not the current conversation date.

For standard EU/Northern Hemisphere campaigns:
- **Mar-Apr / Sep-Oct transitional:** limit shorts/swim and overt high-summer pieces; emphasize long pants, long sleeves, overshirts, light jackets, sweats and knitwear. Short-sleeve tees may remain as layering/support items.
- **May-Aug warm:** lighter layers, shorts and short sleeves are normal when story-appropriate.
- **Nov-Feb cold:** heavily de-prioritize shorts/swim and summer-only pieces; emphasize outerwear, knitwear, sweats, long sleeves and pants.

Treat this as a weighting, not a universal exclusion. The campaign brief, imagery, market/climate, and intentional stories such as resort/travel override the calendar.

If the campaign brief is ambiguous, ask whether the user wants normal seasonal balance or an intentional off-season story rather than guessing.

## Assortment balance

Consider complete looks and avoid over-concentration unless the story calls for it:
- T-shirts / long sleeves
- shirts / overshirts
- sweatshirts / knitwear
- jackets / layering pieces
- pants / denim / shorts
- footwear
- accessories

Target 48 products so one complete storefront grid page is filled. If fewer than 48 strong eligible products are available, keep the stronger edit and report the shortfall instead of padding it with near-duplicates or weak products.

## Date-sort logic

The temporary sorting fields are:
- `attributes.firstPublishedDate`
- `attributes.new_arrivals_date`

Use the same generated date in both fields for every intentionally ranked product.

Start from campaign live date and subtract one day per position. Example for `2026-09-26`:
1. item 1 -> `2026-09-26`
2. item 2 -> `2026-09-25`
3. item 3 -> `2026-09-24`

Modes:
- `hero_only`: rank ordered hero keys only.
- `hero_and_priority`: rank ordered heroes, then the user-approved ordered post-hero mix.
- `none`: no date overrides.

For every other selected product, copy the original two date values exactly from the export. Do not blank, normalize, or rewrite them.

Require every nonblank source or generated value in both date columns to use `YYYY-MM-DD`. Stop with a clear validation error when an exported value uses a locale format such as `9/29/26`; do not generate an invalid import.

If a preserved product has a date that could sort above/interleave with a ranked item, report that as a warning. Do not silently change it unless the user opted into broader date adjustment.

## Output

Review CSV:
```csv
key,product_name,variants.key,categories,date_sort_rank,date_sort_action,attributes.firstPublishedDate,attributes.new_arrivals_date
```

Direct CT import:
```csv
key,variants.key,categories,attributes.firstPublishedDate,attributes.new_arrivals_date
```

`date_sort_action` should be `override` for intentionally ranked products and `preserve` for untouched products.

The builder also writes `REVIEW_Audience_Check.csv`, with one row per destination/product pair.
The review workbook turns this into an **Audience Check** worksheet. Humans must confirm every
`REVIEW_REQUIRED` or `NOT_CHECKED_REDUCED` row before upload.
