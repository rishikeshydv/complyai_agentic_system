"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
  Clock3,
  FileCheck2,
  ShieldAlert,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { calSans } from "@/font/font";
import { apiRequest } from "@/lib/api";
import { BankScopeMode, getOrCreateSessionBankId, getStoredBankScope, setStoredBankScope } from "@/lib/sessionBank";

type CaseRecord = {
  case_id: string;
  alert_id: string;
  status: string;
  alert_type?: string;
  casefile_json?: {
    header?: {
      alert_type?: string;
    };
  };
  created_at: string;
  updated_at: string;
};

const statusOptions = [
  "",
  "QUEUED",
  "GENERATING",
  "READY",
  "READY_FOR_REVIEW",
  "REVIEWED",
  "ESCALATED",
  "SAR_DRAFTED",
  "SAR_APPROVED",
  "SAR_FILED",
  "CLOSED",
  "ERROR",
];

function toneFromStatus(status: string): "neutral" | "good" | "warn" | "bad" {
  if (["READY", "READY_FOR_REVIEW", "REVIEWED", "CLOSED", "SAR_FILED"].includes(status)) return "good";
  if (["ESCALATED", "SAR_DRAFTED", "SAR_APPROVED"].includes(status)) return "warn";
  if (status === "ERROR") return "bad";
  return "neutral";
}

function formatDate(value: string): string {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return "NOT PROVIDED";
  return timestamp.toLocaleString();
}

function statusLabel(value: string): string {
  return value.replace(/_/g, " ");
}

export default function CasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [status, setStatus] = useState("");
  const [alertType, setAlertType] = useState("");
  const [sessionBankId, setSessionBankId] = useState("");
  const [bankScope, setBankScope] = useState<BankScopeMode>("session");
  const [loading, setLoading] = useState(true);
  const [demoLoading, setDemoLoading] = useState<"AML" | "SANCTIONS" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);

  const effectiveBankId = useMemo(() => {
    if (bankScope === "all") return null;
    if (bankScope === "demo") return "demo";
    return sessionBankId || null;
  }, [bankScope, sessionBankId]);

  useEffect(() => {
    const bankId = getOrCreateSessionBankId();
    setSessionBankId(bankId);
    setBankScope(getStoredBankScope());
  }, []);

  useEffect(() => {
    setStoredBankScope(bankScope);
  }, [bankScope]);

  const loadCases = useCallback(async () => {
    if (bankScope !== "all" && !effectiveBankId) {
      // Avoid accidentally loading all banks before session bank_id is established.
      setCases([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (effectiveBankId) params.set("bank_id", effectiveBankId);
      if (status) params.set("status", status);
      if (alertType) params.set("alert_type", alertType);
      const query = params.toString();
      const items = await apiRequest<CaseRecord[]>(`/v1/cases${query ? `?${query}` : ""}`);
      setCases(items);
      setLastSyncedAt(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cases");
    } finally {
      setLoading(false);
    }
  }, [alertType, bankScope, effectiveBankId, status]);

  useEffect(() => {
    void loadCases();
    const timer = window.setInterval(() => {
      void loadCases();
    }, 15000);
    return () => window.clearInterval(timer);
  }, [loadCases]);

  const metrics = useMemo(() => {
    return {
      total: cases.length,
      escalated: cases.filter((item) => item.status === "ESCALATED").length,
      sarFlow: cases.filter((item) => ["SAR_DRAFTED", "SAR_APPROVED", "SAR_FILED"].includes(item.status)).length,
      errors: cases.filter((item) => item.status === "ERROR").length,
    };
  }, [cases]);

  const hasFilters = Boolean(status || alertType);

  async function generateDemo(kind: "AML" | "SANCTIONS") {
    const targetBankId = bankScope === "demo" ? "demo" : sessionBankId;
    if (!targetBankId) return;
    setDemoLoading(kind);
    setError(null);
    try {
      const payload = await apiRequest<{ case_id: string }>(`/v1/demo/generate-case`, {
        method: "POST",
        body: JSON.stringify({ bank_id: targetBankId, kind }),
      });
      if (bankScope === "all") setBankScope("session");
      router.push(`/cases/${payload.case_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate demo case");
    } finally {
      setDemoLoading(null);
      void loadCases();
    }
  }

  return (
    <main className="space-y-5 p-6 md:p-10 xl:p-20">
      <section className="relative overflow-hidden rounded-3xl border border-black/10 bg-white/85 p-6 shadow-sm md:p-8">
        <div className="pointer-events-none absolute -right-8 -top-10 h-44 w-44 rounded-full bg-emerald-200/40 blur-3xl" />
        <div className="pointer-events-none absolute -left-8 bottom-0 h-36 w-36 rounded-full bg-sky-200/40 blur-2xl" />
        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700/90">Operations</p>
            <h1 className={`text-3xl font-bold tracking-tight text-slate-900 md:text-4xl ${calSans.className}`}>
              Case Workbench
            </h1>
            <p className="max-w-2xl text-sm text-slate-700 md:text-base">
              Manage generated case files, monitor SAR progression, and move investigations forward with a complete
              audit trail.
            </p>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge tone="neutral">Scope: {bankScope === "all" ? "All banks" : bankScope === "demo" ? "Shared demo" : "This session"}</Badge>
              {effectiveBankId ? <Badge tone="neutral">Bank: {effectiveBankId}</Badge> : <Badge tone="neutral">Bank: All</Badge>}
            </div>
            {hasFilters ? (
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <Badge tone="neutral">Filtered View</Badge>
                {status ? <Badge tone="warn">Status: {statusLabel(status)}</Badge> : null}
                {alertType ? <Badge tone="neutral">Alert: {alertType}</Badge> : null}
              </div>
            ) : null}
          </div>
          <div className="flex w-full flex-wrap gap-2 sm:w-auto">
            <Button variant="outline" onClick={() => void loadCases()} disabled={loading} className="flex-1 sm:flex-none">
              {loading ? "Refreshing..." : "Refresh"}
            </Button>
            <Link href="/playground">
              <Button className="flex-1 sm:flex-none">Open Playground</Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Card className="space-y-2 border-emerald-100 bg-white/90 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-black/55">Total Cases</p>
            <FileCheck2 className="h-4 w-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900">{metrics.total}</p>
          <p className="text-xs text-black/55">All cases in current scope</p>
        </Card>
        <Card className="space-y-2 border-amber-100 bg-white/90 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-black/55">Escalated</p>
            <ShieldAlert className="h-4 w-4 text-amber-600" />
          </div>
          <p className="text-2xl font-bold text-amber-700">{metrics.escalated}</p>
          <p className="text-xs text-black/55">Cases requiring additional oversight</p>
        </Card>
        <Card className="space-y-2 border-sky-100 bg-white/90 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-black/55">SAR Flow</p>
            <Clock3 className="h-4 w-4 text-sky-600" />
          </div>
          <p className="text-2xl font-bold text-sky-700">{metrics.sarFlow}</p>
          <p className="text-xs text-black/55">Drafted, approved, or filed SARs</p>
        </Card>
        <Card className="space-y-2 border-rose-100 bg-white/90 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-black/55">Errors</p>
            <XCircle className="h-4 w-4 text-rose-600" />
          </div>
          <p className="text-2xl font-bold text-rose-700">{metrics.errors}</p>
          <p className="text-xs text-black/55">Cases that need retry or triage</p>
        </Card>
      </section>

      <Card className="space-y-3 p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-black/60">Filters</h2>
          <p className="text-xs text-black/55">
            {loading
              ? "Syncing cases..."
              : lastSyncedAt
                ? `Last synced ${formatDate(lastSyncedAt)}`
                : "No sync recorded yet"}
          </p>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="space-y-1">
            <span className="text-xs font-medium text-black/60">Bank Scope</span>
            <Select value={bankScope} onChange={(event) => setBankScope(event.target.value as BankScopeMode)}>
              <option value="session">This session ({sessionBankId ? sessionBankId.slice(0, 18) : "..."})</option>
              <option value="demo">Shared demo (demo)</option>
              <option value="all">All banks</option>
            </Select>
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium text-black/60">Status</span>
            <Select value={status} onChange={(event) => setStatus(event.target.value)}>
              {statusOptions.map((option) => (
                <option key={option} value={option}>
                  {option ? statusLabel(option) : "All statuses"}
                </option>
              ))}
            </Select>
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium text-black/60">Alert Type</span>
            <Select value={alertType} onChange={(event) => setAlertType(event.target.value)}>
              <option value="">All alert types</option>
              <option value="AML">AML</option>
              <option value="SANCTIONS">SANCTIONS</option>
            </Select>
          </label>
        </div>
      </Card>

      <Card className="overflow-hidden p-0">
        <div className="border-b border-black/10 bg-slate-50/85 px-4 py-3">
          <p className="text-sm font-medium text-slate-700">Case Queue</p>
          <p className="text-xs text-black/55">Click a case ID to open full investigation details.</p>
        </div>
        {loading ? (
          <div className="space-y-3 p-4">
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="h-12 animate-pulse rounded-lg bg-black/[0.06]" />
            ))}
          </div>
        ) : null}
        {error ? (
          <div className="m-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}
        {!loading && !cases.length ? (
          <div className="m-4 space-y-2 rounded-xl border border-dashed border-black/20 bg-white p-6 text-sm text-black/70">
            <p className="font-semibold text-slate-800">No cases found for current filters.</p>
            <p>Generate a sample casefile to see the full evidence-first artifact end-to-end.</p>
            <div className="grid gap-2 pt-2 sm:grid-cols-2">
              <Button
                className="h-11 w-full justify-center"
                onClick={() => void generateDemo("AML")}
                disabled={demoLoading !== null || !sessionBankId}
              >
                {demoLoading === "AML" ? "Generating AML..." : "Generate sample AML case"}
              </Button>
              <Button
                variant="outline"
                className="h-11 w-full justify-center"
                onClick={() => void generateDemo("SANCTIONS")}
                disabled={demoLoading !== null || !sessionBankId}
              >
                {demoLoading === "SANCTIONS" ? "Generating Sanctions..." : "Generate sample sanctions case"}
              </Button>
            </div>
            <Link href="/" className="text-sky-700 underline inline-block">
              Back to home
            </Link>
          </div>
        ) : null}
        {!!cases.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-[900px] text-sm">
              <thead className="bg-slate-50 text-left">
                <tr className="border-b border-black/10">
                  <th className="px-4 py-3 font-semibold text-slate-700">Case ID</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">Alert ID</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">Type</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">Status</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">Created</th>
                  <th className="px-4 py-3 font-semibold text-slate-700">Updated</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((item) => (
                  <tr key={item.case_id} className="border-b border-black/5 transition-colors hover:bg-emerald-50/40">
                    <td className="px-4 py-3">
                      <Link className="inline-flex items-center gap-2 font-semibold text-sky-700 hover:underline" href={`/cases/${item.case_id}`}>
                        <span className="font-mono">{item.case_id.slice(0, 10)}...</span>
                        <ArrowUpRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700">{item.alert_id || "NOT PROVIDED"}</td>
                    <td className="px-4 py-3">{item.alert_type || item.casefile_json?.header?.alert_type || "NOT PROVIDED"}</td>
                    <td className="px-4 py-3">
                      <Badge text={statusLabel(item.status)} tone={toneFromStatus(item.status)} />
                    </td>
                    <td className="px-4 py-3 text-slate-700">{formatDate(item.created_at)}</td>
                    <td className="px-4 py-3 text-slate-700">{formatDate(item.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card>
    </main>
  );
}
