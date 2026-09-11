import { Badge } from "../../../design-system/Badge/Badge";
import styles from "./LimitedDataNotice.module.css";

export interface LimitedDataNoticeProps {
  title: string;
  explanation: string;
}

/** "Limited" is a feature, not an error state (sec 10): a value is shown
 * alongside a plain-language reason, never hidden. Used wherever a Metric's
 * data_quality is "limited". */
export function LimitedDataNotice({ title, explanation }: LimitedDataNoticeProps) {
  return (
    <div className={styles.notice}>
      <Badge tone="warning">Limited</Badge>
      <div>
        <p className={styles.title}>{title}</p>
        <p className={styles.explanation}>{explanation}</p>
      </div>
    </div>
  );
}
