/**
 * Formatting is presentation only (sec 34, 50): every function here takes
 * the exact string the API sent and returns a display string. None of them
 * round, recalculate, or otherwise alter the underlying figure -- the value
 * a caller reads back out of the DOM must equal the API value to the
 * precision this module declares, never silently drift further.
 *
 * These functions parse the Decimal-as-string once, at the last possible
 * moment, purely to drive Intl formatting -- the parsed number is never
 * stored, compared, or fed into another calculation.
 */

const CURRENCY = new Intl.NumberFormat("en-AU", {
  style: "currency", currency: "AUD", minimumFractionDigits: 2, maximumFractionDigits: 2,
});
const CURRENCY_COMPACT = new Intl.NumberFormat("en-AU", {
  style: "currency", currency: "AUD", notation: "compact", maximumFractionDigits: 1,
});
const PERCENT = new Intl.NumberFormat("en-AU", {
  style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "exceptZero",
});
const PERCENT_PLAIN = new Intl.NumberFormat("en-AU", {
  style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1,
});
const UNITS = new Intl.NumberFormat("en-AU", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
const DATE_SHORT = new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric" });
const DATE_LONG = new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "long", year: "numeric" });

/** $124,582.32 / -$4,200.00. Always shows the sign for a negative value via
 * the standard currency format's own convention; positive values carry no
 * explicit "+" (use formatMoneySigned for that -- gain/loss contexts want it,
 * a plain balance does not). */
export function formatMoney(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return CURRENCY.format(n);
}

/** +$12,431.20 / -$4,200.00 -- explicit sign, for a gain/loss or a flow
 * where "money arrived" vs "money left" must be visually unambiguous even
 * before colour is considered (sec 32: never colour-only encoding). */
export function formatMoneySigned(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return sign + CURRENCY.format(n);
}

/** $124.6k -- for a tight space (a sparkline label, a compact card) where
 * full precision is not the point of the display. Never use this where the
 * exact figure matters. */
export function formatMoneyCompact(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return CURRENCY_COMPACT.format(n);
}

/** The API sends returns as a decimal fraction ("0.184" = 18.4%). +18.4% /
 * -4.8%, sign always shown -- a return's direction is never left implicit. */
export function formatPercentSigned(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return PERCENT.format(n);
}

/** 42.0% -- for a share of something (allocation weight, concentration),
 * where a "+" would be meaningless. */
export function formatPercentPlain(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return PERCENT_PLAIN.format(n);
}

/** 1,284.5200 units -- unit counts carry more decimal places than currency,
 * since a fractional unit is common and rounding it away would misstate a
 * holding, not just its display. */
export function formatUnits(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${UNITS.format(n)} units`;
}

export function formatDate(value: string | null | undefined, style: "short" | "long" = "short"): string {
  if (!value) return "—";
  const d = new Date(value + (value.length === 10 ? "T00:00:00" : ""));
  if (Number.isNaN(d.getTime())) return "—";
  return (style === "long" ? DATE_LONG : DATE_SHORT).format(d);
}

/** True when the value is a positive, negative, or exactly-zero number --
 * used to pick a semantic colour token, never to alter what is displayed. */
const INDEX = new Intl.NumberFormat("en-AU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** 1.68 -- a chained return-index level (Phase 3's return_index), never a
 * currency value and never a percentage: those are different fields
 * (total_return etc.) the backend already computes separately. This
 * formatter exists specifically so a return-index chart never displays a
 * dollar sign against a unitless index number (sec 10). */
export function formatIndex(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return INDEX.format(n);
}

export function sign(value: string | null | undefined): "positive" | "negative" | "neutral" {
  if (value === null || value === undefined) return "neutral";
  const n = Number(value);
  if (!Number.isFinite(n) || n === 0) return "neutral";
  return n > 0 ? "positive" : "negative";
}
