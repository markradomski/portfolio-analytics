/**
 * A per-viewer convenience, not a source of truth: the last period the user
 * selected on Overview or Performance, so it survives a detour through a
 * screen that doesn't carry the "period" query param (Holdings, Income,
 * ...) and isn't lost by the time they navigate back. The query param is
 * still the primary mechanism (shareable/bookmarkable, drives the nav
 * links) -- this is only the fallback read when a page loads with no
 * "period" param of its own at all.
 */
const STORAGE_KEY = "portfolio.selectedPeriod";

export function getStoredPeriod(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredPeriod(value: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch {
    // Private browsing / storage disabled -- the URL param still works
    // within a session, it just won't survive a detour with no param.
  }
}
