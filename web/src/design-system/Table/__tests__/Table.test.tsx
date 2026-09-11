/**
 * Step 8 hardening (sec 14/16): the Table primitive's own accessibility
 * contract -- sortable columns already had aria-sort/keyboard support;
 * this covers the `onRowClick` affordance, which previously reached only
 * a mouse (a bare `onClick` on a `<tr>`, no `tabIndex`, no keyboard
 * handler).
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Table, type Column } from "../Table";

interface Row { id: string; label: string; }
const rows: Row[] = [{ id: "a", label: "Row A" }, { id: "b", label: "Row B" }];
const columns: Column<Row>[] = [{ key: "label", header: "Label", render: (r) => r.label }];

describe("Table: sorting", () => {
  it("toggles aria-sort and reorders rows when a sortable header is activated", async () => {
    const numericColumns: Column<Row & { n: number }>[] = [
      { key: "n", header: "N", sortable: true, sortValue: (r) => r.n, render: (r) => String(r.n) },
    ];
    const numericRows = [{ id: "a", label: "A", n: 2 }, { id: "b", label: "B", n: 1 }];
    render(<Table columns={numericColumns} rows={numericRows} rowKey={(r) => r.id} caption="t" />);
    const header = screen.getByRole("columnheader", { name: "N" });
    expect(header).toHaveAttribute("aria-sort", "none");
    await userEvent.click(header);
    expect(header).toHaveAttribute("aria-sort", "descending");
  });
});

describe("Table: onRowClick keyboard accessibility", () => {
  it("makes a clickable row reachable by Tab and activatable with Enter", async () => {
    const onRowClick = vi.fn();
    render(<Table columns={columns} rows={rows} rowKey={(r) => r.id} caption="t" onRowClick={onRowClick} />);
    const firstRow = screen.getByText("Row A").closest("tr")!;
    expect(firstRow).toHaveAttribute("tabIndex", "0");

    firstRow.focus();
    expect(firstRow).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });

  it("also activates on Space", async () => {
    const onRowClick = vi.fn();
    render(<Table columns={columns} rows={rows} rowKey={(r) => r.id} caption="t" onRowClick={onRowClick} />);
    screen.getByText("Row A").closest("tr")!.focus();
    await userEvent.keyboard(" ");
    expect(onRowClick).toHaveBeenCalledTimes(1);
  });

  it("leaves a plain row (no onRowClick) out of the tab order, unchanged from before", () => {
    render(<Table columns={columns} rows={rows} rowKey={(r) => r.id} caption="t" />);
    const row = screen.getByText("Row A").closest("tr")!;
    expect(row).not.toHaveAttribute("tabIndex");
  });
});
