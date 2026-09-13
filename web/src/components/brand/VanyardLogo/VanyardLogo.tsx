import shipTileBurgundy from "./assets/ship-tile-burgundy.png";
import shipTileReversed from "./assets/ship-tile-reversed.png";
import styles from "./VanyardLogo.module.css";

export interface VanyardLogoProps {
  /** "tile" (default): the supplied burgundy rounded-square + white ship
   * artwork, standalone -- suitable for placement on any surface.
   * "reversed": the supplied paper-tile + burgundy-ship artwork, for
   * placement on a burgundy surface (see docs/vanyard-theme.md). */
  variant?: "tile" | "reversed";
  /** Pairs the mark with the "Vanyard" wordmark to its right (the header
   * lockup: [ship tile] Vanyard). Omit for icon-only placements. */
  withWordmark?: boolean;
  /** Adds "SAME PRINCIPLES. MORE INSIGHTS." beneath the wordmark -- only
   * where real space exists (About, footer), never in-nav (sec 2/5). */
  withTagline?: boolean;
  size?: "small" | "medium" | "large";
  className?: string;
}

const TILE_SRC: Record<"tile" | "reversed", string> = {
  tile: shipTileBurgundy,
  reversed: shipTileReversed,
};

/**
 * The Vanyard brand mark: the supplied ship/iceberg artwork (cropped
 * directly from the approved reference images -- see
 * docs/vanyard-theme.md for provenance; not a redrawn approximation).
 * Renders only when consumed by Vanyard-themed chrome; the component
 * itself carries no theme logic, it is simply the asset AppShell swaps in
 * when `data-theme="vanyard"`.
 */
export function VanyardLogo({
  variant = "tile", withWordmark = false, withTagline = false, size = "medium", className,
}: VanyardLogoProps) {
  return (
    <span className={`${styles.lockup} ${className ?? ""}`}>
      <img
        src={TILE_SRC[variant]}
        alt="Vanyard"
        className={`${styles.tile} ${styles[size]}`}
      />
      {withWordmark && (
        <span className={styles.wordmarkGroup}>
          <span className={styles.wordmark}>
            Vanyard<sup className={styles.registered}>®</sup>
          </span>
          {withTagline && <span className={styles.tagline}>Same principles. More insights.</span>}
        </span>
      )}
    </span>
  );
}
