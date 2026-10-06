---
name: begin-web-dmd-workflow
description: Show a clickable in-conversation launcher for Carhartt WIP Web DMD work and route the selected task to Campaign Product Picker or Category Builder. Use when the user opens the Web DMD plugin, asks what it can do, wants to start a merchandising workflow, or has not yet specified whether they are building a campaign, adding or correcting categories, moving products into or out of Sale, or reviewing assignments.
---

# Web DMD Workflow

## Show the launcher

Use the in-conversation launcher as the default plugin entry point. Locate the thread-scoped
`.codex/visualizations/...` writable root from the environment context, then run:

```bash
python3 scripts/render_selector.py \
  --out <thread-visualization-root>/web-dmd-workflow-selector.html
```

Respond with only a short question followed by the inline directive:

```text
What do you want to do?

::codex-inline-vis{file="web-dmd-workflow-selector.html"}
```

Each button sends a follow-up message that explicitly invokes the correct skill. Do not also print
the six choices as a text list. If inline visualizations are unavailable, use the same six choices
as a concise text fallback.

## Route the choice

- Route **Build a campaign** to `$campaign-product-picker`.
- Route the other five choices to `$category-builder` with the chosen situation already stated.
- Do not ask the user to choose the workflow again after the button follow-up appears.
- Keep the standalone Category Builder browser UI optional and open it only when explicitly asked.

## Show a compact result

After either workflow finishes, create `codex-summary.json` in that run's output directory:

```json
{
  "metrics": [
    {"label": "Ready to upload", "value": "1,519"},
    {"label": "Excluded", "value": "349"},
    {"label": "Review", "value": "153"}
  ],
  "status": ["16 products currently in Sale"],
  "warnings": ["One or more products need a decision before upload."],
  "handoff": [
    {"kind": "review", "label": "REVIEW.xlsx · Review file", "description": "Open safely using the download link below."},
    {"kind": "upload", "label": "CT Import ZIP · Upload package", "description": "Use the download link below, then extract a fresh CSV and upload it without opening or resaving it."}
  ],
  "actions": [
    {
      "id": "open-review"
    }
  ]
}
```

Use at most three metrics. Include only real counts and warnings from the completed run. Use the
optional `handoff` cards for campaign output safety; omit them for workflows that do not need the
review/upload distinction. Actions use only the renderer-owned `open-review` ID; never place a
free-form follow-up prompt in summary JSON. Then render
the result into the thread visualization root:

```bash
python3 scripts/render_summary.py \
  --input <run-output>/codex-summary.json \
  --out <thread-visualization-root>/web-dmd-results.html
```

Show `::codex-inline-vis{file="web-dmd-results.html"}` before the normal download links. Keep the
CSV, XLSX, ZIP, rollback, excluded, and optional `review.html` files as ordinary downloadable
artifacts outside the result panel.
