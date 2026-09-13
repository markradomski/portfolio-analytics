import type { ReactNode } from "react";
import { NavLink, useSearchParams } from "react-router-dom";

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
  // Falls back to the persisted value when the current screen's URL has no
  // "period" param at all (e.g. browsing Holdings, which doesn't carry
  // one) -- so the Overview/Performance nav links don't lose the selection
  // just because the current page happens not to echo it.
  const period = searchParams.get("period") ?? getStoredPeriod();

  return (
    <div className={styles.shell}>
      <a href="#main" className={styles.skipLink}>Skip to content</a>
      <ThemeToggle />
      <nav className={styles.nav} aria-label="Primary">
        <p className={styles.brand}>Portfolio</p>
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
      </nav>
      <main id="main" className={styles.main} tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
