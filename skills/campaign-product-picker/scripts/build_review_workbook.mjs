#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [, , inputPath, outputPath, previewPath] = process.argv;
if (!inputPath || !outputPath) {
  console.error("Usage: node build_review_workbook.mjs REVIEW.csv REVIEW.xlsx");
  process.exit(2);
}

const csvText = await fs.readFile(inputPath, "utf8");
const nonEmptyLines = csvText.split(/\r?\n/).filter((line) => line.length > 0);
if (nonEmptyLines.length < 2) {
  throw new Error("Review CSV must contain a header and at least one data row.");
}

const inputInfo = path.parse(inputPath);
const audiencePath = path.join(inputInfo.dir, `${inputInfo.name}_Audience_Check${inputInfo.ext || ".csv"}`);
let audienceText;
try {
  audienceText = await fs.readFile(audiencePath, "utf8");
} catch {
  throw new Error(`Audience review CSV not found: ${audiencePath}`);
}
const audienceLines = audienceText.split(/\r?\n/).filter((line) => line.length > 0);
if (audienceLines.length < 2) {
  throw new Error("Audience review CSV must contain a header and at least one data row.");
}

const workbook = await Workbook.fromCSV(csvText, { sheetName: "Review" });
const sheet = workbook.worksheets.getItem("Review");
const lastRow = nonEmptyLines.length;
const body = sheet.getRange(`A1:H${lastRow}`);

sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
body.format.font = { name: "Arial", size: 10, color: "#1A1A1A" };
body.format.verticalAlignment = "center";

const header = sheet.getRange("A1:H1");
header.format = {
  fill: "#2B2B2B",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
header.format.rowHeight = 34;

sheet.getRange(`G2:H${lastRow}`).format.numberFormat = "@";
sheet.getRange(`E2:H${lastRow}`).format.horizontalAlignment = "center";
sheet.getRange(`A2:D${lastRow}`).format.horizontalAlignment = "left";
sheet.getRange(`B2:B${lastRow}`).format.wrapText = true;

sheet.getRange(`A1:A${lastRow}`).format.columnWidth = 22;
sheet.getRange(`B1:B${lastRow}`).format.columnWidth = 52;
sheet.getRange(`C1:C${lastRow}`).format.columnWidth = 24;
sheet.getRange(`D1:D${lastRow}`).format.columnWidth = 32;
sheet.getRange(`E1:F${lastRow}`).format.columnWidth = 18;
sheet.getRange(`G1:H${lastRow}`).format.columnWidth = 25;
sheet.getRange(`A2:H${lastRow}`).format.autofitRows();

const audienceWorkbook = await Workbook.fromCSV(audienceText, { sheetName: "Audience Check" });
const audienceSource = audienceWorkbook.worksheets.getItem("Audience Check");
const audienceValues = audienceSource.getUsedRange().values;
const audienceSheet = workbook.worksheets.add("Audience Check");
const audienceLastRow = audienceValues.length;
audienceSheet.getRange("A1").write(audienceValues);
const audienceBody = audienceSheet.getRange(`A1:H${audienceLastRow}`);
audienceSheet.showGridLines = false;
audienceSheet.freezePanes.freezeRows(1);
audienceSheet.tabColor = "#D97706";
audienceBody.format.font = { name: "Arial", size: 10, color: "#1A1A1A" };
audienceBody.format.verticalAlignment = "center";
audienceSheet.getRange("A1:H1").format = {
  fill: "#2B2B2B",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
audienceSheet.getRange("A1:H1").format.rowHeight = 34;
audienceSheet.getRange(`A2:H${audienceLastRow}`).format.wrapText = true;
audienceSheet.getRange(`A2:H${audienceLastRow}`).format.horizontalAlignment = "left";
audienceSheet.getRange(`A1:A${audienceLastRow}`).format.columnWidth = 24;
audienceSheet.getRange(`B1:B${audienceLastRow}`).format.columnWidth = 22;
audienceSheet.getRange(`C1:C${audienceLastRow}`).format.columnWidth = 48;
audienceSheet.getRange(`D1:E${audienceLastRow}`).format.columnWidth = 22;
audienceSheet.getRange(`F1:G${audienceLastRow}`).format.columnWidth = 38;
audienceSheet.getRange(`H1:H${audienceLastRow}`).format.columnWidth = 54;
for (let rowIndex = 1; rowIndex < audienceValues.length; rowIndex += 1) {
  const verdict = String(audienceValues[rowIndex][4] || "");
  if (verdict === "REVIEW_REQUIRED") {
    audienceSheet.getRange(`A${rowIndex + 1}:H${rowIndex + 1}`).format.fill = "#FFF2CC";
    audienceSheet.getRange(`E${rowIndex + 1}`).format.font = { name: "Arial", size: 10, bold: true, color: "#9C5700" };
  } else if (verdict === "NOT_CHECKED_REDUCED") {
    audienceSheet.getRange(`A${rowIndex + 1}:H${rowIndex + 1}`).format.fill = "#FCE4D6";
    audienceSheet.getRange(`E${rowIndex + 1}`).format.font = { name: "Arial", size: 10, bold: true, color: "#C00000" };
  }
}
audienceSheet.getRange(`A2:H${audienceLastRow}`).format.autofitRows();

workbook.recalculate();
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const saved = await FileBlob.load(outputPath);
const verifiedWorkbook = await SpreadsheetFile.importXlsx(saved);
const verifiedSheet = verifiedWorkbook.worksheets.getItem("Review");
const verifiedAudienceSheet = verifiedWorkbook.worksheets.getItem("Audience Check");
const verifiedDates = verifiedSheet.getRange(`G2:H${lastRow}`).values.flat();
const invalidDates = verifiedDates.filter(
  (value) => value !== null && value !== "" && (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)),
);
if (invalidDates.length) {
  throw new Error(`Review workbook contains ${invalidDates.length} non-ISO or non-text date value(s).`);
}
const verifiedAudienceValues = verifiedAudienceSheet.getRange(`A1:H${audienceLastRow}`).values;
if (verifiedAudienceValues.some((row) => String(row[4] || "") === "BLOCK")) {
  throw new Error("Audience Check contains a blocking mismatch; the workbook must not be handed off.");
}

const sample = await verifiedWorkbook.inspect({
  kind: "table",
  sheetId: "Review",
  range: `G1:H${Math.min(lastRow, 8)}`,
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 2,
  maxChars: 3000,
});
console.log(sample.ndjson);

if (previewPath) {
  const preview = await verifiedWorkbook.render({
    sheetName: "Review",
    range: `A1:H${Math.min(lastRow, 18)}`,
    scale: 1,
    format: "png",
  });
  await fs.mkdir(path.dirname(previewPath), { recursive: true });
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
  const audiencePreview = await verifiedWorkbook.render({
    sheetName: "Audience Check",
    range: `A1:H${Math.min(audienceLastRow, 18)}`,
    scale: 1,
    format: "png",
  });
  const previewInfo = path.parse(previewPath);
  const audiencePreviewPath = path.join(previewInfo.dir, `${previewInfo.name}-audience-check${previewInfo.ext || ".png"}`);
  await fs.writeFile(audiencePreviewPath, new Uint8Array(await audiencePreview.arrayBuffer()));
}

console.log(`Wrote Excel-safe review workbook: ${outputPath}`);
console.log("Date columns are literal ISO text, so Excel displays YYYY-MM-DD without locale conversion.");
console.log("Audience Check worksheet added; review every non-PASS row before upload.");
