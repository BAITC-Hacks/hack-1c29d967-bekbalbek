import { render, screen } from "@testing-library/react";
import { BeforeAfter } from "./StatusCards";

describe("BeforeAfter", () => {
  it("should take the row-label column header from the domain adapter", () => {
    render(<BeforeAfter rows={[{ label: "Поручения", before: "0", after: "3" }]} verification={null} label="Показатель протокола" />);
    expect(screen.getByRole("columnheader", { name: "Показатель протокола" })).toBeInTheDocument();
    expect(screen.getByText("Поручения")).toBeInTheDocument();
  });
});
