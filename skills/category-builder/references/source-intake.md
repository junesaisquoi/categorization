# Source intake

Use a staged intake. Do not present every option and missing field in the first response.

1. Ask for the files.
2. Inspect what arrived.
3. Show a short status.
4. Ask only the next blocking question.

## Commercetools category export

The category tree. Needs `key`, `parent.key`, `custom.fields.active`, `name.en`.

Without it nothing can run: every category the tool assigns is checked against this file.

## Commercetools product export

**Every category decision comes from this file.** Needs `key` and `categories` always, plus
`name.en`, `attributes.category_main`, `attributes.type`, `attributes.fit`,
`attributes.pattern`, `attributes.gender_product`,
`attributes.main_material_description.en`. Simplest is to export all attributes.

Two things to check when it arrives:

- **Is it filtered to published products?** If every row has `published = true`, say so.
  Carryovers sitting unpublished will otherwise look like they are missing from
  commercetools. Ask for an export without that filter, or for the unpublished one as a
  second file. Several files can be passed at once and are merged by product key.
- **Are the attribute columns there?** Without `attributes.category_main` the tool falls
  back to guessing, and most products will be held back.

## Buying's item list

Optional. It narrows the run and carries buying's instructions. Only a column holding the
product key is required; the tool finds it by testing which column's values match product
keys, so the column name does not matter.

Columns it will use when present: delivery date or drop code, new/repeat style and colour,
order quantities, comments, and buying's own category label.

Column names change every season and often contain line breaks. Both are handled. If a
column is missing, the rule that depends on it simply does not fire, and the run says so.

## Status to show after inspecting

> **Files**
> - [x] Category tree — 578 categories
> - [x] Product data — 33,036 products, includes unpublished
> - [x] Buying's list — 2,144 rows, 177 marked red
>
> **Next:** which of these are you doing? (A/B/C/D)

Keep it to this shape. Do not list every detected column.
