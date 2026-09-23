import { parseRoute, routeHash } from "./route";

describe("route", () => {
  it("should parse run and example hashes and fall back to none", () => {
    expect(parseRoute("#/app/run/run-3")).toEqual({ kind: "run", id: "run-3" });
    expect(parseRoute("#/app/example/week-plan")).toEqual({ kind: "example", id: "week-plan" });
    expect(parseRoute("#/app")).toEqual({ kind: "none" });
    expect(parseRoute("")).toEqual({ kind: "none" });
  });

  it("should round-trip ids that need escaping", () => {
    const route = { kind: "run", id: "run/with space" } as const;
    expect(parseRoute(routeHash(route))).toEqual(route);
    expect(routeHash({ kind: "none" })).toBe("#/app");
  });
});
