import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

import styles from "./ChartContainer.module.css";

export interface ChartDimensions {
  width: number;
  height: number;
}

export interface ChartContainerProps {
  height?: number;
  title?: string;
  /** A short, plain-language summary of what the chart shows -- read by
   * screen readers and always present, so the chart's meaning does not
   * depend on being able to see it (sec 32: "charts must have textual
   * representations"). */
  accessibleSummary: string;
  children: (dimensions: ChartDimensions) => ReactNode;
}

/** Owns exactly one thing: measuring available width via ResizeObserver and
 * handing (width, height) to the chart body. All D3 geometry lives in the
 * children render-prop; this component holds no chart-specific state, so it
 * is the one place every chart gets its responsive sizing from (sec 3: React
 * owns composition/state, D3 owns geometry). */
export function ChartContainer({ height = 320, title, accessibleSummary, children }: ChartContainerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Measure synchronously on mount, before first paint -- a
    // ResizeObserver's first callback fires a frame *later*, which used to
    // leave the chart body unrendered for that frame (and indefinitely in
    // an environment where the observer callback is throttled or the
    // element was briefly 0-width when the observer attached). Fall back to
    // `clientWidth` when `contentRect` reports 0 but the box has real
    // layout, so a chart never renders as an empty container.
    const measure = (candidate: number) => {
      const w = candidate || el.clientWidth || el.getBoundingClientRect().width;
      if (w > 0) setWidth(w);
    };
    measure(el.getBoundingClientRect().width);

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) measure(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <figure className={styles.figure}>
      {title && <figcaption className={styles.title}>{title}</figcaption>}
      <div ref={ref} className={styles.canvas} style={{ height }}>
        {width > 0 && children({ width, height })}
      </div>
      <p className={styles.srOnly}>{accessibleSummary}</p>
    </figure>
  );
}
