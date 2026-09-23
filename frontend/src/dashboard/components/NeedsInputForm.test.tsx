import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { protokolDomain } from "../../domain/protokol";
import { NeedsInputForm } from "./NeedsInputForm";

describe("NeedsInputForm", () => {
  it("should render one input per missing field and merge the values into the original input", async () => {
    const user = userEvent.setup();
    const onContinue = vi.fn();
    render(
      <NeedsInputForm
        message="Two fields are missing."
        fields={[{ field: "meeting_date", reason: "unknown" }, { field: "language", reason: "unknown" }]}
        input={{ notes: "keep" }}
        domain={protokolDomain}
        onContinue={onContinue}
      />,
    );
    await user.type(screen.getByLabelText("meeting_date"), "2026-09-23");
    await user.type(screen.getByLabelText("language"), "ru");
    await user.click(screen.getByRole("button", { name: /продолжить/i }));
    expect(onContinue).toHaveBeenCalledWith({ notes: "keep", meeting_date: "2026-09-23", language: "ru" });
  });

  it("should keep continue disabled until every field has a value", () => {
    render(<NeedsInputForm message="m" fields={[{ field: "meeting_date", reason: "r" }]} input={{}} domain={protokolDomain} onContinue={vi.fn()} />);
    expect(screen.getByRole("button", { name: /продолжить/i })).toBeDisabled();
  });
});
