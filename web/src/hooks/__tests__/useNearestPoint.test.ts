/**
 * Regression test: every chart using this hook renders its interactive
 * overlay <rect> inside a `<g transform="translate(MARGIN.left,
 * MARGIN.top)">` -- so the overlay's own on-screen left edge sits
 * MARGIN.left inside the outer <svg>. `onPointerMove` used to measure the
 * pointer position from the *outer svg's* bounding rect, which is exactly
 * MARGIN.left too far left relative to what `xScale` expects (its range
 * starts at 0 at the plot area's own left edge, not the svg's). That
 * consistently misaligned the crosshair/tooltip from the actual mouse
 * position by that margin -- reported live and reproduced here by giving
 * the overlay and the outer svg two different bounding rects, the way
 * they always differ in a real chart.
 */
import { act, renderHook } from "@testing-library/react";
import * as d3 from "d3";
import { describe, expect, it } from "vitest";

import { useNearestPoint } from "../useNearestPoint";

interface Point { date: Date; label: string; }

const data: Point[] = [
  { date: new Date("2024-01-01"), label: "a" },
  { date: new Date("2024-01-02"), label: "b" },
  { date: new Date("2024-01-03"), label: "c" },
];

// innerWidth = 100 (matches xScale's range below); MARGIN.left = 64, the
// same value every real chart in this app uses.
const MARGIN_LEFT = 64;
const xScale = d3.scaleTime().domain([data[0].date, data[2].date]).range([0, 100]);

function makeEvent(clientX: number): React.PointerEvent<SVGElement> {
  const overlayRect = { left: MARGIN_LEFT, top: 0 } as DOMRect;
  const svgRect = { left: 0, top: 0 } as DOMRect;
  const overlay = { getBoundingClientRect: () => overlayRect } as unknown as SVGElement;
  const outerSvg = { getBoundingClientRect: () => svgRect } as unknown as SVGSVGElement;
  return {
    clientX,
    currentTarget: Object.assign(overlay, { ownerSVGElement: outerSvg }),
  } as unknown as React.PointerEvent<SVGElement>;
}

describe("useNearestPoint: pointer coordinate frame", () => {
  it("measures from the interactive overlay's own bounding rect, not the outer svg's, so the crosshair lands under the actual cursor", () => {
    const { result } = renderHook(() => useNearestPoint(data, (d) => d.date, xScale));

    // Cursor sits at the overlay's own x=0 (i.e. clientX === overlay.left,
    // MARGIN_LEFT pixels right of the outer svg's left edge) -- this must
    // resolve to the first data point, not one shifted right by the margin.
    act(() => { result.current.onPointerMove(makeEvent(MARGIN_LEFT)); });
    expect(result.current.hovered?.label).toBe("a");
  });

  it("resolves a point near the left edge to the nearest (first) point, not one shifted right by the outer svg's margin", () => {
    const { result } = renderHook(() => useNearestPoint(data, (d) => d.date, xScale));

    // Cursor sits 20px into the 100px-wide plot area (nearest to "a" at 0,
    // 20px away, vs "b" at 50, 30px away). The old bug added MARGIN_LEFT
    // (64px) on top of this before inverting, landing at x=84 -- nearer
    // to "c" (100, 16px away) than "b" (50, 34px away) -- resolving to the
    // wrong point entirely rather than merely being imprecise.
    act(() => { result.current.onPointerMove(makeEvent(MARGIN_LEFT + 20)); });
    expect(result.current.hovered?.label).toBe("a");
  });
});
