import { useMemo, useState } from "react";

import styles from "./Table.module.css";

export interface Column<T> {
  key: string;
  header: string;
  numeric?: boolean;
  sortable?: boolean;
  render: (row: T) => React.ReactNode;
  sortValue?: (row: T) => number | string;
}

export interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  caption: string;
  onRowClick?: (row: T) => void;
}

/** A precision table (sec 15: "do not replace the table entirely with
 * cards"). Sorting is presentation-only client-side reordering of rows
 * already supplied by the API -- it never recomputes a figure. */
export function Table<T>({ columns, rows, rowKey, caption, onRowClick }: TableProps<T>) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const column = columns.find((c) => c.key === sort.key);
    if (!column?.sortValue) return rows;
    return [...rows].sort((a, b) => {
      const av = column.sortValue!(a);
      const bv = column.sortValue!(b);
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return cmp * sort.dir;
    });
  }, [rows, sort, columns]);

  function toggleSort(column: Column<T>) {
    if (!column.sortable) return;
    setSort((prev) =>
      prev?.key === column.key ? { key: column.key, dir: prev.dir === 1 ? -1 : 1 } : { key: column.key, dir: -1 },
    );
  }

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <caption style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
          {caption}
        </caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={column.numeric ? styles.numeric : undefined}
                onClick={() => toggleSort(column)}
                tabIndex={column.sortable ? 0 : undefined}
                // No role override here: a <th> is already a columnheader in
                // the accessibility tree, and setting role="button" would
                // erase that native semantic -- exactly what sec 32 ("accessible
                // tables") means to protect. aria-sort is the correct ARIA
                // pattern for a sortable header; tabIndex/onKeyDown make it
                // keyboard-operable without changing what it announces as.
                aria-sort={column.sortable ? (sort?.key === column.key ? (sort.dir === 1 ? "ascending" : "descending") : "none") : undefined}
                onKeyDown={(e) => {
                  if (column.sortable && (e.key === "Enter" || e.key === " ")) {
                    e.preventDefault();
                    toggleSort(column);
                  }
                }}
              >
                {column.header}
                {column.sortable && sort?.key === column.key && (
                  <span className={styles.sortIcon} aria-hidden="true">{sort.dir === 1 ? "▲" : "▼"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr
              key={rowKey(row)}
              className={styles.row}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              style={onRowClick ? { cursor: "pointer" } : undefined}
              // Step 8 hardening (sec 14/16): a clickable row must be as
              // keyboard-operable as any other interactive control -- a
              // bare onClick on a <tr> reaches only a mouse. tabIndex/
              // onKeyDown make a row this prop is used on reachable by Tab
              // and activatable with Enter or Space. No role override (same
              // reasoning as the header cells below): a <tr> is already a
              // native "row" in the accessibility tree, and a table's own
              // structural roles matter more here than announcing
              // "button" -- the row's own cell content already reads
              // sensibly. No effect when onRowClick is not passed (every
              // current table caller navigates via a real <Link> inside a
              // cell instead, which is natively keyboard-operable already).
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={
                onRowClick
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onRowClick(row);
                      }
                    }
                  : undefined
              }
            >
              {columns.map((column) => (
                <td key={column.key} className={column.numeric ? styles.numeric : undefined}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
