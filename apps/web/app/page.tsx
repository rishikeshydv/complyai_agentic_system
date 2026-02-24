"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  CheckCircle,
  FileSearch,
  Phone,
  Settings,
  TrendingDown,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { calSans } from "@/font/font";

const features = [
  {
    icon: TrendingDown,
    badge: "Detection",
    title: "Fewer False Positives",
    description:
      "Adaptive models learn from analyst feedback to focus on real risk while preserving high recall. Less noise, more signal.",
  },
  {
    icon: BookOpen,
    badge: "Legal Search",
    title: "Exact Laws, Instantly",
    description:
      "Jump to mapped citations with clean snippets and quickly trace every claim back to evidence pointers.",
  },
  {
    icon: Zap,
    badge: "Speed",
    title: "Extremely Fast",
    description:
      "Generate structured case files in minutes from incoming alerts, including deterministic evidence mapping.",
  },
  {
    icon: CheckCircle,
    badge: "Integration",
    title: "Plug-and-Play Setup",
    description:
      "Use your current AML and sanctions alert engines. Comply AI interprets and documents, not replaces.",
  },
  {
    icon: Settings,
    badge: "Control",
    title: "Analyst + Admin Workflow",
    description:
      "Review, escalate, close, and SAR status transitions are all tracked with immutable timeline events.",
  },
  {
    icon: FileSearch,
    badge: "Transparency",
    title: "Everything Explained",
    description:
      "Narratives are evidence-linked to payload fields and missing details are explicitly marked NOT PROVIDED.",
  },
];

const steps = [
  {
    num: "01",
    title: "Ingest Existing Alerts",
    desc: "Push AML and sanctions alerts from your current rule/screening engines.",
  },
  {
    num: "02",
    title: "Generate Case File",
    desc: "Comply AI builds deterministic evidence tables and AI narrative with traceability pointers.",
  },
  {
    num: "03",
    title: "Human Review",
    desc: "Analysts review, edit SAR drafts, and apply disposition actions with role-based controls.",
  },
  {
    num: "04",
    title: "Export + Audit",
    desc: "Export markdown/json bundles and retain immutable AI + human action history.",
  },
];

export default function LandingPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const preview = {
    meta: {
      caseId: "CASE-DEMO-0001",
      alertType: "AML",
      status: "READY_FOR_REVIEW",
      evidenceHash: "sha256:9c1b...f2a9",
      casefileHash: "sha256:3ad8...c91e",
      generatedAt: "2026-02-14 12:02 UTC",
    },
    summary: {
      recommendedDisposition: "REVIEW",
      observedFacts: [
        {
          label: "Cash deposits (7 days)",
          value: "3 deposits near USD 10,000",
          evidence: ["ev:agg:CUST-DEMO:STRUCTURING_RULE_03:7"],
        },
        {
          label: "Total amount (7 days)",
          value: "USD 28,100",
          evidence: ["ev:agg:CUST-DEMO:STRUCTURING_RULE_03:7"],
        },
      ],
      interpretation:
        "Pattern is consistent with structuring red flags and warrants analyst review based on observed thresholds.",
      interpretationEvidence: ["ev:cond:STRUCTURING_RULE_03:0", "ev:cond:STRUCTURING_RULE_03:1"],
    },
    ruleRows: [
      {
        condition: "cash_deposit_count_7d",
        threshold: ">= 3",
        actual: "3",
        window: "7d",
        evidence: "ev:agg:CUST-DEMO:STRUCTURING_RULE_03:7",
      },
      {
        condition: "cash_deposit_total_7d",
        threshold: ">= 20,000",
        actual: "28,100",
        window: "7d",
        evidence: "ev:agg:CUST-DEMO:STRUCTURING_RULE_03:7",
      },
    ],
    evidencePointers: [
      { label: "Alert", value: "ev:alert:ALERT-DEMO-AML-..." },
      { label: "Customer", value: "ev:cust:CUST-DEMO-..." },
      { label: "Primary transaction", value: "ev:tx:TX-DEMO-..." },
      { label: "Aggregates", value: "ev:agg:CUST-DEMO:STRUCTURING_RULE_03:7" },
    ],
    citations: [
      {
        citation: "31 C.F.R. 1010.320 (SAR filing requirements)",
        why: "Structuring patterns can require SAR consideration depending on facts and investigation outcome.",
        evidence: ["ev:cond:STRUCTURING_RULE_03:0", "ev:agg:CUST-DEMO:STRUCTURING_RULE_03:7"],
      },
    ],
    sar: {
      required: false,
      narrative: "NOT PROVIDED",
    },
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <section className="relative overflow-hidden bg-[url(/bgs/grid-1.png)] bg-repeat bg-top px-4 pb-24 pt-28">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/35 to-white" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-100/60 via-transparent to-transparent" />

        <div className="container relative mx-auto max-w-5xl text-center">
          <div className={`transition-all duration-700 ${mounted ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}>
            <Badge variant="secondary" className="mb-6 border border-emerald-200 bg-emerald-50 text-emerald-700">
              <div className="mr-2 h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Designed with BSA leaders
            </Badge>
            <h1 className={`mb-6 text-5xl font-bold leading-[1.1] text-slate-900 tracking-tighter md:text-7xl ${calSans.className}`}>
              Turn AML &amp; Sanctions Alerts into
              <span className="bg-gradient-to-r from-emerald-400 to-teal-500 bg-clip-text text-transparent"> Evidence-Ready Cases.</span>
            </h1>

            <p className="mx-auto mb-10 max-w-3xl text-lg leading-relaxed text-slate-600 md:text-xl">
              An AI compliance copilot that interprets alerts from your existing systems, produces audit-ready case files,
              and cites the exact evidence behind each conclusion.
            </p>

            <div className="mb-16 flex flex-col items-center justify-center gap-4 sm:flex-row sm:gap-6">
              <Link href="/cases" className="w-full sm:w-auto">
                <Button size="lg" className="h-12 w-full px-8 text-base shadow-lg shadow-emerald-300/40 sm:w-auto">
                  Open Case Workbench
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/playground" className="w-full sm:w-auto">
                <Button
                  size="lg"
                  variant="outline"
                  className="group relative h-12 w-full px-8 text-base shadow-lg transition-all hover:scale-[1.02] hover:shadow-xl sm:w-auto"
                >
                  Open Playground
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white/60 px-4 py-20">
        <div className="container mx-auto max-w-6xl">
          <div className="mb-10 text-center">
            <Badge variant="secondary" className="mb-4 border border-emerald-200 bg-emerald-50 text-emerald-700">
              Output Artifact
            </Badge>
            <h2 className={`mb-3 text-4xl font-bold tracking-tighter text-slate-900 md:text-5xl ${calSans.className}`}>
              The Case File, End-to-End
            </h2>
            <p className="mx-auto max-w-3xl text-lg text-slate-600">
              Your core deliverable is a discrete, audit-ready case file. Every non-trivial statement is tied to evidence pointers.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-12">
            <Card className="border-black/10 bg-white lg:col-span-5">
              <CardContent className="flex h-full flex-col gap-4 p-8">
                <div className="space-y-1">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700/90">What you get</p>
                  <h3 className={`text-2xl font-semibold text-slate-900 ${calSans.className}`}>A regulator-ready bundle</h3>
                </div>
                <div className="space-y-4">
                  <ul className="space-y-3 text-sm text-slate-700">
                    <li className="flex items-start gap-2">
                      <CheckCircle className="mt-0.5 h-4 w-4 text-emerald-600" />
                      Executive summary with recommended disposition.
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="mt-0.5 h-4 w-4 text-emerald-600" />
                      Deterministic rule evaluation (threshold vs actual).
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="mt-0.5 h-4 w-4 text-emerald-600" />
                      Evidence pointers for every non-trivial statement.
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="mt-0.5 h-4 w-4 text-emerald-600" />
                      Regulatory traceability mapped to citations.
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle className="mt-0.5 h-4 w-4 text-emerald-600" />
                      Optional SAR draft section with edits tracked in audit events.
                    </li>
                  </ul>

                  <div className="rounded-2xl border border-black/10 bg-slate-50/70 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Export bundle</p>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-700">
                      <span className="rounded-full border border-black/10 bg-white px-2 py-1">Markdown report</span>
                      <span className="rounded-full border border-black/10 bg-white px-2 py-1">JSON casefile</span>
                      <span className="rounded-full border border-black/10 bg-white px-2 py-1">Evidence hash</span>
                      <span className="rounded-full border border-black/10 bg-white px-2 py-1">Casefile hash</span>
                    </div>
                  </div>
                </div>

                <div className="mt-auto flex flex-col gap-3 sm:flex-row">
                  <Link href="/cases" className="w-full sm:w-auto">
                    <Button className="w-full sm:w-auto">View Cases</Button>
                  </Link>
                  <Link href="/playground" className="w-full sm:w-auto">
                    <Button variant="outline" className="w-full sm:w-auto">
                      Generate a demo case
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            <Card className="overflow-hidden border-black/10 bg-white lg:col-span-7">
              <div className="border-b border-black/10 bg-slate-50/80 px-6 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Sample Case File</p>
                    <p className="text-sm text-slate-700">How the artifact reads to an analyst and auditor.</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <Badge tone="neutral">Alert: {preview.meta.alertType}</Badge>
                    <Badge tone="good">{preview.meta.status.replace(/_/g, " ")}</Badge>
                  </div>
                </div>
              </div>

              <div className="max-h-[520px] overflow-auto p-6">
                <div className="rounded-2xl border border-black/10 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
                  <div className="border-b border-black/10 bg-gradient-to-r from-white via-slate-50 to-white px-5 py-4 text-slate-900">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-600">Comply AI Case File</p>
                        <p className={`text-lg font-semibold text-slate-900 ${calSans.className}`}>{preview.meta.caseId}</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-700">
                        <span className="rounded-full border border-black/10 bg-white px-2 py-1">
                          Generated {preview.meta.generatedAt}
                        </span>
                        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 font-mono text-emerald-900">
                          Evidence {preview.meta.evidenceHash}
                        </span>
                        <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-1 font-mono text-sky-900">
                          Casefile {preview.meta.casefileHash}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-5 p-5">
                    <section className="rounded-2xl border border-black/10 bg-slate-50/70 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Executive Summary</p>
                        <Badge tone="neutral">Disposition: {preview.summary.recommendedDisposition}</Badge>
                      </div>
                      <div className="mt-3 grid gap-3 md:grid-cols-2">
                        {preview.summary.observedFacts.map((item) => (
                          <div key={item.label} className="rounded-xl border border-black/10 bg-white p-3">
                            <p className="text-xs font-semibold text-slate-900">{item.label}</p>
                            <p className="mt-1 text-sm text-slate-700">{item.value}</p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {item.evidence.map((ev) => (
                                <span
                                  key={ev}
                                  className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[11px] text-emerald-800"
                                >
                                  {ev}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 rounded-xl border border-black/10 bg-white p-3">
                        <p className="text-xs font-semibold text-slate-900">Interpretation</p>
                        <p className="mt-1 text-sm text-slate-700">{preview.summary.interpretation}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {preview.summary.interpretationEvidence.map((ev) => (
                            <span
                              key={ev}
                              className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 font-mono text-[11px] text-sky-800"
                            >
                              {ev}
                            </span>
                          ))}
                        </div>
                      </div>
                    </section>

                    <section className="rounded-2xl border border-black/10 bg-white p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Rule Evaluation</p>
                        <p className="text-xs text-slate-600">Deterministic from evidence</p>
                      </div>

                      <div className="mt-3 overflow-hidden rounded-xl border border-black/10">
                        <div className="grid grid-cols-12 bg-slate-50/80 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                          <div className="col-span-5">Condition</div>
                          <div className="col-span-2 text-right">Threshold</div>
                          <div className="col-span-2 text-right">Actual</div>
                          <div className="col-span-1 text-right">Window</div>
                          <div className="col-span-2 text-right">Evidence</div>
                        </div>
                        <div className="divide-y divide-black/10">
                          {preview.ruleRows.map((row) => (
                            <div key={row.condition} className="grid grid-cols-12 items-center px-3 py-2 text-sm">
                              <div className="col-span-5 font-medium text-slate-900">{row.condition}</div>
                              <div className="col-span-2 text-right text-slate-700">{row.threshold}</div>
                              <div className="col-span-2 text-right text-slate-700">{row.actual}</div>
                              <div className="col-span-1 text-right text-slate-700">{row.window}</div>
                              <div className="col-span-2 text-right">
                                <span className="inline-flex max-w-full truncate rounded-full border border-black/10 bg-white px-2 py-0.5 font-mono text-[11px] text-slate-700">
                                  {row.evidence}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </section>

                    <section className="grid gap-4 lg:grid-cols-2">
                      <div className="rounded-2xl border border-black/10 bg-white p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Evidence Pointers</p>
                        <div className="mt-3 space-y-2">
                          {preview.evidencePointers.map((item) => (
                            <div key={item.label} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-black/10 bg-slate-50/70 px-3 py-2">
                              <span className="text-sm font-medium text-slate-900">{item.label}</span>
                              <span className="max-w-full truncate font-mono text-[12px] text-slate-700">{item.value}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="rounded-2xl border border-black/10 bg-white p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Regulatory Traceability</p>
                        <div className="mt-3 space-y-3">
                          {preview.citations.map((item) => (
                            <div key={item.citation} className="rounded-xl border border-black/10 bg-slate-50/70 p-3">
                              <p className="text-sm font-semibold text-slate-900">{item.citation}</p>
                              <p className="mt-1 text-sm text-slate-700">{item.why}</p>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {item.evidence.map((ev) => (
                                  <span key={ev} className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 font-mono text-[11px] text-amber-800">
                                    {ev}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </section>

                    <section className="rounded-2xl border border-black/10 bg-white p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">SAR Draft</p>
                        <Badge tone="neutral">{preview.sar.required ? "Required" : "Optional"}</Badge>
                      </div>
                      <p className="mt-2 text-sm text-slate-700">
                        {preview.sar.narrative}
                      </p>
                      <p className="mt-2 text-xs text-slate-600">
                        SAR content is generated only when disposition escalates, or when explicitly requested.
                      </p>
                    </section>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>

      <section id="features" className="bg-muted/30 px-4 py-24">
        <div className="container mx-auto max-w-7xl">
          <div className="mb-16 text-center">
            <Badge variant="secondary" className="mb-4 border border-emerald-200 bg-emerald-50 text-emerald-700">
              Platform
            </Badge>
            <h2 className={`mb-5 text-4xl font-bold text-slate-900 tracking-tighter md:text-5xl ${calSans.className}`}>
              Built for Speed, Precision, and Trust
            </h2>
            <p className="mx-auto max-w-2xl text-lg tracking-tight text-slate-600">
              Audit alerts faster, reduce review noise, and preserve full traceability for regulator-ready documentation.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <Card
                key={feature.title}
                className="group h-full border-black/10 bg-white transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
              >
                <CardContent className="space-y-4 p-8">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 transition-all group-hover:scale-110 group-hover:bg-emerald-100">
                    <feature.icon className="h-6 w-6 text-emerald-600" />
                  </div>
                  <Badge variant="outline" className="w-fit border-emerald-200 text-emerald-700">
                    {feature.badge}
                  </Badge>
                  <h3 className={`text-xl font-semibold text-slate-900 ${calSans.className}`}>{feature.title}</h3>
                  <p className="leading-relaxed text-slate-600">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="bg-white/60 px-4 py-24">
        <div className="container mx-auto max-w-6xl">
          <div className="mb-16 text-center">
            <Badge variant="secondary" className="mb-4 border border-emerald-200 bg-emerald-50 text-emerald-700">
              Process
            </Badge>
            <h2 className={`mb-5 text-4xl font-bold tracking-tighter text-slate-900 md:text-5xl ${calSans.className}`}>How It Works</h2>
            <p className="text-lg text-slate-600">From ingestion to audit export in a clean four-step workflow.</p>
          </div>

          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {steps.map((step) => (
              <div key={step.num} className="relative rounded-2xl p-5 shadow-sm transition hover:shadow-md">
                <div className="mb-3 text-6xl font-bold leading-none text-emerald-100">{step.num}</div>
                <h3 className={`mb-2 text-xl font-semibold text-slate-900 ${calSans.className}`}>{step.title}</h3>
                <p className="text-sm leading-relaxed text-slate-600">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden bg-muted/30 px-4 py-24 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-emerald-400/25 via-transparent to-transparent opacity-70" />
        <div className="container relative mx-auto max-w-4xl text-center">
          <h2 className={`mb-6 text-4xl font-bold tracking-tighter text-black md:text-5xl ${calSans.className}`}>
            Production-grade compliance workflows, without replacing your core alerting stack.
          </h2>
          <p className="mb-12 text-xl text-black/75">Deploy quickly, keep human oversight, and maintain regulator-ready traceability.</p>

          <div className="mb-12 flex flex-col justify-center gap-4 sm:flex-row">
            <Link href="/pilot" className="w-full sm:w-auto">
              <Button size="lg" className="h-12 w-full px-8 text-base text-white sm:w-auto">
                <Phone className="h-4 w-4" />
                Request a 30-day Pilot
              </Button>
            </Link>
            <a href="/api/docs" target="_blank" rel="noreferrer" className="w-full sm:w-auto">
              <Button
                variant="outline"
                size="lg"
                className="group relative flex h-12 w-full items-center justify-center gap-2 px-8 text-black shadow-lg transition-all duration-300 ease-out hover:scale-105 hover:shadow-xl active:scale-95 sm:w-auto"
              >
                API Docs
                <ArrowRight className="h-4 w-4" />
              </Button>
            </a>
          </div>

          <div className="flex flex-wrap justify-center gap-6 text-sm text-white/70">
            <div className="flex items-center gap-2 text-black/80">
              <CheckCircle className="h-4 w-4 text-emerald-300" />
              Evidence-linked outputs
            </div>
            <div className="flex items-center gap-2 text-black/80">
              <CheckCircle className="h-4 w-4 text-emerald-300" />
              Human + AI timeline
            </div>
            <div className="flex items-center gap-2 text-black/80">
              <CheckCircle className="h-4 w-4 text-emerald-300" />
              SAR workflow controls
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-black/10 bg-white/70 px-4 py-6">
        <div className="container mx-auto flex flex-col items-center justify-between gap-4 md:flex-row">
          <Link href="/">
            <Image src="/logo/comply-ai-logo.png" alt="Comply AI" width={120} height={120} />
          </Link>
          <p className="text-sm text-slate-600">
            © 2026 <span className="font-medium text-emerald-600">Comply AI</span>. All rights reserved.
          </p>
          <div className="flex items-center gap-6 text-sm text-slate-600">
            <Link href="/security">Security</Link>
            <Link href="#">Privacy</Link>
            <Link href="#">Terms</Link>
            <Link href="#">Contact</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
