import { Component, type ErrorInfo, type ReactNode } from "react";

import { Button } from "../../../design-system/Button/Button";
import styles from "./ErrorBoundary.module.css";

interface Props { children: ReactNode; }
interface State { error: Error | null; }

/**
 * Sec 38: distinguishes a genuine unexpected failure from the API/data
 * states QueryBoundary already handles (loading, unavailable, no data). This
 * only catches a rendering exception -- a bug -- not "the API returned a 503",
 * which is a normal, expected condition surfaced through React Query's own
 * error state instead.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled error in the portfolio UI:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className={styles.wrap} role="alert">
          <p className={styles.title}>Something went wrong displaying this.</p>
          <p className={styles.detail}>{this.state.error.message}</p>
          <Button onClick={() => this.setState({ error: null })}>Try again</Button>
        </div>
      );
    }
    return this.props.children;
  }
}
