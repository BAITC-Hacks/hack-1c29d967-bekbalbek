import { render, screen } from "@testing-library/react";
import { brand, landingCopy, tourTabs } from "../config";
import Landing from "./Landing";

describe("Landing", () => {
  it("should render the brand tagline, nav and product tour from config", () => {
    render(<Landing />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(brand.tagline);
    for (const item of brand.nav) expect(screen.getAllByText(item.label).length).toBeGreaterThan(0);
    expect(screen.getByRole("tab", { name: new RegExp(tourTabs[0].label) })).toBeInTheDocument();
  });

  it("should render section headings and footer from landingCopy", () => {
    render(<Landing />);
    expect(screen.getByRole("heading", { name: landingCopy.tourHeading })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: landingCopy.signature.heading })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: landingCopy.howHeading })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: landingCopy.ctaHeading })).toBeInTheDocument();
    expect(screen.getByText(new RegExp(landingCopy.footer))).toBeInTheDocument();
  });
});
