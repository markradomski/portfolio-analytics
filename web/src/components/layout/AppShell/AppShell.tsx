import { useEffect, type ReactNode } from "react";
import { NavLink, useSearchParams } from "react-router-dom";

import { VanyardLogo } from "../../brand/VanyardLogo/VanyardLogo";
import { useThemeContext } from "../../../hooks/ThemeContext";
import { getStoredPeriod } from "../../../lib/periodStorage";
import { ThemeToggle } from "../ThemeToggle/ThemeToggle";
import styles from "./AppShell.module.css";

const NAV_ITEMS = [
  // Overview and Performance both read/write the shared "period" query
  // param (see useSelectedPeriod) -- periodAware carries the current
  // selection through the primary nav too, not just the in-page links, so
  // switching screens from the sidebar never silently resets it back to
  // the default.
  { to: "/", label: "Overview", end: true, periodAware: true },
  { to: "/performance", label: "Performance", periodAware: true },
  { to: "/holdings", label: "Holdings" },
  { to: "/income", label: "Income" },
  { to: "/gains", label: "Gains" },
  { to: "/contributions", label: "Contributions" },
  { to: "/risk", label: "Risk" },
  { to: "/history", label: "History" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const [searchParams] = useSearchParams();
  const { resolved } = useThemeContext();
  // Falls back to the persisted value when the current screen's URL has no
  // "period" param at all (e.g. browsing Holdings, which doesn't carry
  // one) -- so the Overview/Performance nav links don't lose the selection
  // just because the current page happens not to echo it.
  const period = searchParams.get("period") ?? getStoredPeriod();

  // Sec 23: an optional, cleanly-scoped browser-title swap -- restores the
  // normal title on unmount/theme change rather than leaving it stuck.
  useEffect(() => {
    document.title = resolved === "vanyard" ? "Vanyard | Portfolio Analytics" : "Portfolio Analytics";
  }, [resolved]);

  return (
    <div className={styles.shell}>
      <a href="#main" className={styles.skipLink}>Skip to content</a>
      <ThemeToggle />
      <nav className={styles.nav} aria-label="Primary">
        {/* The Vanyard identity (sec 2/13 of the theme spec) is a brand
            swap, not a second header component -- everything else about
            this nav (links, destinations, active-state mechanism,
            responsive collapse) is exactly what Light/Dark already use. */}
        {resolved === "vanyard" ? (
          <VanyardLogo withWordmark size="small" className={styles.vanyardBrand} />
        ) : (
          <p className={styles.brand}>Portfolio</p>
        )}
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.periodAware && period ? `${item.to}?period=${period}` : item.to}
            end={item.end}
            className={({ isActive }) => `${styles.link} ${isActive ? styles.linkActive : ""}`}
          >
            {item.label}
          </NavLink>
        ))}
        {/* Sec 24: a subtle, low-priority disclaimer -- always in the DOM,
            only shown at all when Vanyard is active (AppShell.module.css). */}
        <p className={styles.disclaimer}>
          Vanyard is a fictional portfolio analytics demonstration and is not affiliated with Vanguard.
        </p>
      </nav>
      <main id="main" className={styles.main} tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
