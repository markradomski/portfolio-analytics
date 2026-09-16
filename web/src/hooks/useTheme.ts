import { useCallback, useEffect, useState } from "react";

/**
 * Colour-theme preference, layered on top of the token system in
 * `design-system/tokens.css`:
 *
 *   "system" -> no explicit choice stored. Resolves to Vanyard Dark (the
 *               app's canonical default presentation), not to the OS
 *               `prefers-color-scheme` -- Vanyard is the brand; "system"
 *               here means "nothing chosen yet", not "follow the OS".
 *   "light" / "dark" / "vanyard" -> `data-theme` set on <html>, which the
 *               token file's `:root[data-theme=...]` rules honour.
 *
 * "vanyard" (the button/preference) is always the existing warm-paper
 * Vanyard Light look, explicitly chosen -- unchanged by the default above.
 * Vanyard Dark is reached two ways: implicitly, as what "system" resolves
 * to, or by clearing/never setting a preference; it has no button of its
 * own in the three-mark ThemeToggle (see its own comment).
 *
 * The choice persists in `localStorage` under `theme`. "system" clears the
 * key. Every access is guarded so the hook is safe under jsdom / a private
 * window / disabled storage.
 */
export type ThemePreference = "light" | "dark" | "vanyard" | "system";
/** What is actually applied to the page right now. "vanyard-dark" is a
 * distinct resolved value from "vanyard" (same `data-theme="vanyard"`
 * attribute, plus `data-vanyard-mode="dark"` -- see `applyTheme`) so every
 * Vanyard-scoped `[data-theme="vanyard"]` style in the app (nav, tabs,
 * tables, tooltips, ...) keeps applying in both, and only the colour tokens
 * themselves need a dark variant. */
export type ActiveTheme = "light" | "dark" | "vanyard" | "vanyard-dark";

const STORAGE_KEY = "theme";

function readStored(): ThemePreference {
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    if (v === "light" || v === "dark" || v === "vanyard") return v;
  } catch {
    /* storage unavailable -- fall through to system */
  }
  return "system";
}

/** No explicit preference resolves to Vanyard Dark -- the canonical default
 * presentation, unconditionally (not OS-dependent). */
function resolvePreference(preference: ThemePreference): ActiveTheme {
  return preference === "system" ? "vanyard-dark" : preference;
}

/** True for both Vanyard variants -- everywhere the app needs to know "is
 * this the Vanyard brand" without caring which luminance. */
export function isVanyardTheme(theme: ActiveTheme): boolean {
  return theme === "vanyard" || theme === "vanyard-dark";
}

/** Apply the resolved theme to the DOM. Exported so the pre-paint inline
 * script (index.html) and the hook stay in sync on the attribute contract. */
export function applyTheme(preference: ThemePreference): void {
  const root = document.documentElement;
  const resolved = resolvePreference(preference);
  if (resolved === "vanyard-dark") {
    root.setAttribute("data-theme", "vanyard");
    root.setAttribute("data-vanyard-mode", "dark");
  } else {
    root.setAttribute("data-theme", resolved);
    root.removeAttribute("data-vanyard-mode");
  }
}

export interface UseThemeResult {
  /** What the user picked. */
  preference: ThemePreference;
  /** What is actually showing right now. */
  resolved: ActiveTheme;
  setPreference: (next: ThemePreference) => void;
  /** Pick this theme -- for "light"/"dark", returns to "system" (Vanyard
   * Dark) if it is already the explicit choice; "vanyard" has no such
   * equivalent, so picking it always just selects it explicitly.
   * "vanyard-dark" is not a selectable target -- it has no button, only
   * ever reached as what "system" resolves to. */
  toggleTo: (theme: "light" | "dark" | "vanyard") => void;
}

export function useTheme(): UseThemeResult {
  const [preference, setPreferenceState] = useState<ThemePreference>(readStored);

  // Keep the DOM in sync with the preference.
  useEffect(() => {
    applyTheme(preference);
  }, [preference]);

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    try {
      if (next === "system") window.localStorage.removeItem(STORAGE_KEY);
      else window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* persistence is best-effort */
    }
  }, []);

  const resolved = resolvePreference(preference);

  const toggleTo = useCallback(
    (theme: "light" | "dark" | "vanyard") => {
      if (theme === "vanyard") {
        setPreference("vanyard");
        return;
      }
      setPreference(preference === theme ? "system" : theme);
    },
    [preference, setPreference],
  );

  return { preference, resolved, setPreference, toggleTo };
}
