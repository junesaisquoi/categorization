#!/usr/bin/env python3
"""Render a compact, theme-aware Codex result panel from validated run counts."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


ACTION_DEFINITIONS = {
    "open-review": {
        "label": "Open full review",
        "prompt": "Open the optional full review for the latest Web DMD run.",
        "title": "Open full review",
    }
}


def text(value: object) -> str:
    return html.escape(str(value), quote=True)


def short_string(value: object, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must be a non-empty string of at most {limit} characters")
    return value.strip()


def script_json(value: object) -> str:
    """Serialize data safely for an inline script element."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    metrics = data.get("metrics", [])
    if not isinstance(metrics, list) or not 1 <= len(metrics) <= 3:
        raise ValueError("metrics must contain between one and three entries")
    clean_metrics = []
    for index, item in enumerate(metrics):
        if not isinstance(item, dict):
            raise ValueError(f"metrics[{index}] must be an object")
        clean_metrics.append(
            {
                "label": short_string(item.get("label"), f"metrics[{index}].label", 60),
                "value": short_string(str(item.get("value", "")), f"metrics[{index}].value", 40),
            }
        )

    status = data.get("status", [])
    warnings = data.get("warnings", [])
    actions = data.get("actions", [])
    handoff = data.get("handoff", [])
    if not all(isinstance(items, list) for items in (status, warnings, actions, handoff)):
        raise ValueError("status, warnings, actions and handoff must be lists")
    if len(status) > 6 or len(warnings) > 6 or len(actions) > 3:
        raise ValueError("status and warnings allow at most six items; actions allow at most three")
    if len(handoff) > 2:
        raise ValueError("handoff must contain at most two entries")
    clean_status = [short_string(item, f"status[{index}]", 180) for index, item in enumerate(status)]
    clean_warnings = [short_string(item, f"warnings[{index}]", 240) for index, item in enumerate(warnings)]
    clean_handoff = []
    for index, item in enumerate(handoff):
        if not isinstance(item, dict) or item.get("kind") not in {"review", "upload"}:
            raise ValueError(f"handoff[{index}] must use kind review or upload")
        clean_handoff.append(
            {
                "kind": item["kind"],
                "label": short_string(item.get("label"), f"handoff[{index}].label", 80),
                "description": short_string(item.get("description"), f"handoff[{index}].description", 240),
            }
        )
    safe_actions = []
    for index, item in enumerate(actions):
        if not isinstance(item, dict) or item.get("id") not in ACTION_DEFINITIONS:
            raise ValueError(f"actions[{index}] must contain an allowed id")
        safe_actions.append(ACTION_DEFINITIONS[item["id"]])

    metrics_markup = "\n".join(
        f'''    <div class="card viz-stat">
      <div class="text-muted">{text(item["label"])}</div>
      <div class="viz-stat-value">{text(item["value"])}</div>
    </div>'''
        for item in clean_metrics
    )
    status_markup = "\n".join(
        f'    <span class="viz-badge">{text(item)}</span>' for item in clean_status
    )
    warning_markup = "\n".join(
        f"    <li>{text(item)}</li>" for item in clean_warnings
    )
    actions_markup = "\n".join(
        f'    <button class="btn" type="button" data-action="{index}">{text(item["label"])}</button>'
        for index, item in enumerate(safe_actions)
    )
    handoff_markup = "\n".join(
        f'''    <div class="card web-dmd-handoff web-dmd-handoff-{text(item.get("kind", "review"))}">
      <strong>{text(item["label"])}</strong>
      <div class="text-small text-muted">{text(item["description"])}</div>
    </div>'''
        for item in clean_handoff
    )

    fragment = f'''<div id="web-dmd-results" aria-label="Web DMD workflow results">
  <style>
    #web-dmd-results .web-dmd-handoff-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:12px; }}
    #web-dmd-results .web-dmd-handoff {{ padding:13px; border-width:1px; }}
    #web-dmd-results .web-dmd-handoff strong {{ display:block; margin-bottom:4px; }}
    #web-dmd-results .web-dmd-handoff-review {{ background:color-mix(in srgb,var(--card) 84%,#376dff 16%); }}
    #web-dmd-results .web-dmd-handoff-upload {{ background:color-mix(in srgb,var(--card) 84%,#138a4b 16%); }}
    @media (max-width:620px) {{ #web-dmd-results .web-dmd-handoff-grid {{ grid-template-columns:minmax(0,1fr); }} }}
  </style>
  <div class="viz-grid">
{metrics_markup}
  </div>
  <div class="viz-row">
{status_markup}
  </div>
  {f'<ul class="text-destructive">{warning_markup}</ul>' if warnings else ''}
  {f'<div class="web-dmd-handoff-grid">{handoff_markup}</div>' if handoff else ''}
  <div class="viz-controls">
{actions_markup}
  </div>
  <div id="web-dmd-results-status" class="text-small text-muted" aria-live="polite"></div>
</div>
<script>
(() => {{
  const root = document.getElementById("web-dmd-results");
  const status = document.getElementById("web-dmd-results-status");
  const actions = {script_json(safe_actions)};
  if (!root || !status) return;
  root.addEventListener("click", async (event) => {{
    const button = event.target.closest("button[data-action]");
    if (!button || !root.contains(button)) return;
    const action = actions[Number(button.dataset.action)];
    if (!action) return;
    button.disabled = true;
    status.textContent = `Opening ${{action.title}}…`;
    try {{
      await window.openai.sendFollowUpMessage(action);
      status.textContent = "";
    }} catch (error) {{
      button.disabled = false;
      status.textContent = "That action did not open. Please try again.";
    }}
  }});
}})();
</script>
'''
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(fragment, encoding="utf-8")


if __name__ == "__main__":
    main()
