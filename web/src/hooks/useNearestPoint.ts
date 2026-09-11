import { useCallback, useMemo, useState } from "react";
import * as d3 from "d3";

/**
 * The shared hover/crosshair convention every time-series chart uses (sec
 * 36): move the pointer, find the nearest data point by x position via
 * d3.bisector, expose it as React state. Every chart that needs "hover ->
 * crosshair -> tooltip" wires through this one hook rather than
 * reimplementing pointer math per chart.
 *
 * Step 8 hardening: the same "current point" is also reachable by keyboard
 * -- ArrowLeft/ArrowRight/Home/End step a focused index through `data`,
 * independent of pointer position, so a chart's tooltip/crosshair is not
 * mouse-only. Keyboard focus and pointer hover are mutually exclusive: the
 * one used most recently wins, matching how a sighted mouse user and a
 * keyboard user each expect the point under them.
 */
export function useNearestPoint<T>(data: T[], xAccessor: (d: T) => Date, xScale: d3.ScaleTime<number, number>) {
  const [pointerHovered, setPointerHovered] = useState<T | null>(null);
  const [focusedIndex, setFocusedIndex] = useState<number | null>(null);
  const bisect = useMemo(() => d3.bisector(xAccessor).left, [xAccessor]);

  const onPointerMove = useCallback(
    (event: React.PointerEvent<SVGElement>) => {
      // Bug fix: this used to measure from the outer <svg>'s bounding rect,
      // but xScale's range is [0, innerWidth] -- the coordinate space of
      // the chart's own plot area, which starts MARGIN.left/MARGIN.top
      // inside the outer svg (the `<g transform="translate(...)">` every
      // chart wraps its plot in). Measuring from the outer svg left the
      // crosshair/tooltip consistently offset from the actual pointer
      // position by that margin. `currentTarget` here is always the
      // transparent interaction <rect> itself, which exactly spans the
      // plot area -- its own bounding rect is already in the right frame.
      const rect = event.currentTarget.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const date = xScale.invert(x);
      const index = bisect(data, date, 1);
      const a = data[index - 1];
      const b = data[index];
      setFocusedIndex(null); // pointer interaction supersedes a prior keyboard focus
      if (!a) { setPointerHovered(b ?? null); return; }
      if (!b) { setPointerHovered(a); return; }
      const nearest = date.getTime() - xAccessor(a).getTime() > xAccessor(b).getTime() - date.getTime() ? b : a;
      setPointerHovered(nearest);
    },
    [data, xScale, bisect, xAccessor],
  );

  const onPointerLeave = useCallback(() => setPointerHovered(null), []);

  const onFocus = useCallback(() => {
    setFocusedIndex((i) => i ?? (data.length ? 0 : null));
  }, [data.length]);

  const onBlur = useCallback(() => setFocusedIndex(null), []);

  const onKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (!data.length) return;
      if (event.key === "ArrowRight") {
        event.preventDefault();
        setFocusedIndex((i) => Math.min((i ?? -1) + 1, data.length - 1));
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        setFocusedIndex((i) => Math.max((i ?? data.length) - 1, 0));
      } else if (event.key === "Home") {
        event.preventDefault();
        setFocusedIndex(0);
      } else if (event.key === "End") {
        event.preventDefault();
        setFocusedIndex(data.length - 1);
      }
    },
    [data.length],
  );

  const hovered = focusedIndex !== null ? (data[focusedIndex] ?? null) : pointerHovered;

  return {
    hovered, onPointerMove, onPointerLeave,
    /** Wire these three onto the same interactive element as onPointerMove
     * (typically a transparent overlay <rect>) to make it keyboard-operable
     * -- give that element `tabIndex={0}` too. Unused by a chart that has
     * not yet been wired for keyboard access; adding them is additive and
     * does not change that chart's current (mouse-only) behaviour. */
    onFocus, onBlur, onKeyDown,
    isKeyboardActive: focusedIndex !== null,
  };
}
