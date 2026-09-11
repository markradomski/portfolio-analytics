import type { ReactNode } from "react";

import styles from "./Card.module.css";

export interface CardProps {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  elevation?: "flat" | "raised";
  children: ReactNode;
  className?: string;
}

export function Card({ title, subtitle, action, elevation = "flat", children, className }: CardProps) {
  return (
    <section className={[styles.card, styles[elevation], className].filter(Boolean).join(" ")}>
      {(title || action) && (
        <header className={styles.header}>
          <div>
            {title && <h3 className={styles.title}>{title}</h3>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
