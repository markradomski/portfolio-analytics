import { useCallback, useEffect, useState } from "react";

/**
 * Colour-theme preference, layered on top of the token system in
 * `design-system/tokens.css`:
 *
 *   "system" -> no `data-theme` attribute; the CSS `@media
 *               (prefers-color-scheme: dark)` block decides.
 *   "light" / "dark" -> `data-theme` set on <html>, which the token file's
 *               `:root[data-theme=...]` rules honour over the media query.
 *
 * The choice persists in `localStorage` under `theme`. "system" clears the
 * key, so the app goes back to following the OS. Every access is guarded so
 * the hook is safe under jsdom / a private window / disabled storage.
 */
export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

function readStored(): ThemePreference {
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    if (v === "light" || v === "dark") return v;
  } catch {
    /* storage unavailable -- fall through to system */
  }
  return "system";
}

function systemTheme(): ResolvedTheme {
  try {
    return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

/** Apply (or clear) the `data-theme` attribute. Exported so the pre-paint
 * inline script and the hook stay in sync on the attribute name. */
export function applyTheme(preference: ThemePreference): void {
  const root = document.documentElement;
  if (preference === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", preference);
}

export interface UseThemeResult {
  /** What the user picked. */
  preference: ThemePreference;
  /** What is actually showing right now (system resolved to light/dark). */
  resolved: ResolvedTheme;
  setPreference: (next: ThemePreference) => void;
  /** Pick this theme, or return to "system" if it is already the explicit
   * choice -- lets a two-icon switch still reach the follow-the-OS state. */
  toggleTo: (theme: ResolvedTheme) => void;
}

export function useTheme(): UseThemeResult {
  const [preference, setPreferenceState] = useState<ThemePreference>(readStored);
  const [system, setSystem] = useState<ResolvedTheme>(systemTheme);

  // Keep `data-theme` in sync with the preference.
  useEffect(() => {
    applyTheme(preference);
  }, [preference]);

  // Track the OS setting so the switch's highlight follows it while on "system".
  useEffect(() => {
    let mql: MediaQueryList;
    try {
      mql = window.matchMedia(DARK_QUERY);
    } catch {
      return;
    }
    const onChange = () => setSystem(mql.matches ? "dark" : "light");
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    try {
      if (next === "system") window.localStorage.removeItem(STORAGE_KEY);
      else window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* persistence is best-effort */
    }
  }, []);

  const resolved: ResolvedTheme = preference === "system" ? system : preference;

  const toggleTo = useCallback(
    (theme: ResolvedTheme) => {
      setPreference(preference === theme ? "system" : theme);
    },
    [preference, setPreference],
  );

  return { preference, resolved, setPreference, toggleTo };
}
