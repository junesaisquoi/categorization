#!/usr/bin/env python3
"""Regression tests for the Web DMD result renderer."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("render_summary.py")


def base_data() -> dict:
    return {
        "metrics": [{"label": "Selected", "value": "86"}],
        "status": [],
        "warnings": [],
        "handoff": [],
        "actions": [],
    }


class RenderSummaryTests(unittest.TestCase):
    def render(self, data: dict) -> subprocess.CompletedProcess[str]:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        source = root / "summary.json"
        output = root / "result.html"
        source.write_text(json.dumps(data), encoding="utf-8")
        result = subprocess.run(
            ["python3", str(SCRIPT), "--input", str(source), "--out", str(output)],
            text=True,
            capture_output=True,
        )
        result.output_path = output  # type: ignore[attr-defined]
        return result

    def tearDown(self) -> None:
        if hasattr(self, "tempdir"):
            self.tempdir.cleanup()

    def test_inline_script_json_cannot_close_script(self) -> None:
        data = base_data()
        data["actions"] = [{"id": "open-review"}]
        data["status"] = ["</script><img src=x onerror=alert(1)>"]
        result = self.render(data)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.output_path.read_text(encoding="utf-8")  # type: ignore[attr-defined]
        self.assertNotIn("</script><img", output)
        self.assertIn("&lt;/script&gt;&lt;img", output)

    def test_unknown_action_is_rejected(self) -> None:
        data = base_data()
        data["actions"] = [{"id": "run-anything"}]
        result = self.render(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("allowed id", result.stderr)

    def test_unknown_handoff_kind_is_rejected(self) -> None:
        data = base_data()
        data["handoff"] = [{"kind": "danger", "label": "X", "description": "Y"}]
        result = self.render(data)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("kind review or upload", result.stderr)


if __name__ == "__main__":
    unittest.main()
