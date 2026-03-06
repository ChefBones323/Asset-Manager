import { jsPDF } from "jspdf";
import { socialApi } from "@/services/api";
import { useEventStore } from "@/store/eventStore";

type ExportFormat = "pdf" | "csv" | "json";

function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function downloadPDF(doc: jsPDF, filename: string): void {
  doc.save(filename);
}

function createPDFDoc(title: string): jsPDF {
  const doc = new jsPDF();
  doc.setFontSize(18);
  doc.text(title, 14, 20);
  doc.setFontSize(10);
  doc.text(`Generated: ${new Date().toISOString()}`, 14, 28);
  doc.setFontSize(10);
  return doc;
}

function arrayToCSV(headers: string[], rows: string[][]): string {
  const escape = (v: string) => `"${String(v).replace(/"/g, '""')}"`;
  const lines = [headers.map(escape).join(",")];
  for (const row of rows) {
    lines.push(row.map(escape).join(","));
  }
  return lines.join("\n");
}

export async function printGovernanceReport(format: ExportFormat = "pdf"): Promise<void> {
  let proposals: any[] = [];
  try {
    proposals = await socialApi.getGovernanceProposals();
  } catch { proposals = []; }

  let policiesData: any = { policies: [], active_count: 0 };
  try {
    policiesData = await socialApi.getFeedPolicies();
  } catch {}

  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");

  if (format === "json") {
    const data = { generated: new Date().toISOString(), proposals, policies: policiesData.policies, active_policies: policiesData.active_count };
    downloadFile(JSON.stringify(data, null, 2), `governance-report-${timestamp}.json`, "application/json");
    return;
  }

  if (format === "csv") {
    const headers = ["Proposal ID", "Title", "Type", "Domain", "Status", "Votes For", "Votes Against"];
    const rows = proposals.map((p: any) => [p.proposal_id, p.title || "", p.proposal_type, p.domain, p.status, String(p.votes_for ?? 0), String(p.votes_against ?? 0)]);
    downloadFile(arrayToCSV(headers, rows), `governance-report-${timestamp}.csv`, "text/csv");
    return;
  }

  const doc = createPDFDoc("Governance Report");
  let y = 36;
  doc.setFontSize(12);
  doc.text("Proposal Summary", 14, y); y += 8;
  doc.setFontSize(9);
  doc.text(`Total: ${proposals.length}  |  Active Policies: ${policiesData.active_count}`, 14, y); y += 10;

  for (const p of proposals.slice(0, 20)) {
    if (y > 270) { doc.addPage(); y = 20; }
    doc.setFontSize(9);
    doc.text(`[${p.status?.toUpperCase()}] ${p.title || p.proposal_id.slice(0, 12)}`, 14, y); y += 5;
    doc.setFontSize(8);
    doc.text(`Type: ${p.proposal_type}  |  Domain: ${p.domain}  |  Votes: ${p.total_votes ?? 0}`, 20, y); y += 7;
  }

  downloadPDF(doc, `governance-report-${timestamp}.pdf`);
}

export async function printFeedSnapshot(format: ExportFormat = "pdf"): Promise<void> {
  const events = useEventStore.getState().events;
  const feedEvents = events.filter((e) => e.domain === "content");
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");

  if (format === "json") {
    downloadFile(JSON.stringify({ generated: new Date().toISOString(), feed_events: feedEvents, total: feedEvents.length }, null, 2), `feed-snapshot-${timestamp}.json`, "application/json");
    return;
  }

  if (format === "csv") {
    const headers = ["Event ID", "Type", "Actor", "Timestamp", "Content Preview"];
    const rows = feedEvents.map((e) => [e.event_id, e.event_type, e.actor_id, e.timestamp, String(e.payload.content || "").slice(0, 100)]);
    downloadFile(arrayToCSV(headers, rows), `feed-snapshot-${timestamp}.csv`, "text/csv");
    return;
  }

  const doc = createPDFDoc("Feed Snapshot Report");
  let y = 36;
  doc.setFontSize(12);
  doc.text("Civic Feed Snapshot", 14, y); y += 8;
  doc.setFontSize(9);
  doc.text(`Total feed events: ${feedEvents.length}`, 14, y); y += 10;

  for (const e of feedEvents.slice(0, 30)) {
    if (y > 270) { doc.addPage(); y = 20; }
    doc.setFontSize(9);
    doc.text(`${e.event_type} — ${e.actor_id.slice(0, 12)}`, 14, y); y += 5;
    doc.setFontSize(8);
    const preview = String(e.payload.content || "").slice(0, 80);
    if (preview) { doc.text(preview, 20, y); y += 5; }
    doc.text(e.timestamp, 20, y); y += 7;
  }

  downloadPDF(doc, `feed-snapshot-${timestamp}.pdf`);
}

export async function printTrustGraph(format: ExportFormat = "pdf"): Promise<void> {
  const events = useEventStore.getState().events;
  const trustEvents = events.filter((e) => e.domain === "trust");
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");

  const trustMap = new Map<string, number>();
  for (const e of trustEvents) {
    if (e.payload.trust_score !== undefined) {
      trustMap.set(e.actor_id, e.payload.trust_score as number);
    }
  }
  const sorted = Array.from(trustMap.entries()).sort((a, b) => b[1] - a[1]);

  if (format === "json") {
    downloadFile(JSON.stringify({ generated: new Date().toISOString(), trust_events: trustEvents.length, trust_profiles: sorted.map(([id, score]) => ({ user_id: id, score })) }, null, 2), `trust-graph-${timestamp}.json`, "application/json");
    return;
  }

  if (format === "csv") {
    const headers = ["User ID", "Trust Score", "Events"];
    const rows = sorted.map(([id, score]) => [id, String(score), String(trustEvents.filter((e) => e.actor_id === id).length)]);
    downloadFile(arrayToCSV(headers, rows), `trust-graph-${timestamp}.csv`, "text/csv");
    return;
  }

  const doc = createPDFDoc("Trust Graph Analysis Report");
  let y = 36;
  doc.setFontSize(12);
  doc.text("Trust Network Analysis", 14, y); y += 8;
  doc.setFontSize(9);
  doc.text(`Trust events: ${trustEvents.length}  |  Unique actors: ${trustMap.size}`, 14, y); y += 10;
  doc.text("Top Trusted Actors:", 14, y); y += 7;

  for (const [id, score] of sorted.slice(0, 20)) {
    if (y > 270) { doc.addPage(); y = 20; }
    doc.text(`  ${id.slice(0, 16)}...  Score: ${score}`, 14, y); y += 6;
  }

  downloadPDF(doc, `trust-graph-${timestamp}.pdf`);
}

export async function printEventLog(format: ExportFormat = "pdf"): Promise<void> {
  let events: any[] = [];
  let total = 0;
  try {
    const result = await socialApi.getEvents({ limit: 200 });
    events = result.events;
    total = result.total;
  } catch {
    events = useEventStore.getState().events;
    total = events.length;
  }

  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");

  if (format === "json") {
    downloadFile(JSON.stringify({ generated: new Date().toISOString(), total, events }, null, 2), `event-log-${timestamp}.json`, "application/json");
    return;
  }

  if (format === "csv") {
    const headers = ["Event ID", "Domain", "Event Type", "Actor ID", "Timestamp", "Payload"];
    const rows = events.map((e: any) => [e.event_id, e.domain, e.event_type, e.actor_id, e.timestamp, JSON.stringify(e.payload)]);
    downloadFile(arrayToCSV(headers, rows), `event-log-${timestamp}.csv`, "text/csv");
    return;
  }

  const doc = createPDFDoc("Event Log Export");
  let y = 36;
  doc.setFontSize(12);
  doc.text("System Event Log", 14, y); y += 8;
  doc.setFontSize(9);
  doc.text(`Total events: ${total}  |  Exported: ${events.length}`, 14, y); y += 10;

  for (const e of events.slice(0, 50)) {
    if (y > 270) { doc.addPage(); y = 20; }
    doc.setFontSize(8);
    doc.text(`[${e.domain}] ${e.event_type}`, 14, y); y += 4;
    doc.text(`  ID: ${e.event_id.slice(0, 20)}  Actor: ${e.actor_id.slice(0, 16)}  ${e.timestamp}`, 14, y); y += 6;
  }

  downloadPDF(doc, `event-log-${timestamp}.pdf`);
}

export async function printConfigurationHistory(format: ExportFormat = "pdf"): Promise<void> {
  const events = useEventStore.getState().events;
  const configEvents = events.filter((e) =>
    e.event_type === "config_changed" ||
    e.event_type === "policy_activated" ||
    e.domain === "feed_policy"
  );
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");

  if (format === "json") {
    downloadFile(JSON.stringify({ generated: new Date().toISOString(), configuration_events: configEvents }, null, 2), `config-history-${timestamp}.json`, "application/json");
    return;
  }

  if (format === "csv") {
    const headers = ["Event ID", "Type", "Domain", "Actor", "Timestamp", "Details"];
    const rows = configEvents.map((e) => [e.event_id, e.event_type, e.domain, e.actor_id, e.timestamp, JSON.stringify(e.payload)]);
    downloadFile(arrayToCSV(headers, rows), `config-history-${timestamp}.csv`, "text/csv");
    return;
  }

  const doc = createPDFDoc("Configuration History Report");
  let y = 36;
  doc.setFontSize(12);
  doc.text("Configuration Change History", 14, y); y += 8;
  doc.setFontSize(9);
  doc.text(`Total changes: ${configEvents.length}`, 14, y); y += 10;

  for (const e of configEvents.slice(0, 30)) {
    if (y > 270) { doc.addPage(); y = 20; }
    doc.setFontSize(9);
    doc.text(`${e.event_type} — ${e.timestamp}`, 14, y); y += 5;
    doc.setFontSize(8);
    doc.text(`Actor: ${e.actor_id}`, 20, y); y += 7;
  }

  downloadPDF(doc, `config-history-${timestamp}.pdf`);
}
