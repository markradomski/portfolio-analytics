import { useId, useRef, useState, type ReactNode } from "react";

import styles from "./Tooltip.module.css";

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
}

/** A generic hover/focus tooltip -- keyboard accessible (shows on focus, not
 * only hover) since a mouse-only affordance would fail sec 32. Chart
 * tooltips (ChartTooltip) are a separate, position-tracking component built
 * for pointer-driven crosshair interaction; this one is for a static
 * trigger like an info icon or a methodology disclosure. */
export function Tooltip({ content, children }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);

  function place() {
    const rect = ref.current?.getBoundingClientRect();
    if (rect) setPos({ x: rect.left, y: rect.bottom + 6 });
  }

  return (
    <span
      ref={ref}
      className={styles.trigger}
      aria-describedby={open ? id : undefined}
      onMouseEnter={() => { place(); setOpen(true); }}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => { place(); setOpen(true); }}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && (
        <span role="tooltip" id={id} className={styles.panel} style={{ left: pos.x, top: pos.y }}>
          {content}
        </span>
      )}
    </span>
  );
}
