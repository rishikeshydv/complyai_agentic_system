"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bot,
  Database,
  PlayCircle,
  Radar,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { calSans } from "@/font/font";
import { apiRequest } from "@/lib/api";
import {
  BANK_SESSION_KEY,
  BankScopeMode,
  getOrCreateSessionBankId,
  getStoredBankScope,
  setStoredBankScope,
} from "@/lib/sessionBank";

type PlaygroundStatus = {
  bank_id: string;
  simulator: {
    running: boolean;
    config: {
      bank_id: string;
      seed_customers: number;
      tx_per_tick: number;
      aml_alert_rate: number;
      sanctions_alert_rate: number;
    };
    started_at: string | null;
    last_tick_at: string | null;
    totals: {
      transactions_generated: number;
      alerts_generated: number;
      aml_alerts_generated: number;
      sanctions_alerts_generated: number;
      customers_in_store: number;
      transactions_in_store: number;
      alerts_in_store: number;
      latest_alert_id: string | null;
    };
  };
  pipeline: {
    total_cases: number;
    ready_for_review: number;
    sar_flow_cases: number;
    ingestion_events_total: number;
    ingestion_events_last_hour: number;
    cases_last_hour: number;
    latest_case_id: string | null;
    latest_ingest_status: string | null;
  };
};

type CaseRecord = {
  case_id: string;
  alert_id: string;
  bank_id: string;
  status: string;
  created_at: string;
  alert_type: string;
};

const bankApiUsage: Array<{ endpoint: string; purpose: string }> = [
  {
    endpoint: "GET /v1/bank/alerts?created_after=&limit=",
    purpose: "Background feed poll to discover newly generated alerts.",
  },
  {
    endpoint: "GET /v1/bank/alerts/{alert_id}",
    purpose: "Fetch alert metadata, rule thresholds, and conditions triggered.",
  },
  {
    endpoint: "GET /v1/bank/transactions/{transaction_id}",
    purpose: "Load primary transaction evidence linked to alert.",
  },
  {
    endpoint: "GET /v1/bank/customers/{customer_id}",
    purpose: "Load customer and KYC snapshot for case context.",
  },
  {
    endpoint: "GET /v1/bank/aggregates?customer_id=&rule_triggered=&window_days=",
    purpose: "Load lookback aggregates and linked transactions used in rule explanation.",
  },
  {
    endpoint: "GET /v1/bank/sanctions/hits/{alert_id}",
    purpose: "Load sanctions match details for sanctions alerts.",
  },
];

function formatDate(value: string | null): string {
  if (!value) return "N/A";
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return "N/A";
  return timestamp.toLocaleString();
}

export default function PlaygroundPage() {
  const [status, setStatus] = useState<PlaygroundStatus | null>(null);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionBankId, setSessionBankId] = useState("");
  const [bankScope, setBankScope] = useState<BankScopeMode>("session");
  const [config, setConfig] = useState({
    bank_id: "",
    seed_customers: 20,
    tx_per_tick: 12,
    aml_alert_rate: 0.2,
    sanctions_alert_rate: 0.05,
  });

  async function load() {
    if (!config.bank_id) return;
    setError(null);
    try {
      const [statusPayload, casesPayload] = await Promise.all([
        apiRequest<PlaygroundStatus>(`/v1/playground/status?bank_id=${encodeURIComponent(config.bank_id)}`),
        apiRequest<CaseRecord[]>(`/v1/cases?bank_id=${encodeURIComponent(config.bank_id)}`),
      ]);
      setStatus(statusPayload);
      setCases(casesPayload.slice(0, 8));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load playground");
    } finally {
      setLoading(false);
    }
  }

  async function start() {
    setError(null);
    try {
      await apiRequest<PlaygroundStatus>("/v1/playground/start", {
        method: "POST",
        body: JSON.stringify({ ...config, reset_before_start: true }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start simulator");
    }
  }

  async function stop() {
    setError(null);
    try {
      await apiRequest<PlaygroundStatus>(`/v1/playground/stop?bank_id=${encodeURIComponent(config.bank_id)}`, {
        method: "POST",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop simulator");
    }
  }

  async function toggleSimulation() {
    setError(null);
    setActionLoading(true);
    try {
      if (status?.simulator.running) {
        await stop();
      } else {
        await start();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update simulator");
    } finally {
      setActionLoading(false);
    }
  }

  useEffect(() => {
    const bankId = getOrCreateSessionBankId();
    setSessionBankId(bankId);
    const storedScope = getStoredBankScope();
    setBankScope(storedScope === "all" ? "session" : storedScope);
  }, []);

  useEffect(() => {
    setStoredBankScope(bankScope);
    const nextBankId = bankScope === "demo" ? "demo" : sessionBankId;
    if (nextBankId && config.bank_id !== nextBankId) {
      setConfig((prev) => ({ ...prev, bank_id: nextBankId }));
    }
  }, [bankScope, sessionBankId]);

  useEffect(() => {
    if (!config.bank_id) return;
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [config.bank_id]);

  const rateSummary = useMemo(() => {
    if (!status) return "N/A";
    return `${Math.round(status.simulator.config.aml_alert_rate * 100)}% AML / ${Math.round(
      status.simulator.config.sanctions_alert_rate * 100,
    )}% Sanctions`;
  }, [status]);

  return (
    <main className="space-y-5 p-6 md:p-10 xl:p-20">
      <section className="relative overflow-hidden rounded-3xl border border-black/10 bg-white/85 p-6 shadow-sm md:p-8">
        <div className="pointer-events-none absolute -right-8 -top-10 h-44 w-44 rounded-full bg-emerald-200/40 blur-3xl" />
        <div className="pointer-events-none absolute -left-8 bottom-0 h-36 w-36 rounded-full bg-sky-200/40 blur-2xl" />
        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700/90">Simulation</p>
            <h1 className={`text-3xl font-bold tracking-tight text-slate-900 md:text-4xl ${calSans.className}`}>
              Agentic Playground
            </h1>
            <p className="max-w-2xl text-sm text-slate-700 md:text-base">
              Generate realistic customer activity, trigger AML/sanctions alerts, and watch the platform create
              audit-ready cases in the background.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={status?.simulator.running ? "good" : "neutral"}>
                {status?.simulator.running ? "Simulator Running" : "Simulator Stopped"}
              </Badge>
              <Badge tone="neutral">Rates: {rateSummary}</Badge>
              <Badge tone="neutral">Bank: {config.bank_id || "..."}</Badge>
            </div>
          </div>
          <div className="flex w-full flex-wrap gap-2 sm:w-auto">
            <Button variant="outline" className="h-10 w-full sm:w-auto" onClick={() => void load()}>
              Refresh
            </Button>
            <Link href="/cases" className="w-full sm:w-auto">
              <Button className="h-10 w-full sm:w-auto">Open Cases</Button>
            </Link>
          </div>
        </div>
      </section>

      <Card className="space-y-3 p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-black/60">Session Scope</h2>
          <p className="text-xs text-black/55">Choose whether to isolate data per session or share the demo bank.</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <label className="space-y-1">
            <span className="text-xs font-medium text-black/60">Bank Scope</span>
            <select
              className="h-10 w-full rounded-md border border-black/10 bg-white px-3 text-sm"
              value={bankScope === "all" ? "session" : bankScope}
              onChange={(e) => setBankScope(e.target.value as BankScopeMode)}
            >
              <option value="session">This session ({sessionBankId ? sessionBankId.slice(0, 18) : "..."})</option>
              <option value="demo">Shared demo (demo)</option>
            </select>
          </label>
        </div>
      </Card>

      {error ? (
        <Card className="border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p>{error}</p>
          </div>
        </Card>
      ) : null}

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Card className="space-y-2 border-emerald-100 bg-white/90 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-black/55">Generated Transactions</p>
            <Database className="h-4 w-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900">{status?.simulator.totals.transactions_generated ?? 0}</p>
          <p className="text-xs text-black/55">Synthetic financial activity created</p>
        </Card>
        <Card className="space-y-2 border-amber-100 bg-white/90 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-black/55">Generated Alerts</p>
            <Radar className="h-4 w-4 text-amber-600" />
          </div>
          <p className="text-2xl font-bold text-amber-700">{status?.simulator.totals.alerts_generated ?? 0}</p>
          <p className="text-xs text-black/55">AML + sanctions alerts emitted</p>
        </Card>
        <Card className="space-y-2 border-sky-100 bg-white/90 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-black/55">Cases (Total)</p>
            <Bot className="h-4 w-4 text-sky-600" />
          </div>
          <p className="text-2xl font-bold text-sky-700">{status?.pipeline.total_cases ?? 0}</p>
          <p className="text-xs text-black/55">Case files created by orchestrator</p>
        </Card>
        <Card className="space-y-2 border-indigo-100 bg-white/90 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-black/55">Cases Ready</p>
            <ShieldCheck className="h-4 w-4 text-indigo-600" />
          </div>
          <p className="text-2xl font-bold text-indigo-700">{status?.pipeline.ready_for_review ?? 0}</p>
          <p className="text-xs text-black/55">Ready for analyst review</p>
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-12">
        <Card className="space-y-4 p-5 lg:col-span-8">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Simulator Controls</h2>
            {loading ? <span className="text-xs text-black/60">Loading runtime...</span> : null}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="text-xs font-medium text-black/60">Bank ID</span>
              <Input
                value={config.bank_id}
                onChange={(e) => {
                  const nextBankId = e.target.value.trim();
                  if (!nextBankId) return;
                  window.sessionStorage.setItem(BANK_SESSION_KEY, nextBankId);
                  setConfig((prev) => ({ ...prev, bank_id: nextBankId }));
                }}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-xs font-medium text-black/60">Seed Customers</span>
              <Input type="number" min={1} max={200} value={config.seed_customers} onChange={(e) => setConfig((prev) => ({ ...prev, seed_customers: Number(e.target.value || 20) }))} />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-xs font-medium text-black/60">Transactions / Tick</span>
              <Input type="number" min={1} max={100} value={config.tx_per_tick} onChange={(e) => setConfig((prev) => ({ ...prev, tx_per_tick: Number(e.target.value || 12) }))} />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-xs font-medium text-black/60">AML Alert Rate (0-1)</span>
              <Input type="number" step="0.01" min={0} max={1} value={config.aml_alert_rate} onChange={(e) => setConfig((prev) => ({ ...prev, aml_alert_rate: Number(e.target.value || 0.2) }))} />
            </label>
            <label className="space-y-1 text-sm md:col-span-2">
              <span className="text-xs font-medium text-black/60">Sanctions Alert Rate (0-1)</span>
              <Input type="number" step="0.01" min={0} max={1} value={config.sanctions_alert_rate} onChange={(e) => setConfig((prev) => ({ ...prev, sanctions_alert_rate: Number(e.target.value || 0.05) }))} />
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => void toggleSimulation()}
              variant={status?.simulator.running ? "destructive" : "default"}
              disabled={loading || actionLoading}
              className="gap-2"
            >
              <PlayCircle className="h-4 w-4" />
              {actionLoading
                ? status?.simulator.running
                  ? "Stopping..."
                  : "Starting..."
                : status?.simulator.running
                  ? "Stop Simulation"
                  : "Start Simulation"}
            </Button>
          </div>
        </Card>

        <Card className="space-y-3 p-5 lg:col-span-4">
          <h2 className="text-lg font-semibold">Runtime</h2>
          <p className="text-sm">Running: <span className="font-semibold">{status?.simulator.running ? "YES" : "NO"}</span></p>
          <p className="text-sm">Latest Alert: {status?.simulator.totals.latest_alert_id || "N/A"}</p>
          <p className="text-sm">Last Tick: {formatDate(status?.simulator.last_tick_at || null)}</p>
          <p className="text-sm">Latest Case: {status?.pipeline.latest_case_id || "N/A"}</p>
          <p className="text-sm">Latest Ingest: {status?.pipeline.latest_ingest_status || "N/A"}</p>
          <p className="text-xs text-black/60">Ingestion is automatic in background while simulation is running.</p>
        </Card>
      </section>

      <Card className="space-y-2 p-5">
        <h2 className="text-lg font-semibold">Bank APIs Used In Simulation</h2>
        <p className="text-sm text-black/65">
          During alert-to-case generation, core-api pulls evidence from connector using these bank endpoints.
        </p>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2 pr-3">Endpoint</th>
                <th className="py-2 pr-3">How it is used</th>
              </tr>
            </thead>
            <tbody>
              {bankApiUsage.map((row) => (
                <tr key={row.endpoint} className="border-b align-top">
                  <td className="py-2 pr-3 font-mono text-xs">{row.endpoint}</td>
                  <td className="py-2 pr-3">{row.purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="space-y-2 p-5">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-emerald-600" />
          <h2 className="text-lg font-semibold">Latest Cases</h2>
        </div>
        {!cases.length ? <p className="text-sm">No cases yet. Start the simulator and wait for auto-ingestion.</p> : null}
        {!!cases.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="py-2 pr-3">Case ID</th>
                  <th className="py-2 pr-3">Alert ID</th>
                  <th className="py-2 pr-3">Type</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((row) => (
                  <tr key={row.case_id} className="border-b">
                    <td className="py-2 pr-3">
                      <Link className="inline-flex items-center gap-1.5 text-blue-700 underline" href={`/cases/${row.case_id}`}>
                        {row.case_id.slice(0, 10)}...
                        <ArrowUpRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                    <td className="py-2 pr-3">{row.alert_id}</td>
                    <td className="py-2 pr-3">{row.alert_type}</td>
                    <td className="py-2 pr-3">{row.status}</td>
                    <td className="py-2 pr-3">{formatDate(row.created_at)}</td>
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
