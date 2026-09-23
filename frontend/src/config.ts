// ============================================================
// ONE FILE TO ALIGN WITH THE HACK CASE.
// Change strings, tabs, scenes and sample cases here.
// Components never hardcode copy.
// ============================================================

export type WorkspaceKind = "table" | "timeline" | "document";

export interface ChangeRow {
  id: string;
  label: string;        // e.g. "Order #4821"
  field: string;        // e.g. "Assigned worker"
  from: string;
  to: string;
  checks: { name: string; status: "pass" | "warn" | "fail" }[];
  why: string;          // plain-language reason
  evidence: { source: string; ref: string; snippet: string };
}

export interface SampleCase {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low";
  owner: string;
  status: "new" | "analyzing" | "proposed" | "applied" | "verified";
  summary: string;
  workspace: WorkspaceKind;
  rows: { id: string; cells: string[] }[];
  columns: string[];
  changes: ChangeRow[];
  events: { key: string; label: string; detail: string; ms: number }[];
}

export const brand = {
  name: "Relay",
  tagline: "The workspace where the agent shows its work.",
  sub: "Relay reads the situation, proposes a fix on the thing you are already looking at, checks it against your rules, and only calls it done when the system says so.",
  ctaPrimary: "Open the demo",
  ctaSecondary: "See how it works",
  announcement: "Built in 48 hours for the hackathon. Swap this line for the case name.",
  nav: [
    { label: "Product", href: "#tour" },
    { label: "How it works", href: "#how" },
    { label: "Evidence", href: "#signature" },
    { label: "Dashboard", href: "#/app" },
  ],
  // Replace with real partner/customer names for the case, or leave empty to hide the strip.
  logos: ["Northwind", "Kaspi Logistics", "Astana Hub", "Halyk", "Beeline", "Air Astana"],
  stats: [
    { value: "3", label: "checks before anything is applied" },
    { value: "1", label: "click from proposal to verified" },
    { value: "0", label: "changes made without a source" },
  ],
};

// Copy for the landing sections that are not part of the hero, tour tabs or how-it-works steps.
export const landingCopy = {
  mockApply: "Apply proposal",
  mockWhy: "Why?",
  tourHeading: "What you see on screen.",
  tourResult: {
    title: "Delivery #4821 — result",
    body: "2 changes applied. Dispatch confirmed the new schedule at 14:07. Ayan S. accepted #4822.",
    evidenceLabel: "Evidence:",
    evidence: "Courier schedule · Ayan S. · row 3",
  },
  signature: {
    heading: "The change happens where you are looking.",
    lead: "Relay never asks you to trust a summary. The proposed change is drawn on the row it affects, with the rule it passed and the record that backs it. Apply is one click, and the green state waits for the system.",
    steps: [
      "Proposed — highlighted on the row",
      "Applying — written to the system of record",
      "Applied — the write succeeded",
      "Verified — read back and matched",
    ],
    phases: { proposed: "Apply proposal", applying: "Applying…", applied: "Applied — verifying", verified: "Verified" },
  },
  howHeading: "Four steps, in that order, every time.",
  ctaHeading: "See it on the case.",
  footer: "Built for the hackathon",
};

// Hero: three auto-rotating scenes. Each is a mini product mock rendered by the Landing.
export const heroScenes = [
  {
    kind: "activity" as const,
    title: "Delivery #4821 is 40 minutes late",
    lines: [
      { label: "Checking available couriers", detail: "resource.lookup · 14 couriers · 112 ms" },
      { label: "Checking deadlines and capacity", detail: "constraint.validate · 3 rules · 48 ms" },
      { label: "Preparing revised assignments", detail: "proposal.create · 2 changes" },
      { label: "Ready to review", detail: "" },
    ],
  },
  {
    kind: "proposal" as const,
    title: "Proposed changes",
    rows: [
      { label: "Order #4821", field: "Courier", from: "Dias K.", to: "Ayan S." },
      { label: "Order #4822", field: "Window", from: "14:00–15:00", to: "15:00–16:00" },
    ],
  },
  {
    kind: "verified" as const,
    title: "Applied and verified",
    lines: ["2 changes written to the schedule", "Confirmed by dispatch system", "Ayan S. notified"],
  },
];

// Product tour tabs. Each tab drives the center mock.
export const tourTabs = [
  {
    id: "queue",
    label: "See what needs attention",
    heading: "One queue, sorted by what will hurt first.",
    body: "Cases arrive from your systems with severity, owner and status already set. Nothing sits in an inbox waiting to be noticed.",
    mock: "table" as WorkspaceKind,
  },
  {
    id: "analyze",
    label: "Watch the agent work",
    heading: "Every step in plain language, details one click away.",
    body: "Progress comes from real backend events, not a fake progress bar. Technical details fold away until you want them.",
    mock: "timeline" as WorkspaceKind,
  },
  {
    id: "propose",
    label: "Review the proposal",
    heading: "Changes appear on the thing you are already looking at.",
    body: "Affected rows light up in place. Open any change to see the old value, the new value, the rule it passed and the record that supports it.",
    mock: "table" as WorkspaceKind,
  },
  {
    id: "verify",
    label: "Apply and verify",
    heading: "Done means the system said so.",
    body: "Applying is one action. The status turns green only after the backend confirms the change was saved.",
    mock: "document" as WorkspaceKind,
  },
];

export const howItWorks = [
  { title: "Propose", body: "The agent reads the case and drafts a change against the live data." },
  { title: "Validate", body: "Every change runs through your constraints: deadlines, capacity, budget, policy." },
  { title: "Execute", body: "You apply. The change is written to the system of record, not a copy." },
  { title: "Verify", body: "Relay reads the state back and marks the case verified only when it matches." },
];

// Sample cases for the dashboard. The first one is the demo path.
export const sampleCases: SampleCase[] = [
  {
    id: "c-4821",
    title: "Delivery #4821 running 40 min late",
    severity: "high",
    owner: "Dispatch",
    status: "new",
    summary: "Courier Dias K. is stuck in traffic on Turan Ave. Two downstream deliveries will miss their windows unless reassigned.",
    workspace: "table",
    columns: ["Order", "Customer", "Window", "Courier", "Status"],
    rows: [
      { id: "4819", cells: ["#4819", "Aigerim T.", "13:00–14:00", "Dias K.", "Delivered"] },
      { id: "4821", cells: ["#4821", "Nurlan B.", "14:00–15:00", "Dias K.", "Late"] },
      { id: "4822", cells: ["#4822", "Saule M.", "14:00–15:00", "Dias K.", "At risk"] },
      { id: "4823", cells: ["#4823", "Timur A.", "15:00–16:00", "Ayan S.", "On track"] },
      { id: "4824", cells: ["#4824", "Dana K.", "16:00–17:00", "Ayan S.", "On track"] },
    ],
    changes: [
      {
        id: "ch-1",
        label: "#4822",
        field: "Courier",
        from: "Dias K.",
        to: "Ayan S.",
        checks: [
          { name: "Capacity", status: "pass" },
          { name: "Window", status: "pass" },
          { name: "Distance", status: "warn" },
        ],
        why: "Ayan S. is 6 minutes from the pickup and has one free slot before #4823.",
        evidence: { source: "Courier schedule", ref: "Ayan S. · row 3", snippet: "14:20 free · next stop #4823 at 15:00" },
      },
      {
        id: "ch-2",
        label: "#4821",
        field: "Window",
        from: "14:00–15:00",
        to: "15:00–16:00",
        checks: [
          { name: "Customer policy", status: "pass" },
          { name: "SLA", status: "pass" },
        ],
        why: "Customer accepts a one-hour shift under the standard delay policy.",
        evidence: { source: "Customer record", ref: "Nurlan B. · preferences", snippet: "Flexible delivery: yes · notify by SMS" },
      },
    ],
    events: [
      { key: "resource.lookup", label: "Checking available couriers", detail: "14 couriers in zone · 112 ms", ms: 900 },
      { key: "constraint.validate", label: "Checking deadlines and capacity", detail: "3 rules · 2 pass · 1 warning", ms: 1100 },
      { key: "proposal.create", label: "Preparing revised assignments", detail: "2 changes · 2 orders affected", ms: 800 },
    ],
  },
  {
    id: "c-inv-77",
    title: "Invoice INV-77 amount does not match PO",
    severity: "medium",
    owner: "Finance",
    status: "new",
    summary: "Supplier invoice shows 1,240,000 KZT; purchase order PO-311 shows 1,180,000 KZT.",
    workspace: "table",
    columns: ["Field", "Invoice", "Purchase order", "Match"],
    rows: [
      { id: "r1", cells: ["Supplier", "TOO Nur Trade", "TOO Nur Trade", "Yes"] },
      { id: "r2", cells: ["Amount", "1,240,000", "1,180,000", "No"] },
      { id: "r3", cells: ["Quantity", "120", "120", "Yes"] },
      { id: "r4", cells: ["Unit price", "10,333", "9,833", "No"] },
    ],
    changes: [
      {
        id: "ch-3",
        label: "Amount",
        field: "Approved amount",
        from: "1,240,000",
        to: "1,180,000",
        checks: [
          { name: "PO match", status: "pass" },
          { name: "Budget", status: "pass" },
        ],
        why: "Unit price on the invoice exceeds the agreed PO price. Approve at PO value and flag the difference to the supplier.",
        evidence: { source: "PO-311.pdf", ref: "page 1 · line 4", snippet: "Unit price: 9,833 KZT · Qty 120" },
      },
    ],
    events: [
      { key: "document.extract", label: "Reading the invoice", detail: "2 pages · 9 fields · confidence high", ms: 1000 },
      { key: "constraint.validate", label: "Comparing with purchase order", detail: "4 fields · 2 mismatches", ms: 900 },
      { key: "proposal.create", label: "Preparing the correction", detail: "1 change", ms: 700 },
    ],
  },
  {
    id: "c-done-1",
    title: "Warehouse B restock for SKU 2210",
    severity: "low",
    owner: "Inventory",
    status: "verified",
    summary: "Restock order placed and confirmed by the supplier portal.",
    workspace: "table",
    columns: ["SKU", "On hand", "Reorder point", "Ordered"],
    rows: [{ id: "s1", cells: ["2210", "14", "40", "120"] }],
    changes: [],
    events: [],
  },
];
