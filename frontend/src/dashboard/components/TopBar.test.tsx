import { render, screen } from "@testing-library/react";
import { createFakeApi } from "../../test/fakeApi";
import { TopBar } from "./TopBar";
const controls = { dark: false, onToggleTheme: vi.fn(), onReset: vi.fn(), resetting: false, toast: null };
describe("network and model status", () => {
  it("should show the blocked attempt count and identify scripted runs", async () => {
    const health = await createFakeApi().api.health();
    render(<TopBar {...controls} health={{ ...health, provenance: { enabled: true, blocked_external_connections: 4 } }} />);
    expect(screen.getByText("Заблокировано: 4")).toBeInTheDocument();
    expect(screen.getByText("Демонстрационный режим")).toBeInTheDocument();
    expect(screen.queryByText(/no API key/)).not.toBeInTheDocument();
  });
  it("should not claim network protection when the guard is disabled", async () => {
    const health = await createFakeApi().api.health();
    render(<TopBar {...controls} health={{ ...health, models_present: false, provenance: { enabled: false, blocked_external_connections: 0 } }} />);
    expect(screen.getByText("Защита сети выключена")).toBeInTheDocument();
    expect(screen.getByText("Модели не установлены")).toBeInTheDocument();
    expect(screen.queryByText("Защита сети включена")).not.toBeInTheDocument();
  });
});
