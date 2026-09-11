import { Badge, type BadgeTone } from "../../../design-system/Badge/Badge";
import type { DataQuality } from "../../../api/types";

const TONE: Record<DataQuality, BadgeTone> = {
  actual: "quality-actual",
  calculated: "quality-calculated",
  estimated: "quality-estimated",
  limited: "quality-limited",
  unavailable: "quality-unavailable",
};

const LABEL: Record<DataQuality, string> = {
  actual: "Actual",
  calculated: "Calculated",
  estimated: "Estimated",
  limited: "Limited",
  unavailable: "Unavailable",
};

export interface DataQualityBadgeProps {
  quality: DataQuality;
  /** Overrides the default label -- e.g. "23 quarterly obs." instead of
   * just "Limited", when the caller has that detail to hand. */
  label?: string;
}

/** The one place a DataQuality value becomes a visible badge (sec 40).
 * Every screen that shows a figure with provenance uses this rather than
 * inventing its own colour/label mapping. */
export function DataQualityBadge({ quality, label }: DataQualityBadgeProps) {
  return <Badge tone={TONE[quality]}>{label ?? LABEL[quality]}</Badge>;
}
