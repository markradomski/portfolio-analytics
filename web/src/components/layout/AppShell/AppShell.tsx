import { useEffect, type ReactNode } from "react";
import { NavLink, useSearchParams } from "react-router-dom";

import { VanyardLogo } from "../../brand/VanyardLogo/VanyardLogo";
import { isVanyardTheme, type ActiveTheme } from "../../../hooks/useTheme";
import { useThemeContext } from "../../../hooks/ThemeContext";
import { getStoredPeriod } from "../../../lib/periodStorage";
import { ThemeToggle } from "../ThemeToggle/ThemeToggle";
import styles from "./AppShell.module.css";

// Light and Dark share the app's one brand mark (no separate dark-tuned
// icon exists); both Vanyard variants use the cropped ship-tile artwork
// (see VanyardLogo's own provenance note).
const FAVICON_BY_THEME: Record<ActiveTheme, { href: string; type: string }> = {
  light: { href: "/favicon.svg", type: "image/svg+xml" },
  dark: { href: "/favicon.svg", type: "image/svg+xml" },
  vanyard: { href: "/vanyard-favicon.png", type: "image/png" },
  "vanyard-dark": { href: "/vanyard-favicon.png", type: "image/png" },
};

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
    document.title = isVanyardTheme(resolved) ? "Vanyard | Portfolio Analytics" : "Portfolio Analytics";
  }, [resolved]);

  // Same idea for the tab icon, explicit per scheme rather than a single
  // vanyard/not-vanyard branch: Light and Dark share the app's one brand
  // mark (no separate dark-tuned icon exists), Vanyard gets its own ship
  // mark. Reuses the single <link rel="icon"> from index.html rather than
  // adding a second tag.
  useEffect(() => {
    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (!link) return;
    const favicon = FAVICON_BY_THEME[resolved];
    link.type = favicon.type;
    link.href = favicon.href;
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
        {isVanyardTheme(resolved) ? (
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
      </nav>
      <main id="main" className={styles.main} tabIndex={-1}>
        {children}
      </main>
      {/* Sec 24: a subtle, low-priority disclaimer -- always in the DOM,
          only shown at all when Vanyard is active (AppShell.module.css).
          Deliberately a sibling of `.nav`, not a child of it: it used to
          live inside the nav's own flex flow and broke at the mobile
          breakpoint, where nav switches to flex-direction: row (its
          display:none there was also being beaten on specificity by the
          vanyard-scoped display:block rule -- fixed alongside this move,
          see AppShell.module.css). Fixed-positioned so it never
          participates in either layout at all. */}
      <p className={styles.disclaimer}>
        Vanyard is a fictional portfolio analytics demonstration and is not affiliated with Vanguard.
      </p>
    </div>
  );
}
