import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation, useSearchParams } from "react-router-dom";

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
  const location = useLocation();
  const { resolved } = useThemeContext();
  const [menuOpen, setMenuOpen] = useState(false);
  // Falls back to the persisted value when the current screen's URL has no
  // "period" param at all (e.g. browsing Holdings, which doesn't carry
  // one) -- so the Overview/Performance nav links don't lose the selection
  // just because the current page happens not to echo it.
  const period = searchParams.get("period") ?? getStoredPeriod();

  // The mobile nav overlay must not survive a route change (selecting a
  // destination, or any other navigation) -- close it whenever the path
  // changes rather than relying on each NavLink's own onClick to catch
  // every way the route can change.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Escape closes the overlay; body scroll is locked while it's open and
  // restored the moment it isn't (covers both the close button and this
  // effect's own cleanup on unmount).
  useEffect(() => {
    if (!menuOpen) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [menuOpen]);

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

  // The Vanyard identity (sec 2/13 of the theme spec) is a brand swap, not
  // a second header component -- everything else about the nav (links,
  // destinations, active-state mechanism) is exactly what Light/Dark
  // already use. One element, reused wherever the brand mark appears
  // (desktop sidebar, mobile header) rather than redeclared per site.
  const brand = isVanyardTheme(resolved) ? (
    <VanyardLogo withWordmark size="small" className={styles.vanyardBrand} />
  ) : (
    <p className={styles.brand}>Portfolio</p>
  );

  // NAV_ITEMS is declared once above; this renders it into whichever
  // presentation (desktop sidebar vs. mobile overlay) needs it, so the two
  // never risk drifting into different route lists. `onNavigate` lets the
  // mobile overlay close itself on selection without the desktop sidebar
  // needing to know that concept exists.
  function navLinks(onNavigate?: () => void) {
    return NAV_ITEMS.map((item) => (
      <NavLink
        key={item.to}
        to={item.periodAware && period ? `${item.to}?period=${period}` : item.to}
        end={item.end}
        className={({ isActive }) => `${styles.link} ${isActive ? styles.linkActive : ""}`}
        onClick={onNavigate}
      >
        <span className={styles.linkLabel}>{item.label}</span>
      </NavLink>
    ));
  }

  return (
    <div className={styles.shell}>
      <a href="#main" className={styles.skipLink}>Skip to content</a>
      <ThemeToggle />

      {/* <=860px only (AppShell.module.css): the sidebar's nav/brand are
          hidden entirely at this width, replaced by this compact header
          (brand + hamburger) and the overlay it opens below. */}
      <div className={styles.mobileHeader}>
        {brand}
        <button
          type="button"
          className={styles.hamburger}
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={menuOpen}
          aria-controls="primary-nav-mobile"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className={styles.hamburgerBar} aria-hidden="true" />
          <span className={styles.hamburgerBar} aria-hidden="true" />
          <span className={styles.hamburgerBar} aria-hidden="true" />
        </button>
      </div>

      <nav className={styles.nav} aria-label="Primary">
        {brand}
        {navLinks()}
      </nav>

      {menuOpen && (
        <>
          <div className={styles.backdrop} onClick={() => setMenuOpen(false)} aria-hidden="true" />
          <nav id="primary-nav-mobile" className={styles.mobileNav} aria-label="Primary">
            {navLinks(() => setMenuOpen(false))}
          </nav>
        </>
      )}

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
