/**
 * The same three-step responsive ladder documented at the top of
 * `tokens.css` (CSS media queries can't read a custom property, so those
 * stay as literal numbers) -- kept here as the single source of truth for
 * the handful of places that need a breakpoint in JS rather than CSS
 * (ChartContainer's height ratio, PortfolioGrowthChart's margins/ticks).
 */
export const BREAKPOINT_TABLET = 768;
export const BREAKPOINT_PHONE = 480;
export const BREAKPOINT_NARROW_PHONE = 390;
