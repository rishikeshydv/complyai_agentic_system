"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  FileJson2,
  FileText,
  Package,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { calSans } from "@/font/font";
import { apiRequest } from "@/lib/api";

const actions = [
  "REVIEW",
  "ESCALATE",
  "CLOSE",
  "REQUEST_SAR_DRAFT",
  "APPROVE_SAR",
  "MARK_SAR_FILED",
] as const;

const actionLabels: Record<(typeof actions)[number], string> = {
  REVIEW: "Mark Reviewed",
  ESCALATE: "Escalate",
  CLOSE: "Close Case",
  REQUEST_SAR_DRAFT: "Save SAR Draft",
  APPROVE_SAR: "Approve SAR",
  MARK_SAR_FILED: "Mark SAR Filed",
};

const actionDescriptions: Record<(typeof actions)[number], string> = {
  REVIEW: "Confirms initial analyst review is complete.",
  ESCALATE: "Routes this case for deeper investigation.",
  CLOSE: "Final disposition with no further action required.",
  REQUEST_SAR_DRAFT: "Stores the edited SAR narrative in the case file.",
  APPROVE_SAR: "Approves the current SAR narrative for filing.",
  MARK_SAR_FILED: "Marks the SAR as filed for final audit tracking.",
};

type CaseRecord = {
  case_id: string;
  alert_id: string;
  status: string;
  casefile_json: any;
  created_at: string;
  updated_at: string;
  integrity?: {
    export_id?: string;
    source_payload_sha256?: string;
  };
};

function toneFromStatus(status: string): "neutral" | "good" | "warn" | "bad" {
  if (["READY", "READY_FOR_REVIEW", "REVIEWED", "CLOSED", "SAR_FILED"].includes(status)) return "good";
  if (["ESCALATED", "SAR_DRAFTED", "SAR_APPROVED"].includes(status)) return "warn";
  if (status === "ERROR") return "bad";
  return "neutral";
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "NOT PROVIDED";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatDate(value: string): string {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return "NOT PROVIDED";
  return timestamp.toLocaleString();
}

function formatStatus(value: string): string {
  return value.replace(/_/g, " ");
}

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<CaseRecord | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sarDraft, setSarDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activeAction, setActiveAction] = useState<(typeof actions)[number] | null>(null);
  const [downloading, setDownloading] = useState(false);

  async function loadCase() {
    setLoading(true);
    setLoadError(null);
    setActionError(null);
    try {
      const record = await apiRequest<CaseRecord>(`/v1/cases/${params.id}`);
      setData(record);
      setSarDraft(record.casefile_json?.sar_draft?.narrative_draft || "");
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to load case");
    } finally {
      setLoading(false);
    }
  }

  async function runAction(action: (typeof actions)[number], notes?: string) {
    if (!data) return;
    setSubmitting(true);
    setActiveAction(action);
    setActionError(null);
    try {
      const updated = await apiRequest<CaseRecord>(`/v1/cases/${data.case_id}/actions`, {
        method: "POST",
        body: JSON.stringify({
          action,
          actor_id: "web-user",
          notes,
          sar_narrative: action === "REQUEST_SAR_DRAFT" ? sarDraft : undefined,
        }),
      });
      setData(updated);
      setSarDraft(updated.casefile_json?.sar_draft?.narrative_draft || sarDraft);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setSubmitting(false);
      setActiveAction(null);
    }
  }

  async function downloadMarkdown() {
    if (!data) return;
    setDownloading(true);
    setActionError(null);
    try {
      const markdown = await apiRequest<string>(`/v1/cases/${data.case_id}/export/markdown`);
      const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${data.alert_id || data.case_id}.md`;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to export markdown");
    } finally {
      setDownloading(false);
    }
  }

  useEffect(() => {
    void loadCase();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  if (loading) {
    return (
      <main className="container space-y-4 py-8">
        <Card className="space-y-3 p-6">
          <div className="h-5 w-36 animate-pulse rounded bg-black/10" />
          <div className="h-10 w-2/3 animate-pulse rounded bg-black/10" />
          <div className="h-4 w-1/3 animate-pulse rounded bg-black/10" />
        </Card>
        <div className="grid gap-4 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, idx) => (
            <Card key={idx} className="h-28 animate-pulse bg-black/[0.04]" />
          ))}
        </div>
      </main>
    );
  }

  if (loadError || !data) {
    return (
      <main className="container py-8">
        <Card className="space-y-4 border-red-200 bg-red-50 p-6">
          <div className="flex items-start gap-2 text-red-700">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p>{loadError || "Case not found"}</p>
          </div>
          <Button onClick={() => router.push("/cases")} className="w-fit">
            Back to Cases
          </Button>
        </Card>
      </main>
    );
  }

  const caseJson = data.casefile_json;
  const summary = caseJson?.executive_summary;
  const trigger = caseJson?.trigger_explanation;
  const customer = caseJson?.customer_context;
  const transaction = caseJson?.transaction_evidence;
  const timeline = caseJson?.timeline_and_audit?.events || [];
  const ruleRows = caseJson?.rule_evaluation_table?.rows || [];
  const citations = caseJson?.regulatory_traceability?.citations || [];

  return (
    <main className="space-y-5 p-6 md:p-10 xl:p-20">
      <section className="relative overflow-hidden rounded-3xl border border-black/10 bg-white/90 p-6 shadow-sm md:p-7">
        <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-emerald-200/40 blur-3xl" />
        <div className="pointer-events-none absolute -left-10 bottom-0 h-36 w-36 rounded-full bg-sky-200/40 blur-2xl" />
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <Link href="/cases" className="inline-flex items-center gap-1.5 text-sm text-sky-700 hover:underline">
              <ArrowLeft className="h-4 w-4" />
              Back to cases
            </Link>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700/90">Case Detail</p>
            <h1 className={`text-2xl font-bold tracking-tight text-slate-900 md:text-3xl ${calSans.className}`}>
              Alert {data.alert_id || "NOT PROVIDED"}
            </h1>
            <p className="font-mono text-xs text-black/60">{data.case_id}</p>
            <div className="flex flex-wrap items-center gap-2">
              <Badge text={formatStatus(data.status)} tone={toneFromStatus(data.status)} />
              <span className="text-xs text-black/60">Created {formatDate(data.created_at)}</span>
              <span className="text-xs text-black/60">Updated {formatDate(data.updated_at)}</span>
            </div>
          </div>

          <div className="flex w-full flex-wrap gap-2 sm:w-auto">
            <Button variant="outline" disabled={loading} onClick={() => void loadCase()} className="gap-2">
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </Button>
            <Button variant="outline" disabled={downloading} onClick={() => void downloadMarkdown()} className="gap-2">
              <FileText className="h-4 w-4" />
              {downloading ? "Exporting..." : "Export Markdown"}
            </Button>
            <a href={`/v1/cases/${data.case_id}/export/exam-packet`}>
              <Button variant="outline" className="gap-2">
                <Package className="h-4 w-4" />
                Exam Packet
              </Button>
            </a>
            <a href={`/v1/cases/${data.case_id}/export/json`} target="_blank" rel="noreferrer">
              <Button variant="outline" className="gap-2">
                <FileJson2 className="h-4 w-4" />
                View JSON
              </Button>
            </a>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Card className="space-y-1 border-emerald-100 p-4">
          <p className="text-xs uppercase tracking-wide text-black/50">Disposition</p>
          <p className="text-lg font-semibold text-slate-900">{summary?.recommended_disposition || "NOT PROVIDED"}</p>
        </Card>
        <Card className="space-y-1 border-sky-100 p-4">
          <p className="text-xs uppercase tracking-wide text-black/50">Confidence</p>
          <p className="text-lg font-semibold text-slate-900">
            {summary?.confidence === null || summary?.confidence === undefined ? "NOT PROVIDED" : `${Math.round(summary.confidence * 100)}%`}
          </p>
        </Card>
        <Card className="space-y-1 border-indigo-100 p-4">
          <p className="text-xs uppercase tracking-wide text-black/50">Alert Type</p>
          <p className="text-lg font-semibold text-slate-900">{caseJson?.header?.alert_type || "NOT PROVIDED"}</p>
        </Card>
        <Card className="space-y-1 border-amber-100 p-4">
          <p className="text-xs uppercase tracking-wide text-black/50">Case Age</p>
          <p className="text-lg font-semibold text-slate-900">{formatDate(data.created_at)}</p>
        </Card>
      </section>

      {actionError ? (
        <Card className="border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p>{actionError}</p>
          </div>
        </Card>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-12">
        <div className="space-y-5 xl:col-span-8">
          <Card className="space-y-4 p-5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-600" />
              <h2 className="text-lg font-semibold">Executive Summary</h2>
            </div>
            <ul className="space-y-2 text-sm text-slate-800">
              {(summary?.bullets || []).map((bullet: string, idx: number) => (
                <li key={idx} className="rounded-lg bg-slate-50 px-3 py-2">
                  {bullet}
                </li>
              ))}
              {!summary?.bullets?.length ? <li className="text-sm text-black/70">NOT PROVIDED</li> : null}
            </ul>
            <p className="text-xs text-black/60">Evidence pointers: {(summary?.evidence_pointers || []).join(", ") || "NOT PROVIDED"}</p>
          </Card>

          <Card className="space-y-3 p-5">
            <h2 className="text-lg font-semibold">Trigger Explanation</h2>
            <p className="text-sm leading-relaxed text-slate-800">{trigger?.narrative || trigger?.interpretation || "NOT PROVIDED"}</p>
            <p className="text-xs text-black/60">Evidence pointers: {(trigger?.evidence_pointers || []).join(", ") || "NOT PROVIDED"}</p>
          </Card>

          <Card className="space-y-3 p-5">
            <h2 className="text-lg font-semibold">Rule Evaluation</h2>
            <div className="overflow-x-auto rounded-xl border border-black/10">
              <table className="min-w-[860px] text-sm">
                <thead className="bg-slate-50 text-left">
                  <tr className="border-b border-black/10">
                    <th className="px-3 py-2 font-semibold text-slate-700">Field</th>
                    <th className="px-3 py-2 font-semibold text-slate-700">Operator</th>
                    <th className="px-3 py-2 font-semibold text-slate-700">Threshold</th>
                    <th className="px-3 py-2 font-semibold text-slate-700">Actual</th>
                    <th className="px-3 py-2 font-semibold text-slate-700">Window</th>
                    <th className="px-3 py-2 font-semibold text-slate-700">Satisfied</th>
                    <th className="px-3 py-2 font-semibold text-slate-700">Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {ruleRows.map((row: any, idx: number) => (
                    <tr key={idx} className="border-b border-black/5">
                      <td className="px-3 py-2">{row.field || "NOT PROVIDED"}</td>
                      <td className="px-3 py-2">{row.operator || "NOT PROVIDED"}</td>
                      <td className="px-3 py-2">{formatValue(row.threshold)}</td>
                      <td className="px-3 py-2">{formatValue(row.actual)}</td>
                      <td className="px-3 py-2">{row.window_days ?? "NOT PROVIDED"}</td>
                      <td className="px-3 py-2">
                        <Badge tone={row.satisfied ? "good" : "bad"}>{row.satisfied ? "Yes" : "No"}</Badge>
                      </td>
                      <td className="px-3 py-2">{row.evidence_pointer || "NOT PROVIDED"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <section className="grid gap-4 lg:grid-cols-2">
            <Card className="space-y-3 p-5">
              <h2 className="text-lg font-semibold">Customer Context</h2>
              <p className="text-sm text-slate-800">{customer?.summary || "NOT PROVIDED"}</p>
              <div className="space-y-2">
                {(customer?.key_facts || []).map((fact: any, idx: number) => (
                  <div key={idx} className="rounded-lg border border-black/10 bg-slate-50/80 p-3 text-sm">
                    <p className="font-semibold text-slate-800">{fact.label || "NOT PROVIDED"}</p>
                    <p>{formatValue(fact.value)}</p>
                    <p className="text-xs text-black/60">{fact.evidence_pointer || "NOT PROVIDED"}</p>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="space-y-3 p-5">
              <h2 className="text-lg font-semibold">Transaction Evidence</h2>
              <p className="text-sm text-slate-800">{transaction?.summary || "NOT PROVIDED"}</p>
              <div className="space-y-2">
                {(transaction?.key_transactions || []).map((item: any, idx: number) => (
                  <div key={idx} className="rounded-lg border border-black/10 bg-slate-50/80 p-3 text-sm">
                    <p className="font-semibold">{item.transaction_id || "NOT PROVIDED"}</p>
                    <p>{item.description || "NOT PROVIDED"}</p>
                    <p className="text-xs text-black/60">{item.evidence_pointer || "NOT PROVIDED"}</p>
                  </div>
                ))}
              </div>
            </Card>
          </section>

          <Card className="space-y-3 p-5">
            <h2 className="text-lg font-semibold">Regulatory Citations</h2>
            <div className="space-y-2">
              {citations.map((citation: any, idx: number) => (
                <div key={idx} className="rounded-lg border border-black/10 bg-white p-3">
                  <p className="text-sm font-semibold text-slate-800">
                    {citation.citation_id || "NOT PROVIDED"} - {citation.title || "NOT PROVIDED"}
                  </p>
                  <p className="text-xs text-black/60">{citation.jurisdiction || "NOT PROVIDED"}</p>
                  <p className="mt-1 text-sm text-slate-800">{citation.why_relevant || "NOT PROVIDED"}</p>
                  <p className="mt-1 text-xs text-black/60">Evidence: {(citation.evidence_pointers || []).join(", ") || "NOT PROVIDED"}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="space-y-3 p-5">
            <h2 className="text-lg font-semibold">Timeline / Audit</h2>
            <div className="space-y-3 text-sm">
              {timeline.map((event: any, idx: number) => (
                <div key={idx} className="relative rounded-xl border border-black/10 bg-slate-50/70 p-4 pl-8">
                  <span className="absolute left-3 top-5 h-2 w-2 rounded-full bg-emerald-500" />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-slate-800">{event.action || "NOT PROVIDED"}</span>
                    <Badge text={event.actor_type || "SYSTEM"} />
                  </div>
                  <p className="text-black/70">
                    {event.actor_id || "NOT PROVIDED"} at {event.timestamp ? new Date(event.timestamp).toLocaleString() : "NOT PROVIDED"}
                  </p>
                  <p className="text-black/70">{event.notes || "NOT PROVIDED"}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <aside className="space-y-5 xl:sticky xl:top-24 xl:col-span-4 xl:self-start">
          <Card className="space-y-4 p-5">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <h2 className="text-lg font-semibold">Action Center</h2>
            </div>
            <p className="text-sm text-black/70">Run workflow actions and keep the audit timeline fully updated.</p>
            <div className="space-y-2">
              {actions.map((action) => (
                <div key={action} className="space-y-1 rounded-lg border border-black/10 p-2">
                  <Button
                    variant={action === "CLOSE" ? "destructive" : "outline"}
                    className="h-auto w-full justify-start whitespace-normal px-3 py-2 text-left"
                    disabled={submitting}
                    onClick={() => void runAction(action, `Case action ${action}`)}
                  >
                    {activeAction === action ? "Working..." : actionLabels[action]}
                  </Button>
                  <p className="px-1 text-xs text-black/55">{actionDescriptions[action]}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="space-y-3 p-5">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-sky-600" />
              <h2 className="text-lg font-semibold">SAR Draft Editor</h2>
            </div>
            <Textarea
              rows={10}
              value={sarDraft}
              onChange={(event) => setSarDraft(event.target.value)}
              placeholder="Edit SAR narrative draft. Use NOT PROVIDED where evidence is missing."
            />
            <Button
              disabled={submitting}
              onClick={() => void runAction("REQUEST_SAR_DRAFT", "SAR draft edited by analyst")}
              className="w-full"
            >
              {activeAction === "REQUEST_SAR_DRAFT" ? "Saving..." : "Save SAR Draft"}
            </Button>
          </Card>

          <Card className="space-y-3 p-5">
            <h2 className="text-lg font-semibold">Integrity Metadata</h2>
            <div className="space-y-2 text-sm">
              <div className="rounded-lg border border-black/10 bg-slate-50/70 p-3">
                <p className="text-xs uppercase tracking-wide text-black/55">Export ID</p>
                <p className="mt-1 break-all font-mono text-xs text-slate-800">{data.integrity?.export_id || "NOT PROVIDED"}</p>
              </div>
              <div className="rounded-lg border border-black/10 bg-slate-50/70 p-3">
                <p className="text-xs uppercase tracking-wide text-black/55">Payload SHA-256</p>
                <p className="mt-1 break-all font-mono text-xs text-slate-800">{data.integrity?.source_payload_sha256 || "NOT PROVIDED"}</p>
              </div>
              <div className="rounded-lg border border-black/10 bg-slate-50/70 p-3">
                <p className="text-xs uppercase tracking-wide text-black/55">Audit Trace Timestamp</p>
                <p className="mt-1 flex items-center gap-1 text-xs text-slate-800">
                  <CalendarDays className="h-3.5 w-3.5" />
                  {formatDate(data.updated_at)}
                </p>
              </div>
            </div>
          </Card>

          <Card className="space-y-2 p-5">
            <h2 className="text-lg font-semibold">Workflow Quality</h2>
            <div className="space-y-2 text-sm text-slate-800">
              <p className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Evidence-linked traceability retained
              </p>
              <p className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Analyst actions logged in timeline
              </p>
              <p className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Export ready in markdown and JSON
              </p>
            </div>
          </Card>
        </aside>
      </section>
    </main>
  );
}
