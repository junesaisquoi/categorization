#!/usr/bin/env python3
"""The category rules, in one place.

Everything the Category Builder decides comes from here. The browser version
(category-builder repo, src/index.html) implements the same rules; if you change one,
change the other until the two share a library.

Nothing here touches files or prints. Logic only, so the tests can run it directly.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field

# --- shared with the campaign picker -----------------------------------------
# A discounted product is not always in a category with "sale" in the name. Friends &
# Family and app early access are price-reduced windows on the same footing.
SALE_MARKERS = ("sale", "friends-family", "early-access")

# Categories that say where a product is merchandised, not what it is. The rules never
# remove these: they are decisions a person made that no attribute can reproduce.
PLACEMENT_PATTERNS = (r"-new$", r"-featured", r"core-products", r"collaborations")

CONFIG: dict = {
    "category_main_overrides": {"atropt_category_accessories_wallets": "accessories-wallets"},

    "accessory_mirror": {
        "accessories-gloves-and-scarves": ["men-accessories-gloves-and-scarves",
                                           "women-accessories-gloves-and-scarves"],
        "accessories-caps": ["men-accessories-caps", "women-accessories-caps"],
        "accessories-beanies": ["men-accessories-beanies", "women-accessories-beanies"],
        "accessories-belts": ["men-accessories-belts", "women-accessories-belts"],
        "accessories-socks": ["men-accessories-socks", "women-accessories-socks"],
        "accessories-backpacks": ["men-accessories-backpacks", "women-accessories-backpacks"],
        "accessories-bags": ["men-accessories-bags", "women-accessories-bags"],
        "accessories-wallets": ["men-accessories-wallets", "women-accessories-wallets"],
        "accessories-bucket-hats": ["men-accessories-bucket-hats", "women-accessories-bucket-hats"],
        "accessories-gadgets": ["men-gadgets", "women-gadgets"],
    },

    "denim_extra": {
        "men": {"pants": ["men-denim-pants", "men-pants-jeans"],
                "shorts": ["men-shorts-denim", "men-denim-shorts"],
                "bib": ["men-denim-pants"], "shirts": ["men-denim-shirts"],
                "jackets": ["men-denim-jackets"]},
        "women": {"pants": ["women-pants-denim", "women-denim-pants-shorts-overalls"],
                  "shorts": ["women-denim-pants-shorts-overalls"],
                  "bib": ["women-denim-pants-shorts-overalls"],
                  "shirts": ["women-denim-jackets"], "jackets": ["women-denim-jackets"]},
    },

    "fit_map": {
        ("men", "top_regular", "tshirts"): "men-tshirts-regularfit",
        ("men", "top_loose", "tshirts"): "men-tshirts-loosefit",
        ("men", "top_regular", "shirts"): "men-shirts-regular",
        ("men", "top_loose", "shirts"): "men-shirts-loosefit",
        ("men", "bottom_regular", "pants"): "men-pants-regular",
        ("men", "bottom_relaxed", "pants"): "men-pants-relaxed",
        ("men", "bottom_loose", "pants"): "men-pants-loose",
        ("men", "bottom_slim", "pants"): "men-pants-slim",
        ("women", "bottom_loose", "pants"): "women-pants-loose",
        ("women", "bottom_straight", "pants"): "women-pants-straight",
    },
    "fit_denim_mirror": {"men-pants-regular": "men-denim-regular",
                         "men-pants-relaxed": "men-denim-relaxed",
                         "men-pants-loose": "men-denim-loose"},

    # Graphic means a graphic print, nothing else. attropt_pattern_print marks any printed
    # element including a small chest logo, and a small embroidered duck is a basic tee.
    "graphic_pattern_values": ("graphic_prints", "graphic_print"),
    "tshirt_basic_tokens": ("chase", "casey", "american script", "pocket", "madison", "dawson",
                            "base", "standard crew neck", "vista", "nelson", "link script",
                            "duster", "script mockneck", "script embroidery", "verner",
                            "signature script", "holm", "work pocket", "heart patch", "benton",
                            "philipa", "chester", "luca", "embroidery"),
    # deliberately excludes "script": Script and American Script tees are core basics
    "tshirt_graphic_tokens": ("blackletter", "avenue", "boxed", "deadline", "ribbon", "limn",
                              "chinsel", "hatching", "ice fishing", "vote", "blinkerfluid",
                              "framework", "pennon", "chez wip", "hourglass", "feather tree",
                              "winners", "logo", "graphic", "artwork", "motif", "print"),
    "tshirt_style": {"men": ("men-tshirts-basic", "men-tshirts-graphic-prints"),
                     "women": ("women-tshirts-basic", "women-tshirts-graphic")},

    # applied on top of category_main, never instead of it
    "name_additions": {"polo": ("men-tshirts-polos", None)},

    "core_products": {
        "chase": ("men-core-products-chase", "women-core-products-casey"),
        "casey": (None, "women-core-products-casey"),
        "american script": ("men-core-products-american-script",
                            "women-core-products-american-script"),
        " og ": ("men-core-products-og-styles", "women-core-products-og-styles"),
        "single knee": ("men-core-products-work-pants", "women-core-products-work-pants"),
        "double knee": ("men-core-products-work-pants", "women-core-products-work-pants"),
        "simple pant": ("men-core-products-work-pants", "women-core-products-work-pants"),
        "knee pant": ("men-core-products-icons", "women-core-products-icons"),
        "knee short": ("men-core-products-icons", "women-core-products-icons"),
        "knee skirt": (None, "women-core-products-icons"),
        "michigan coat": ("men-core-products-icons", "women-core-products-icons"),
        "detroit jacket": ("men-core-products-icons", "women-core-products-icons"),
        "active jacket": ("men-core-products-icons", "women-core-products-icons"),
        "vista": ("men-core-products-icons", None),
        "nelson t-shirt": ("men-core-products-icons", "women-core-products-icons"),
        "essentials bag": ("men-core-products-icons", "women-core-products-icons"),
        "acrylic watch hat": (None, "women-core-products-icons"),
        "june": (None, "women-core-products-icons"),
        "brandon": (None, "women-core-products-icons"),
        "billie": (None, "women-core-products-icons"),
        "nixon": (None, "women-core-products-icons"),
        "maeve": (None, "women-core-products-icons"),
        "pocket t-shirt": (None, "women-core-products-icons"),
        "pocket small heart": (None, "women-core-products-icons"),
    },

    # never overrides PIM; reports the contradiction so PIM can be corrected
    "name_vs_category": {"sweater": "knits", "half zip sweater": "knits", "knit": "knits",
                         "cardigan": "knits", "hoodie": "sweats", "sweatshirt": "sweats",
                         "t-shirt": "tshirts"},

    # last resort when category_main is missing and nothing else matched. Accessories only:
    # the name IS the product type for a sticker or a cap, and is not for a jacket.
    "name_fallback": {"sticker": "accessories-gadgets", "keyholder": "accessories-gadgets",
                      "key holder": "accessories-gadgets", "keychain": "accessories-gadgets",
                      "incense": "accessories-gadgets", "candle": "accessories-gadgets",
                      "ashtray": "accessories-gadgets", "mug": "accessories-gadgets",
                      "poster": "accessories-gadgets", "patch": "accessories-gadgets",
                      "skateboard": "accessories-gadgets", "towel": "accessories-gadgets",
                      "beanie": "accessories-beanies", "watch hat": "accessories-beanies",
                      "bucket hat": "accessories-bucket-hats", "cap": "accessories-caps",
                      "wallet": "accessories-wallets", "backpack": "accessories-backpacks",
                      "bag": "accessories-bags", "belt": "accessories-belts",
                      "socks": "accessories-socks"},

    # GOVERNED GROUPS — the basis for every removal. A group is a set of categories the
    # rules determine completely from one PIM attribute. Inside one, the derived answer is
    # authoritative, so a member that was not derived is wrong. Outside, nothing is removed.
    # Only add a group when a single attribute genuinely settles the whole set: a winter
    # work jacket is legitimately both winter and work, so jacket subtypes are not a group.
    "governed_groups": [
        {"name": "T-shirt style", "source": "attributes.pattern",
         "members": ["men-tshirts-basic", "men-tshirts-graphic-prints",
                     "women-tshirts-basic", "women-tshirts-graphic"]},
        {"name": "Fit", "source": "attributes.fit",
         "pattern": r"-(regularfit|loosefit|regular|relaxed|loose|slim|straight)$"},
        {"name": "Sleeve length", "source": "attributes.category_main",
         "pattern": r"-tshirts-(shortsleeve|longsleeve)$"},
        {"name": "Product type", "source": "attributes.category_main", "product_type": True},
    ],
    "cross_group_allowed": [("shirts", "jackets"), ("denim", "pants"), ("denim", "shorts"),
                            ("denim", "jackets"), ("denim", "shirts"), ("overalls", "pants"),
                            ("overalls", "denim"), ("sweats", "pants"), ("sweats", "shorts"),
                            ("gadgets", "accessories")],

    "no_fit_groups": ("shorts", "swim"),
    "unisex_types": ("accessories", "gadgets", "shoes"),

    # buying's delivery drops. Update every season; buying publishes the dates with the list.
    "delivery_windows": {"pre": "2026-11-01", "c-o": "2026-11-01", "co": "2026-11-01",
                         "d1": "2027-01-01", "d2": "2027-02-01", "d3": "2027-03-01"},
}


@dataclass
class Tree:
    all: set = field(default_factory=set)
    active: set = field(default_factory=set)
    parent: dict = field(default_factory=dict)
    name: dict = field(default_factory=dict)

    def ancestors(self, key):
        out, cur, n = set(), key, 0
        while cur in self.parent and n < 20:
            cur = self.parent[cur]
            if not cur:
                break
            out.add(cur)
            n += 1
        return out

    def strip_parents(self, keys):
        anc = set()
        for k in keys:
            anc |= self.ancestors(k)
        return [k for k in keys if k not in anc]

    def is_sale(self, key):
        return any(key == m or f"-{m}" in key or key.startswith(f"{m}-") for m in SALE_MARKERS)


def build_tree(rows) -> Tree:
    t = Tree()
    for r in rows:
        k = str(r.get("key") or "").strip()
        if not k:
            continue
        t.all.add(k)
        if str(r.get("custom.fields.active", "")).upper() == "TRUE":
            t.active.add(k)
        p = str(r.get("parent.key") or "").strip()
        if p:
            t.parent[k] = p
        t.name[k] = r.get("name.en", "")
    return t


def to_leaf(value):
    v = str(value or "").strip()
    if not v or v == "nan":
        return None
    if v in CONFIG["category_main_overrides"]:
        return CONFIG["category_main_overrides"][v]
    return re.sub(r"^att?ropt_category_", "", v).replace("_", "-")


def group_of(leaf):
    if not leaf:
        return None
    if leaf.startswith("accessories-"):
        return leaf[len("accessories-"):]
    parts = leaf.split("-")
    if parts[0] in ("men", "women"):
        if len(parts) > 1 and parts[1] == "accessories":
            return "-".join(parts[2:])
        return "-".join(parts[1:])
    return leaf


def group_root(leaf):
    g = group_of(leaf)
    return g.split("-")[0] if g else None


def is_placement(key):
    return any(re.search(p, key) for p in PLACEMENT_PATTERNS)


def parse_date(value):
    """A real date, an Excel serial, or a buying drop code such as 'SS27 D1'."""
    if value is None or value == "":
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    s = str(value).strip()
    token = re.sub(r"^[a-z]{2}\d{2}\s*", "", s.lower()).replace(" ", "")
    if token in CONFIG["delivery_windows"]:
        return _dt.date.fromisoformat(CONFIG["delivery_windows"][token])
    m = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$", s)
    if m:
        y = int(m.group(3))
        y += 2000 if y < 100 else 0
        return _dt.date(y, int(m.group(2)), int(m.group(1)))
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    try:
        return _dt.date(1899, 12, 30) + _dt.timedelta(days=round(float(s)))
    except ValueError:
        return None


def is_women_name(name):
    return bool(re.match(r"^[Ww][\u2019']", str(name or "").strip()))


def resolve_gender(tree, name, product):
    """Best evidence first. The W' prefix is the house convention but is not on every
    record, so PIM and the product's own categories are consulted before defaulting."""
    if is_women_name(name):
        return "women", "the W\u2019 prefix"
    pg = str(product.get("attributes.gender_product")
             or product.get("attributes.gender_userfriendly") or "").lower()
    if re.search(r"women|damen|female", pg):
        return "women", "the gender attribute"
    if re.search(r"\bmen\b|herren|male", pg):
        return "men", "the gender attribute"
    cm = str(product.get("attributes.category_main") or "")
    if re.search(r"_women_|^attropt_category_women", cm):
        return "women", "category_main"
    if re.search(r"_men_|^attropt_category_men", cm):
        return "men", "category_main"
    cur = [x.strip() for x in str(product.get("categories") or "").split(";")
           if x.strip() and not is_placement(x.strip()) and not tree.is_sale(x.strip())]
    w = any(k.startswith("women-") for k in cur)
    m = any(k.startswith("men-") for k in cur)
    if w and not m:
        return "women", "the categories already on the product"
    if m and not w:
        return "men", "the categories already on the product"
    return "men", None
