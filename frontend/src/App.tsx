import { useEffect, useState } from "react";
import "./styles/tokens.css";
import { api } from "./api/client";
import { protokolDomain } from "./domain/protokol";
import Landing from "./landing/Landing";
import Dashboard from "./dashboard/Dashboard";
import { defaultEventSourceFactory } from "./dashboard/useRun";

// Hash routing so it drops into any Vite app without react-router: "#/" landing, "#/app…" dashboard.
export default function App() {
  const [route, setRoute] = useState(window.location.hash);
  useEffect(() => {
    const onHash = () => setRoute(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route.startsWith("#/app")
    ? <Dashboard api={api} eventSourceFactory={defaultEventSourceFactory} domain={protokolDomain} />
    : <Landing />;
}
