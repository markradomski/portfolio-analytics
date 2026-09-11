import { useId } from "react";

import styles from "./Tabs.module.css";

export interface TabItem {
  value: string;
  label: string;
  disabled?: boolean;
  /** Shown when a period/tab is disabled by API capability (sec 28) --
   * never a silently missing option, always a stated reason. */
  disabledReason?: string;
}

export interface TabsProps {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
  "aria-label": string;
}

/** A minimal tab list, driven entirely by capability data the caller
 * already resolved (never a rule like `if (years < 1)` inside this
 * component -- sec 39). */
export function Tabs({ items, value, onChange, "aria-label": ariaLabel }: TabsProps) {
  const id = useId();
  return (
    <ul className={styles.list} role="tablist" aria-label={ariaLabel}>
      {items.map((item) => (
        <li key={item.value} role="presentation">
          <button
            role="tab"
            id={`${id}-${item.value}`}
            aria-selected={item.value === value}
            aria-disabled={item.disabled}
            title={item.disabled ? item.disabledReason : undefined}
            disabled={item.disabled}
            className={`${styles.tab} ${item.value === value ? styles.tabActive : ""}`}
            onClick={() => onChange(item.value)}
          >
            {item.label}
          </button>
        </li>
      ))}
    </ul>
  );
}
