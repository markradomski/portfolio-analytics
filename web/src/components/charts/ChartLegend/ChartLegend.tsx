import styles from "./ChartLegend.module.css";

export interface ChartLegendItem {
  label: string;
  /** A CSS colour value (a `var(--...)` token, never a literal hex --
   * this must exactly match the colour the chart itself paints that
   * series in, so the legend never drifts out of sync with what's drawn). */
  color: string;
  /** "line" for a stroked series, "area" for a filled region -- the swatch
   * shape follows the series' own visual treatment rather than always
   * being a plain square, so a reference line and a fill are
   * distinguishable in the legend the same way they are in the chart. */
  shape?: "line" | "area";
  /** The fill-opacity the chart itself paints this series at (default 1)
   * -- so a translucent area's swatch reads at the same intensity as the
   * region it labels, not a fully saturated colour the chart never
   * actually shows. */
  opacity?: number;
}

export interface ChartLegendProps {
  items: ChartLegendItem[];
}

/**
 * A persistent, hover-independent colour key (never a tooltip-only
 * affordance) -- every multi-series chart in this app that isn't
 * self-explanatory from its axis labels alone should render one of these
 * rather than relying on a viewer to guess what each line/fill means.
 * Wraps naturally on narrow screens; unlike the period-selector Tabs
 * (which deliberately scrolls instead of wrapping, since reordering tabs
 * mid-strip would be confusing), a legend reading top-to-bottom across two
 * lines is not a usability problem.
 */
export function ChartLegend({ items }: ChartLegendProps) {
  return (
    <ul className={styles.list} aria-label="Chart legend">
      {items.map((item) => (
        <li key={item.label} className={styles.item}>
          <span
            className={item.shape === "line" ? styles.swatchLine : styles.swatchArea}
            style={{ background: item.color, borderColor: item.color, opacity: item.opacity ?? 1 }}
            aria-hidden="true"
          />
          <span className={styles.label}>{item.label}</span>
        </li>
      ))}
    </ul>
  );
}
