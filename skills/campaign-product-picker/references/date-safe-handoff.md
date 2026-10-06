# Date-safe spreadsheet handoff

CSV files do not carry column types or display formats. Excel and Google Sheets may therefore interpret a valid ISO value such as `2026-09-29` as a date and display or resave it as `9/29/26`. Quoting the CSV value does not reliably prevent this conversion.

## Create separate human and machine files

Always produce:

1. **`REVIEW.xlsx` for people to open.** Build it from `REVIEW.csv` with `scripts/build_review_workbook.mjs`. Keep both date columns as literal text and apply the Excel text format `@`, so their visible values remain `YYYY-MM-DD`.
2. **`REVIEW_CT_Import.csv` for Commercetools.** Keep raw ISO values with no apostrophes, formulas, spaces, or locale formatting.
3. **`REVIEW_CT_Import_UPLOAD.zip` for handoff.** The Python builder creates this archive automatically from the validated import CSV.

The Python builder also creates `REVIEW_Audience_Check.csv`. The workbook builder requires it and
adds an **Audience Check** worksheet. This worksheet is the human control for regular Men/Women
category evidence; warning rows appear first and are highlighted.

Do not substitute `="2026-09-29"` or `'2026-09-29` in the import CSV. Those techniques may influence spreadsheet display, but they change the actual value sent to Commercetools.

## Build the review workbook

Load the bundled workspace dependencies, create a writable work directory with a `node_modules` link to the bundled modules, and copy the workbook builder into that directory so Node resolves `@oai/artifact-tool` locally. Then run:

```bash
node work/build_review_workbook.mjs REVIEW.csv REVIEW.xlsx work/review-preview.png
```

Use the Spreadsheets skill for creation and verification. Inspect the two date columns and confirm that the first, middle, and last populated values are literal strings matching `^\d{4}-\d{2}-\d{2}$`. Render the sheet once to confirm the dates display as ISO text and the headers are readable.

## Deliver and use the files

- Tell reviewers to open `REVIEW.xlsx` only.
- Require reviewers to inspect the **Audience Check** worksheet and confirm every non-`PASS` row
  before upload. `REVIEW_REQUIRED` means an explicit hero or must-include has no regular category
  for the destination audience. `NOT_CHECKED_REDUCED` means category context was unavailable and
  the row needs manual verification.
- Keep the raw import CSV and ZIP separate from the review workbook.
- For upload, extract the CSV from `REVIEW_CT_Import_UPLOAD.zip` and upload it directly to Commercetools without opening or resaving it in Excel or Google Sheets.
- If someone already opened and saved the CSV in spreadsheet software, discard that copy and extract a fresh one from the ZIP.

Before delivery, parse the raw import CSV as text and confirm every nonblank value in `attributes.firstPublishedDate` and `attributes.new_arrivals_date` uses `YYYY-MM-DD`.
