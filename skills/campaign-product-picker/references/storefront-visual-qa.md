# Storefront visual QA

Run this review after the first Commercetools import has been checked online. It is part of the campaign workflow, not an optional polish pass, unless the user explicitly skips it.

## Request the evidence

Ask for one full-page desktop screenshot per destination after the import is visible. Prefer a four-column view that shows the whole 48-item grid, including the hero block and the final row.

If the screenshot is cropped, review what is visible and ask only for the missing section needed to confirm the grid count or ordering.

## Review each destination independently

Check:

- **Count:** expect 48 products, filling one complete grid page. Report any shortfall or overflow.
- **Hero order:** confirm the approved heroes lead the grid in the intended order.
- **First fold:** inspect the first 12–16 products for immediate campaign identity plus enough visual relief.
- **Color and brightness:** flag an overly dark, light, or single-color run; look for useful contrast from lighter neutrals, muted color, or a different dominant tone.
- **Pattern repetition:** flag clusters of near-identical prints, washes, or fabric treatments unless repetition is intentional to the story.
- **Product-type rhythm:** avoid long runs of the same type; mix outerwear, tops, bottoms, and accessories where eligible items support the story.
- **Accessory density:** keep accessories from overwhelming apparel unless the brief calls for it.
- **Duplication and freshness:** re-check additions against Sale, current-online, recent-two-campaign, and duplicate-product rules.
- **Audience balance:** judge Men and Women separately; do not assume the same mix or issue applies to both.

Use these as diagnostic checks, not rigid quotas. The campaign brief and hero story remain authoritative.

## Propose changes before applying them

Return a compact review with:

1. what works;
2. what looks repetitive, dark, sparse, or unbalanced;
3. the current count and target of 48;
4. proposed removals, additions, and the reason for each;
5. an ordered **post-hero mix** when specific products should appear immediately after the heroes.

Do not modify dates or regenerate the import until the user approves the proposed product keys and order.

When imagery is available, use it to judge the proposed mix. Product attributes may shortlist candidates but are not a substitute for visual confirmation.

## Apply an approved post-hero mix

To place mixed items directly after the hero block:

1. Preserve `hero_keys` in their approved order.
2. Put the approved mix keys in `date_priority_keys` in display order.
3. Set `date_sort_mode` to `hero_and_priority`.
4. Ensure every ranked key also appears in that destination's `keys` list.
5. Regenerate both CSVs and review the warnings.

The builder writes matching sequential values to `attributes.firstPublishedDate` and `attributes.new_arrivals_date`: heroes first, then the approved mix. These are product-level attributes and may affect other storefront placements, so keep the override group as small as the visual goal allows.

## Re-check and close

After the revised import:

1. Ask for updated full-page screenshots.
2. Confirm 48 products, hero order, post-hero order, and improved grid rhythm.
3. Check that no new dark/repetitive cluster was introduced farther down the page.
4. Record the final additions, removals, ranked mix keys, and any accepted limitations.

Complete the workflow only after the user approves the revised storefront or explicitly accepts the remaining limitations.
