export interface CrosshairProps {
  x: number;
  height: number;
  y?: number;
}

/** A vertical line at the hovered x position, with an optional dot marking
 * the data point's y value -- the shared visual convention every
 * time-series chart uses on hover (sec 36). Pure presentation: x/y are
 * handed in already computed by the chart's own D3 scales. */
export function Crosshair({ x, height, y }: CrosshairProps) {
  return (
    <g pointerEvents="none">
      <line x1={x} x2={x} y1={0} y2={height} stroke="var(--color-text-muted)" strokeWidth={1} strokeDasharray="2,2" />
      {y !== undefined && (
        <circle cx={x} cy={y} r={4} fill="var(--color-accent)" stroke="var(--color-surface)" strokeWidth={2} />
      )}
    </g>
  );
}
