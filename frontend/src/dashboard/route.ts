export type Route = { kind: "none" } | { kind: "example"; id: string } | { kind: "run"; id: string };

export function parseRoute(hash: string): Route {
  const run = /^#\/app\/run\/([^/?#]+)/.exec(hash);
  if (run) return { kind: "run", id: decodeURIComponent(run[1]) };
  const example = /^#\/app\/example\/([^/?#]+)/.exec(hash);
  if (example) return { kind: "example", id: decodeURIComponent(example[1]) };
  return { kind: "none" };
}

export function routeHash(route: Route): string {
  if (route.kind === "run") return `#/app/run/${encodeURIComponent(route.id)}`;
  if (route.kind === "example") return `#/app/example/${encodeURIComponent(route.id)}`;
  return "#/app";
}
