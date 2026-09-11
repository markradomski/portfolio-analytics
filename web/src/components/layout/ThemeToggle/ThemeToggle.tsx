import type { ReactElement } from "react";

import { useTheme, type ResolvedTheme } from "../../../hooks/useTheme";
import styles from "./ThemeToggle.module.css";

/** Thin-line sun / crescent-moon marks, drawn from the design token
 * `currentColor` so they inherit the button's text colour in both themes. */
function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" className={styles.icon}>
      <circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <line x1="12" y1="2.5" x2="12" y2="5" />
        <line x1="12" y1="19" x2="12" y2="21.5" />
        <line x1="2.5" y1="12" x2="5" y2="12" />
        <line x1="19" y1="12" x2="21.5" y2="12" />
        <line x1="5.1" y1="5.1" x2="6.9" y2="6.9" />
        <line x1="17.1" y1="17.1" x2="18.9" y2="18.9" />
        <line x1="18.9" y1="5.1" x2="17.1" y2="6.9" />
        <line x1="6.9" y1="17.1" x2="5.1" y2="18.9" />
      </g>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" className={styles.icon}>
      <path
        d="M20 14.5A8 8 0 0 1 9.5 4a7 7 0 1 0 10.5 10.5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const OPTIONS: { theme: ResolvedTheme; label: string; Icon: () => ReactElement }[] = [
  { theme: "light", label: "Light", Icon: SunIcon },
  { theme: "dark", label: "Dark", Icon: MoonIcon },
];

/**
 * A two-mark switch for the colour theme, sitting top-right on every page
 * (rendered once by `AppShell`). The mark matching what is currently shown
 * is highlighted; clicking the other switches to it. Clicking the mark that
 * is already the explicit choice returns to following the OS
 * (`prefers-color-scheme`).
 */
export function ThemeToggle() {
  const { preference, resolved, toggleTo } = useTheme();

  return (
    <div className={styles.group} role="group" aria-label="Colour theme">
      {OPTIONS.map(({ theme, label, Icon }) => {
        const active = resolved === theme;
        const isExplicit = preference === theme;
        return (
          <button
            key={theme}
            type="button"
            className={`${styles.option} ${active ? styles.active : ""}`}
            aria-pressed={active}
            title={
              isExplicit
                ? `${label} theme — click to match your system setting`
                : `Switch to ${label.toLowerCase()} theme`
            }
            onClick={() => toggleTo(theme)}
          >
            <Icon />
            <span className={styles.srOnly}>{label} theme</span>
          </button>
        );
      })}
    </div>
  );
}
