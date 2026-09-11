/**
 * Sec 28: structurally verifies API -> presentation, never
 * API -> financial calculation -> presentation, for the Holdings screen's
 * own source files. In particular: weight is never derived from
 * market_value / portfolio_value client-side (sec 1's explicit example) --
 * every weight rendered comes from an `allocation_pct` field the backend
 * already computed.
 */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const DIR = join(__dirname, "..");
const FILES = readdirSync(DIR)
  .filter((f) => (f.endsWith(".ts") || f.endsWith(".tsx")) && !f.includes(".test."))
  .map((f) => join(DIR, f));

function stripComments(source: string): string {
  return source.split("\n").map((line) => line.replace(/\/\/.*$/, "")).join("\n");
}

describe("Holdings screen: no financial calculation in React", () => {
  it("never divides market_value by a portfolio total to derive a weight", () => {
    for (const file of FILES) {
      const content = stripComments(readFileSync(file, "utf-8"));
      expect(content, `${file} computes weight from market_value / total`).not.toMatch(
        /market_value\s*\/\s*\w*(total|value)/i,
      );
    }
  });

  it("never uses .reduce( to aggregate financial API fields", () => {
    for (const file of FILES) {
      const content = stripComments(readFileSync(file, "utf-8"));
      expect(content, `${file} contains .reduce(`).not.toMatch(/\.reduce\(/);
    }
  });

  it("does not import src/engine or src/history internals", () => {
    for (const file of FILES) {
      const content = readFileSync(file, "utf-8");
      expect(content).not.toMatch(/from ["']src\/(engine|history)/);
      expect(content).not.toMatch(/\bLedger\b|\bStateEngine\b|\bHistoryGenerator\b/);
    }
  });
});
