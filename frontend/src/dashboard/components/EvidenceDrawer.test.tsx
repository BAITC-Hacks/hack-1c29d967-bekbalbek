import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { protokolDomain } from "../../domain/protokol";
import { caseView, proposalRecord } from "../../test/fixtures";
import { EvidenceDrawer } from "./EvidenceDrawer";

const change = protokolDomain.changesFor(proposalRecord.content, proposalRecord.validation, caseView)[1];

function mockClipboard(writeText: (text: string) => Promise<void>) {
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
}

describe("EvidenceDrawer", () => {
  it("should confirm when a reference was copied", async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    const writeText = vi.fn(async () => undefined);
    mockClipboard(writeText);
    render(<EvidenceDrawer change={change} caseView={caseView} domain={protokolDomain} onClose={() => undefined} />);
    await user.click(screen.getAllByRole("button", { name: /copy reference/i })[0]);
    expect(await screen.findByText("Copied")).toBeInTheDocument();
    expect(writeText).toHaveBeenCalledWith("segment:104");
  });

  it("should say when copying failed", async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    mockClipboard(async () => { throw new Error("denied"); });
    render(<EvidenceDrawer change={change} caseView={caseView} domain={protokolDomain} onClose={() => undefined} />);
    await user.click(screen.getAllByRole("button", { name: /copy reference/i })[0]);
    expect(await screen.findByText(/copy failed/i)).toBeInTheDocument();
  });
});
