import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { ThemeToggle } from "../ThemeToggle/ThemeToggle";
import styles from "./AppShell.module.css";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/performance", label: "Performance" },
  { to: "/holdings", label: "Holdings" },
  { to: "/income", label: "Income" },
  { to: "/gains", label: "Gains" },
  { to: "/contributions", label: "Contributions" },
  { to: "/risk", label: "Risk" },
  { to: "/history", label: "History" },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className={styles.shell}>
      <a href="#main" className={styles.skipLink}>Skip to content</a>
      <ThemeToggle />
      <nav className={styles.nav} aria-label="Primary">
        <p className={styles.brand}>Portfolio</p>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
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
