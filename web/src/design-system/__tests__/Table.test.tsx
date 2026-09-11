import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Table, type Column } from "../Table/Table";

interface Row { code: string; value: number; }
const rows: Row[] = [{ code: "VAS", value: 100 }, { code: "VGS", value: 300 }, { code: "VAF", value: 50 }];
const columns: Column<Row>[] = [
  { key: "code", header: "Security", render: (r) => r.code },
  { key: "value", header: "Value", numeric: true, sortable: true, sortValue: (r) => r.value, render: (r) => String(r.value) },
];

describe("Table", () => {
  it("renders every row", () => {
    render(<Table caption="Holdings" rows={rows} columns={columns} rowKey={(r) => r.code} />);
    expect(screen.getByText("VAS")).toBeInTheDocument();
    expect(screen.getByText("VGS")).toBeInTheDocument();
    expect(screen.getByText("VAF")).toBeInTheDocument();
  });

  it("sorts on header click without altering the underlying values", async () => {
    const user = userEvent.setup();
    render(<Table caption="Holdings" rows={rows} columns={columns} rowKey={(r) => r.code} />);
    await user.click(screen.getByRole("columnheader", { name: /Value/ }));
    const cells = screen.getAllByRole("row").slice(1).map((r) => r.textContent);
    // Descending on first click (see Table.tsx toggleSort default dir).
    expect(cells[0]).toContain("300");
  });

  it("has an accessible caption for screen readers (sec 32)", () => {
    render(<Table caption="Current holdings" rows={rows} columns={columns} rowKey={(r) => r.code} />);
    expect(screen.getByText("Current holdings")).toBeInTheDocument();
  });
});
