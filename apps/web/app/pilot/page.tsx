"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, Loader2, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { calSans } from "@/font/font";
import { apiRequest } from "@/lib/api";

type PilotLeadPayload = {
  company?: string | null;
  requester_name?: string | null;
  requester_email: string;
  alert_engine_or_case_tool?: string | null;
  alert_types: string[];
  monthly_alert_volume?: number | null;
  it_contact_name?: string | null;
  it_contact_email?: string | null;
  message?: string | null;
  metadata?: Record<string, any>;
};

const alertTypeOptions = ["AML", "SANCTIONS", "CTR", "SAR"] as const;

export default function PilotPage() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submittedId, setSubmittedId] = useState<number | null>(null);
  const [form, setForm] = useState<PilotLeadPayload>({
    company: "",
    requester_name: "",
    requester_email: "",
    alert_engine_or_case_tool: "",
    alert_types: ["AML", "SANCTIONS"],
    monthly_alert_volume: null,
    it_contact_name: "",
    it_contact_email: "",
    message: "",
    metadata: {},
  });

  const canSubmit = useMemo(() => {
    return Boolean(form.requester_email.trim().length > 3 && form.alert_types.length > 0);
  }, [form.alert_types.length, form.requester_email]);

  async function submit() {
    setError(null);
    setSubmitting(true);
    try {
      const payload: PilotLeadPayload = {
        ...form,
        monthly_alert_volume: form.monthly_alert_volume === null ? null : Number(form.monthly_alert_volume),
        metadata: {
          page: "/pilot",
          ts: new Date().toISOString(),
        },
      };
      const resp = await apiRequest<{ id: number; status: string }>("/v1/leads/pilot", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSubmittedId(resp.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit pilot request");
    } finally {
      setSubmitting(false);
    }
  }

  if (submittedId) {
    return (
      <main className="space-y-6 p-6 md:p-10 xl:p-20">
        <Card className="mx-auto max-w-3xl space-y-4 border-emerald-200 bg-emerald-50 p-6">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-700" />
            <div className="space-y-1">
              <p className="text-sm font-semibold text-emerald-900">Pilot request received</p>
              <p className="text-sm text-emerald-800">
                We will follow up shortly. Reference ID: <span className="font-mono">{submittedId}</span>
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/cases">
              <Button>Open Cases</Button>
            </Link>
            <Link href="/security">
              <Button variant="outline">Review Security</Button>
            </Link>
          </div>
        </Card>
      </main>
    );
  }

  return (
    <main className="space-y-6 p-6 md:p-10 xl:p-20">
      <section className="relative overflow-hidden rounded-3xl border border-black/10 bg-white/85 p-6 shadow-sm md:p-8">
        <div className="pointer-events-none absolute -right-8 -top-10 h-44 w-44 rounded-full bg-emerald-200/40 blur-3xl" />
        <div className="pointer-events-none absolute -left-8 bottom-0 h-36 w-36 rounded-full bg-sky-200/40 blur-2xl" />

        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div className="space-y-3">
            <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-sky-700 hover:underline">
              <ArrowLeft className="h-4 w-4" />
              Back to home
            </Link>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700/90">Pilot</p>
            <h1 className={`text-3xl font-bold tracking-tight text-slate-900 md:text-4xl ${calSans.className}`}>
              Request a 30-day Pilot
            </h1>
            <p className="max-w-3xl text-sm text-slate-700 md:text-base">
              Tell us what you run today and we will scope a low-risk pilot. We do not replace detection; we generate
              evidence-ready case files with audit traceability.
            </p>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge tone="neutral">Connector inside bank boundary</Badge>
              <Badge tone="neutral">Evidence pointers</Badge>
              <Badge tone="neutral">Integrity hashes</Badge>
            </div>
          </div>
          <div className="flex w-full flex-wrap gap-2 sm:w-auto">
            <Link href="/security">
              <Button variant="outline" className="flex-1 sm:flex-none">
                Security
              </Button>
            </Link>
            <a href="/api/docs" target="_blank" rel="noreferrer">
              <Button variant="outline" className="flex-1 sm:flex-none">
                API Docs
              </Button>
            </a>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-12">
        <Card className="space-y-4 p-6 lg:col-span-8">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold uppercase tracking-wide text-black/60">Pilot Details</p>
            <span className="inline-flex items-center gap-2 text-xs text-black/55">
              <ShieldCheck className="h-4 w-4 text-emerald-700" />
              No detection logic changes
            </span>
          </div>

          {error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-xs font-medium text-black/60">Company</span>
              <Input value={form.company || ""} onChange={(e) => setForm((p) => ({ ...p, company: e.target.value }))} />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-medium text-black/60">Your name</span>
              <Input
                value={form.requester_name || ""}
                onChange={(e) => setForm((p) => ({ ...p, requester_name: e.target.value }))}
              />
            </label>
            <label className="space-y-1 md:col-span-2">
              <span className="text-xs font-medium text-black/60">Your email (required)</span>
              <Input
                type="email"
                value={form.requester_email}
                onChange={(e) => setForm((p) => ({ ...p, requester_email: e.target.value }))}
              />
            </label>

            <label className="space-y-1 md:col-span-2">
              <span className="text-xs font-medium text-black/60">Alert engine / Case tool</span>
              <Input
                placeholder="e.g., Actimize, Verafin, internal rules engine"
                value={form.alert_engine_or_case_tool || ""}
                onChange={(e) => setForm((p) => ({ ...p, alert_engine_or_case_tool: e.target.value }))}
              />
            </label>

            <div className="space-y-2 md:col-span-2">
              <span className="text-xs font-medium text-black/60">Alert types (required)</span>
              <div className="flex flex-wrap gap-2">
                {alertTypeOptions.map((opt) => {
                  const active = form.alert_types.includes(opt);
                  return (
                    <button
                      key={opt}
                      type="button"
                      onClick={() =>
                        setForm((p) => ({
                          ...p,
                          alert_types: active ? p.alert_types.filter((t) => t !== opt) : [...p.alert_types, opt],
                        }))
                      }
                      className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition ${
                        active
                          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                          : "border-black/10 bg-white text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            </div>

            <label className="space-y-1">
              <span className="text-xs font-medium text-black/60">Monthly alert volume</span>
              <Input
                type="number"
                min={0}
                value={form.monthly_alert_volume ?? ""}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    monthly_alert_volume: e.target.value === "" ? null : Number(e.target.value),
                  }))
                }
              />
            </label>

            <label className="space-y-1">
              <span className="text-xs font-medium text-black/60">IT contact (name)</span>
              <Input
                value={form.it_contact_name || ""}
                onChange={(e) => setForm((p) => ({ ...p, it_contact_name: e.target.value }))}
              />
            </label>
            <label className="space-y-1 md:col-span-2">
              <span className="text-xs font-medium text-black/60">IT contact (email)</span>
              <Input
                type="email"
                value={form.it_contact_email || ""}
                onChange={(e) => setForm((p) => ({ ...p, it_contact_email: e.target.value }))}
              />
            </label>

            <label className="space-y-1 md:col-span-2">
              <span className="text-xs font-medium text-black/60">Notes</span>
              <Textarea
                value={form.message || ""}
                onChange={(e) => setForm((p) => ({ ...p, message: e.target.value }))}
                placeholder="Any constraints, timelines, or specific alerts you want us to start with."
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-black/10 pt-4">
            <p className="text-xs text-black/55">
              We will use this info to scope a pilot. No external data pulls are required for the initial demo.
            </p>
            <Button disabled={!canSubmit || submitting} onClick={() => void submit()} className="gap-2">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {submitting ? "Submitting..." : "Request Pilot"}
            </Button>
          </div>
        </Card>

        <Card className="h-fit space-y-3 border-black/10 bg-white/90 p-6 lg:col-span-4 lg:self-start">
          <p className="text-sm font-semibold uppercase tracking-wide text-black/60">What You Get</p>
          <div className="space-y-2 text-sm text-slate-700">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
              A connector integration checklist and endpoint contracts
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
              5–10 evidence-ready case files for your alert types
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
              Exportable exam packets (bundle + hashes)
            </div>
          </div>
          <div className="rounded-2xl border border-black/10 bg-slate-50/80 p-4 text-xs text-slate-700">
            Typical timeline: 1–2 days to wire connector endpoints in a pilot environment, then case files generate quietly
            in the background.
          </div>
          <Link href="/playground" className="text-sm text-sky-700 underline inline-block">
            View the live simulation testbench
          </Link>
        </Card>
      </div>
    </main>
  );
}
