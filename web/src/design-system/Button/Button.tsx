import type { ButtonHTMLAttributes, ReactNode } from "react";

import styles from "./Button.module.css";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "default" | "small";
  children: ReactNode;
}

/** The single button implementation the app uses -- variant/size are the
 * only axes of visual difference, so nothing downstream reaches for a raw
 * <button> and a hand-rolled className. */
export function Button({ variant = "secondary", size = "default", className, children, ...props }: ButtonProps) {
  const classes = [styles.button, styles[variant], size === "small" ? styles.small : "", className]
    .filter(Boolean)
    .join(" ");
  return (
    <button className={classes} {...props}>
      {children}
    </button>
  );
}
