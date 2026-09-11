import { Link, useLocation } from "react-router-dom";

import styles from "./NotFoundPage.module.css";

/**
 * Step 8 hardening (sec 4): every unknown route used to render a blank
 * `<main>` -- `Routes` with no matching `Route` renders nothing at all,
 * which looks identical to a stuck loading state. This is the one
 * catch-all `<Route path="*">` in App.tsx, giving a direct navigation to a
 * mistyped or stale URL a real page instead of silence.
 */
export function NotFoundPage() {
  const location = useLocation();
  return (
    <div className={styles.page}>
      <h1>Page not found</h1>
      <p className={styles.description}>
        There's no screen at <code className={styles.path}>{location.pathname}</code>.
      </p>
      <Link to="/" className={styles.link}>← Back to Overview</Link>
    </div>
  );
}
