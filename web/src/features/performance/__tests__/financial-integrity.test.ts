/**
 * Sec 34: structurally verifies API -> presentation, never
 * API -> financial calculation -> presentation, for the Performance
 * screen's own source files. Not a blanket ban on arithmetic (chart
 * coordinates and formatting legitimately compute things) -- specifically
 * `.reduce(` and other aggregation patterns that would mean a financial
 * total was built up client-side instead of read from a single API field.
 */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const DIR = join(__dirname, "..");
const FILES = readdirSync(DIR)
  .filter((f) => (f.endsWith(".ts") || f.endsWith(".tsx")) && !f.includes(".test."))
  .map((f) => join(DIR, f));

/** Strips // line comments so an explanatory comment describing what NOT
 * to do (this file has several) can't itself trip a pattern check meant
 * for real code. */
function stripComments(source: string): string {
  return source.split("\n").map((line) => line.replace(/\/\/.*$/, "")).join("\n");
}

describe("Performance screen: no financial calculation in React", () => {
  it("never uses .reduce( to aggregate financial API fields", () => {
    for (const file of FILES) {
      const content = stripComments(readFileSync(file, "utf-8"));
      expect(content, `${file} contains .reduce(`).not.toMatch(/\.reduce\(/);
    }
  });

  it("never sums attribution income sub-fields into a fabricated total", () => {
    for (const file of FILES) {
      const content = stripComments(readFileSync(file, "utf-8"));
      // The three failure modes this guards: adding dividends+distributions
      // (+interest) together, which would be a new figure the backend
      // never computed and handed over as its own field.
      expect(content).not.toMatch(/dividends\s*\+\s*.*distributions/);
      expect(content).not.toMatch(/investment_gain\s*\/\s*denom/); // Modified Dietz math, Phase 4's job
    }
  });

  it("every percentage/dollar figure rendered on screen traces to a named API field, not a local variable built from arithmetic on two or more API fields", () => {
    for (const file of FILES) {
      const content = stripComments(readFileSync(file, "utf-8"));
      // Matches "x + y", "x - y" etc. where both operands look like API
      // field accesses (a.b or a.b.c) -- the actual failure mode sec 2
      // prohibits. Chart coordinate math (xScale(...), index math on plain
      // numbers) does not match this pattern.
      const suspicious = content.match(/\w+\.\w+(\.\w+)?\s*[-+]\s*\w+\.\w+(\.\w+)?/g) ?? [];
      const genuine = suspicious.filter((s) => !s.includes("styles.") && !s.includes("Math."));
      expect(genuine, `${file}: ${JSON.stringify(genuine)}`).toEqual([]);
    }
  });
});
