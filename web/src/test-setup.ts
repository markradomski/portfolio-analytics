import "@testing-library/jest-dom/vitest";

// jsdom has no matchMedia; components that read prefers-color-scheme
// (useTheme) need a minimal stub. Defaults to light (matches: false).
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}
