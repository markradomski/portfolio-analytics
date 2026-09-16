import type { ReactElement } from "react";

import { useThemeContext } from "../../../hooks/ThemeContext";
import { isVanyardTheme } from "../../../hooks/useTheme";
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

/** The supplied Vanyard ship/iceberg artwork, isolated to a transparent-
 * background silhouette (see assets/ship-mask.png's provenance in
 * VanyardLogo) and painted with `background-color: currentColor` through a
 * CSS mask -- so, like the sun/moon marks either side of it, it inherits
 * the button's colour rather than carrying its own fixed burgundy/white. */
function ShipIcon() {
  return <span className={`${styles.icon} ${styles.shipIcon}`} aria-hidden="true" />;
}

const OPTIONS: { theme: "light" | "dark" | "vanyard"; label: string; Icon: () => ReactElement }[] = [
  { theme: "light", label: "Light", Icon: SunIcon },
  { theme: "dark", label: "Dark", Icon: MoonIcon },
  { theme: "vanyard", label: "Vanyard", Icon: ShipIcon },
];

export interface ThemeToggleProps {
  /** Default (false): the fixed top-right switch shown on every page at
   * desktop width. true: the same switch, laid out in normal document flow
   * instead -- for embedding inside the mobile nav overlay (AppShell),
   * which is where <=860px moves it to rather than floating it over a
   * navbar that no longer has room to spare for it. Same component, same
   * logic, only the positioning differs (ThemeToggle.module.css). */
  inline?: boolean;
}

/**
 * A three-mark switch for the colour theme: fixed top-right on every page
 * at desktop width, or inline inside the mobile nav overlay at <=860px
 * (`inline`) -- rendered by `AppShell` either way. The mark matching what
 * is currently shown is highlighted; clicking another switches to it.
 * Clicking the mark that is already the explicit Light/Dark choice returns
 * to "system" -- which, with no OS-following default any more, means
 * Vanyard Dark (see useTheme's `toggleTo`/`resolvePreference`) -- "vanyard"
 * has no such equivalent, so picking it is always a plain explicit
 * selection.
 *
 * The Vanyard mark's pressed state covers both Vanyard variants
 * (`isVanyardTheme`): Vanyard Dark has no mark of its own (it's the
 * default you land on with no explicit choice, not a fourth button), but
 * the switch should still show *some* mark pressed rather than none.
 */
export function ThemeToggle({ inline = false }: ThemeToggleProps = {}) {
  const { preference, resolved, toggleTo } = useThemeContext();

  return (
    <div
      className={`${styles.group} ${inline ? styles.inline : ""}`}
      role="group"
      aria-label="Colour theme"
    >
      {OPTIONS.map(({ theme, label, Icon }) => {
        const active = theme === "vanyard" ? isVanyardTheme(resolved) : resolved === theme;
        const isExplicit = preference === theme;
        const title =
          theme === "vanyard"
            ? "Switch to Vanyard theme"
            : isExplicit
              ? `${label} theme — click to match your system setting`
              : `Switch to ${label.toLowerCase()} theme`;
        return (
          <button
            key={theme}
            type="button"
            className={`${styles.option} ${active ? styles.active : ""}`}
            aria-pressed={active}
            title={title}
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
