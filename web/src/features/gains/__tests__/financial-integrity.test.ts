/**
 * Sec 34: structurally verifies API -> presentation, never
 * API -> financial calculation -> presentation, for this screen's own
 * source files.
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

describe("Gains screen: no financial calculation in React", () => {
  it("never uses .reduce( to aggregate financial API fields", () => {
    for (const file of FILES) {
      const content = stripComments(readFileSync(file, "utf-8"));
      expect(content, `${file} contains .reduce(`).not.toMatch(/\.reduce\(/);
    }
  });

  it("never imports engine/history calculation modules directly", () => {
    for (const file of FILES) {
      const content = readFileSync(file, "utf-8");
      expect(content).not.toMatch(/from ['"].*\/(src\/engine|src\/history)/);
    }
  });

  it("every percentage/dollar figure traces to a named API field, not arithmetic across two or more API fields", () => {
    for (const file of FILES) {
      const content = stripComments(readFileSync(file, "utf-8"));
      const suspicious = content.match(/\w+\.\w+(\.\w+)?\s*[-+]\s*\w+\.\w+(\.\w+)?/g) ?? [];
      const genuine = suspicious.filter((s) => !s.includes("styles.") && !s.includes("Math."));
      expect(genuine, `${file}: ${JSON.stringify(genuine)}`).toEqual([]);
    }
  });
});
