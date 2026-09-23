import { render, screen } from "@testing-library/react";
import { BeforeAfter } from "./StatusCards";

describe("BeforeAfter", () => {
  it("should take the row-label column header from the domain adapter", () => {
    render(<BeforeAfter rows={[{ label: "Ana Petrova · 2026-09-24", before: "4h of 8h", after: "7h of 8h" }]} verification={null} label="Courier · slot" />);
    expect(screen.getByRole("columnheader", { name: "Courier · slot" })).toBeInTheDocument();
    expect(screen.getByText("Ana Petrova · 2026-09-24")).toBeInTheDocument();
  });
});
