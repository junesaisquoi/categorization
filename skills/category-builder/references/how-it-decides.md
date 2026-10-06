# How the tool decides

## The source of truth

`attributes.category_main` in PIM. Everything else is a supplement or a fallback.

The PIM value converts to a category key mechanically: `attropt_category_men_pants_work`
becomes `men-pants-work`. It can hold several values separated by semicolons, and all of
them are used. A value from the other department is dropped and flagged as a PIM error.

When it is missing, three fallbacks run in order and the row says which one was used:

1. a product category already on the product, ignoring placement categories
2. buying's own category label, if it matches a key or a category name
3. a keyword in the product name — **accessories only**

The third is deliberately limited. The name of a sticker or a cap *is* the product type.
The name of a jacket is not, and guessing jacket subtypes from names is what made the old
VBA macro untrustworthy. A jacket with no `category_main` gets nothing and is held back.

## What is added on top

| Rule | Driven by |
|---|---|
| Denim cross-categories | buying's label, material, or denim categories already there |
| Fit | `attributes.fit` |
| Basic versus graphic tees | `attributes.pattern`, positive evidence only |
| Core product collections | tokens in the product name, checked against the live Icons pages |
| Accessory mirroring | accessories belong in both departments |
| New arrivals, featured slots | chosen per run, never derived |

### Basic versus graphic

Graphic means `attropt_pattern_graphic_prints`, nothing else. Deliberately excluded:

- `attropt_pattern_print` marks any printed element including a small chest logo, and
  covers about a third of the catalogue
- `graphic_embroidery` is a small embroidered chest motif, which is a basic tee

If the pattern attribute is empty and the name is not conclusive, the tee gets **neither**
category and says so. Graphic is never a default bucket. It was, and the men's Graphic
Prints listing filled up with plain tees, rugby shirts and a sweatshirt.

## Governed groups — the rule behind every removal

A **governed group** is a set of categories the tool can determine completely from one PIM
attribute. Inside a governed group the derived answer is authoritative, so a member that
was not derived is wrong and gets removed. Outside these groups nothing is removed, because
the tool cannot tell a wrong category from one a merchandiser added on purpose, or one that
is more specific than PIM allows.

Current groups:

| Group | Source |
|---|---|
| T-shirt style | `attributes.pattern` |
| Fit | `attributes.fit` |
| Sleeve length | `attributes.category_main` |
| Product type | `attributes.category_main` |

Two safeguards:

1. A group only has authority when the rules reached a verdict in it. An empty
   `attributes.pattern` means no verdict on basic versus graphic, so nothing in that group
   is touched.
2. Redundant parents are handled separately, because commercetools assigns them anyway.

**Adding a group is the highest-risk change here.** Only add one when a single attribute
genuinely settles the whole set. A winter work jacket is legitimately both winter and work,
so jacket subtypes are not a governed group. When that rule was missing, a correction run
replaced `women-jackets-winter` with the less specific `women-jackets` on fifteen products.

Exceptions where two product types legitimately coexist are listed in `cross_group_allowed`:
shirt jacs are both shirts and jackets, denim pants are both, and so on.

## What is never touched

Placement categories: new arrivals, featured slots, core products, collaborations. These
are merchandising decisions no attribute can reproduce. A placement *parent* may drop when
one of its own children is kept, which keeps the product in the collaboration via the
specific category rather than the top one.

## Buying's list

| Signal | Effect |
|---|---|
| Row shaded red | the style was cut and will not be produced — excluded |
| Comment: Item OUT, do not publish, not to be sold online | excluded |
| Nothing ordered on any channel | the style is out — excluded |
| One piece ordered | a Fotostudio sample, not sellable — excluded |
| Repeat style and repeat colour | a carryover, so never a new arrival |
| Earliest delivery date or drop code | the new-arrivals cutoff |

Red-row detection reads cell fills from the workbook. The run reports how many it found, so
a silent failure is visible. Saving buying's file as CSV loses that marking; the comment and
quantity signals still apply.

## Sale and regular are mutually exclusive

A product is in the sale tree or the regular tree, never both. Friends & Family and app
early access count as sale: they are price-reduced windows, and the definition here is
identical to `SALE_MARKERS` in the campaign picker.
