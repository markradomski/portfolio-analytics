import { createContext, useContext, type ReactNode } from "react";

import { useTheme, type UseThemeResult } from "./useTheme";

/**
 * Shares one `useTheme()` instance across the app. Until Vanyard, only
 * `ThemeToggle` ever read the theme; adding a second reader (`AppShell`,
 * for the Vanyard brand swap) exposed that two independent `useTheme()`
 * calls don't see each other's updates -- each owns its own `useState`,
 * synchronised only via `localStorage` and the `data-theme` DOM attribute,
 * neither of which triggers a re-render in a *different* component's own
 * hook instance. A context is the smallest fix: one underlying hook call,
 * every consumer reads the same live value.
 */
const ThemeContext = createContext<UseThemeResult | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useTheme();
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useThemeContext(): UseThemeResult {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useThemeContext must be used within a ThemeProvider");
  return ctx;
}
