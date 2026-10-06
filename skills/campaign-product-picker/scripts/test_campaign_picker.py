#!/usr/bin/env python3
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PREPARE = SCRIPT_DIR / "prepare_candidates.py"
BUILD = SCRIPT_DIR / "build_import.py"


class CampaignAudienceValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.products = self.root / "products.csv"
        self.categories = self.root / "categories.csv"
        self.candidates = self.root / "candidates.csv"
        self.context = self.root / "context.json"
        self._write_categories()
        self._write_products()
        result = subprocess.run(
            [
                sys.executable,
                str(PREPARE),
                str(self.products),
                str(self.categories),
                str(self.candidates),
                "--context-json",
                str(self.context),
                "--destinations",
                "women-featured-new",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self):
        self.temp.cleanup()

    def _write_categories(self):
        rows = [
            ["men", "", "0.1", "Men", "true"],
            ["women", "", "0.2", "Women", "true"],
            ["men-featured", "men", "0.1", "Men Featured", "true"],
            ["women-featured", "women", "0.1", "Women Featured", "true"],
            ["men-jackets", "men", "0.2", "Men Jackets", "true"],
            ["women-jackets", "women", "0.2", "Women Jackets", "true"],
            ["women-featured-old", "women-featured", "0.9", "Old Campaign", "false"],
            ["women-featured-new", "women-featured", "0.01", "New Campaign", "true"],
        ]
        with self.categories.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["key", "parent.key", "orderHint", "name.en", "custom.fields.active"])
            writer.writerows(rows)

    def _write_products(self):
        rows = [
            ["MEN_ONLY", "Men Jacket", "MEN_ONLY_V1", "men-jackets", "2026-08-01", "2026-08-01", "true", "true", "false"],
            ["FEATURED_ONLY", "Featured History Jacket", "FEATURED_ONLY_V1", "men-jackets;women-featured-old", "2026-08-02", "2026-08-02", "true", "true", "false"],
            ["WOMEN_OK", "Women Jacket", "WOMEN_OK_V1", "women-jackets", "2026-08-03", "2026-08-03", "true", "true", "false"],
        ]
        with self.products.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "key",
                "name.en",
                "variants.key",
                "categories",
                "attributes.firstPublishedDate",
                "attributes.new_arrivals_date",
                "published",
                "attributes.main_visible_flag_b2c",
                "attributes.main_item_out",
            ])
            writer.writerows(rows)

    def _build(self, key, *, heroes=None, must=None, priority=None, with_context=True):
        plan = {
            "date_sort_mode": "none",
            "target_min": 1,
            "target_max": 1,
            "selections": [
                {
                    "category": "women-featured-new",
                    "keys": [key],
                    "hero_keys": heroes or [],
                    "must_include": must or [],
                    "date_priority_keys": priority or [],
                }
            ],
        }
        plan_path = self.root / f"{key}-selection.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        review_path = self.root / f"{key}-REVIEW.csv"
        command = [sys.executable, str(BUILD), str(self.candidates), str(plan_path), str(review_path)]
        if with_context:
            command.append(str(self.context))
        result = subprocess.run(command, text=True, capture_output=True)
        return result, review_path

    def test_featured_history_is_not_regular_women_evidence(self):
        context = json.loads(self.context.read_text(encoding="utf-8"))
        women = context["eligibility"]["regular_audience_categories"]["women"]
        self.assertIn("WOMEN_OK", women)
        self.assertNotIn("FEATURED_ONLY", women)

        with self.candidates.open(newline="", encoding="utf-8-sig") as f:
            rows = {row["key"]: row for row in csv.DictReader(f)}
        self.assertEqual(rows["FEATURED_ONLY"]["_women_audience_eligible"], "false")
        self.assertEqual(rows["WOMEN_OK"]["_women_audience_eligible"], "true")

    def test_auto_mismatch_blocks_before_outputs(self):
        result, review = self._build("FEATURED_ONLY")
        self.assertEqual(result.returncode, 2)
        self.assertIn("auto-selected products lack a regular Women category", result.stderr)
        self.assertFalse(review.exists())
        self.assertFalse(review.with_name(f"{review.stem}_CT_Import.csv").exists())

    def test_explicit_hero_mismatch_is_listed_for_human_review(self):
        result, review = self._build("FEATURED_ONLY", heroes=["FEATURED_ONLY"], must=["FEATURED_ONLY"])
        self.assertEqual(result.returncode, 0, result.stderr)
        audience = review.with_name(f"{review.stem}_Audience_Check.csv")
        with audience.open(newline="", encoding="utf-8-sig") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["audience_check"], "REVIEW_REQUIRED")
        self.assertEqual(row["selection_role"], "hero")

        ct = review.with_name(f"{review.stem}_CT_Import.csv")
        with ct.open(newline="", encoding="utf-8-sig") as f:
            self.assertEqual(
                csv.DictReader(f).fieldnames,
                [
                    "key",
                    "variants.key",
                    "categories",
                    "attributes.firstPublishedDate",
                    "attributes.new_arrivals_date",
                ],
            )

    def test_regular_women_product_passes(self):
        result, review = self._build("WOMEN_OK")
        self.assertEqual(result.returncode, 0, result.stderr)
        audience = review.with_name(f"{review.stem}_Audience_Check.csv")
        with audience.open(newline="", encoding="utf-8-sig") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["audience_check"], "PASS")
        self.assertEqual(row["regular_destination_categories"], "women-jackets")

    def test_date_priority_alone_does_not_bypass_mismatch(self):
        result, review = self._build("MEN_ONLY", priority=["MEN_ONLY"])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(review.exists())

    def test_reduced_check_build_lists_not_checked(self):
        result, review = self._build("MEN_ONLY", with_context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        audience = review.with_name(f"{review.stem}_Audience_Check.csv")
        with audience.open(newline="", encoding="utf-8-sig") as f:
            row = next(csv.DictReader(f))
        self.assertEqual(row["audience_check"], "NOT_CHECKED_REDUCED")
        self.assertIn("reduced-check", result.stdout)


if __name__ == "__main__":
    unittest.main()
