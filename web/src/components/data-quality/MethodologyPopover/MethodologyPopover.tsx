import { useId, useState } from "react";

import styles from "./MethodologyPopover.module.css";

export interface MethodologyPopoverProps {
  /** The compact trigger, e.g. "23 quarterly observations". */
  summary: string;
  /** The full explanation, revealed on demand (sec 40: progressive
   * disclosure -- "Volatility 18.4% Limited" by default, the detail only on
   * click). */
  detail: string;
}

/** "How is this calculated?" (sec 48). A disclosure, not a modal -- stays
 * inline, keyboard-operable, closes on a second activation or Escape. */
export function MethodologyPopover({ summary, detail }: MethodologyPopoverProps) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span className={styles.wrap}>
      <button
        type="button"
        className={styles.trigger}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); }}
      >
        {summary}
        <span aria-hidden="true" className={styles.icon}>ⓘ</span>
      </button>
      {open && (
        <span id={id} role="note" className={styles.panel}>
          {detail}
        </span>
      )}
    </span>
  );
}
