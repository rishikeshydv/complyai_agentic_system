import Link from "next/link";
import {
  CheckCircle,
  ClipboardCheck,
  Database,
  FileLock2,
  KeyRound,
  Lock,
  Network,
  Shield,
  ShieldCheck,
  Wrench,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { calSans } from "@/font/font";

type ControlStatus = "Implemented" | "Configurable" | "Roadmap";

function statusTone(value: ControlStatus): "good" | "neutral" | "warn" {
  if (value === "Implemented") return "good";
  if (value === "Configurable") return "neutral";
  return "warn";
}

function StatusBadge({ value }: { value: ControlStatus }) {
  return (
    <Badge tone={statusTone(value)} className="text-[11px] font-semibold uppercase tracking-wide">
      {value}
    </Badge>
  );
}

export default function SecurityPage() {
  return (
    <main className="space-y-6 p-6 md:p-10 xl:p-20">
      <section className="relative overflow-hidden rounded-3xl border border-black/10 bg-white/85 p-6 shadow-sm md:p-8">
        <div className="pointer-events-none absolute -right-8 -top-10 h-44 w-44 rounded-full bg-emerald-200/40 blur-3xl" />
        <div className="pointer-events-none absolute -left-8 bottom-0 h-36 w-36 rounded-full bg-sky-200/40 blur-2xl" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-tr from-emerald-200/20 via-white/10 to-sky-200/10 blur-3xl" />

        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700/90">Security</p>
            <h1 className={`text-3xl font-bold tracking-tight text-slate-900 md:text-4xl ${calSans.className}`}>
              Bank-Ready Deployment + Controls
            </h1>
            <p className="max-w-3xl text-sm text-slate-700 md:text-base">
              A practical overview of how Comply AI is designed to run inside bank environments: connector-in-bank,
              evidence-first case generation, and audit-ready governance. Sections are marked as implemented vs roadmap.
            </p>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge tone="good">Evidence-first outputs</Badge>
              <Badge tone="neutral">Deterministic integrity hashes</Badge>
              <Badge tone="neutral">Request IDs everywhere</Badge>
              <Badge tone="warn">mTLS (roadmap)</Badge>
            </div>
          </div>

          <div className="flex w-full flex-wrap gap-2 sm:w-auto">
            <a href="/api/docs" target="_blank" rel="noreferrer">
              <Button variant="outline" className="h-10 flex-1 sm:flex-none">
                API Docs
              </Button>
            </a>
            <Link href="/cases">
              <Button className="h-10 flex-1 sm:flex-none">Open Cases</Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-12">
        <Card className="border-black/10 bg-white/90 lg:col-span-7">
          <div className="border-b border-black/10 bg-slate-50/80 px-6 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Architecture</p>
            <p className="text-sm text-slate-700">Connector runs inside the bank network. Core generates case files.</p>
          </div>
          <CardContent className="p-6">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-black/10 bg-white p-4">
                <div className="flex items-center gap-2">
                  <Network className="h-4 w-4 text-emerald-700" />
                  <p className="text-sm font-semibold text-slate-900">Bank Network</p>
                </div>
                <p className="mt-2 text-sm text-slate-700">
                  Alert engine, KYC, and transaction systems remain inside the bank boundary.
                </p>
              </div>
              <div className="rounded-2xl border border-black/10 bg-white p-4">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-sky-700" />
                  <p className="text-sm font-semibold text-slate-900">Connector Service</p>
                </div>
                <p className="mt-2 text-sm text-slate-700">
                  Normalizes evidence via allowlisted endpoints and logs every fetch.
                </p>
              </div>
              <div className="rounded-2xl border border-black/10 bg-white p-4">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-slate-700" />
                  <p className="text-sm font-semibold text-slate-900">Core Platform</p>
                </div>
                <p className="mt-2 text-sm text-slate-700">
                  Builds evidence graphs, generates case files, and stores audit events and hashes.
                </p>
              </div>
            </div>

            <div className="mt-5 rounded-2xl border border-black/10 bg-gradient-to-br from-slate-50 to-white p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Data Flow</p>
              <ol className="mt-3 grid gap-3 md:grid-cols-2">
                <li className="rounded-xl border border-black/10 bg-white p-4 text-sm text-slate-700">
                  <p className="font-semibold text-slate-900">1. Alert arrives</p>
                  <p className="mt-1">A bank alert ID is detected or received (AML or sanctions).</p>
                </li>
                <li className="rounded-xl border border-black/10 bg-white p-4 text-sm text-slate-700">
                  <p className="font-semibold text-slate-900">2. Evidence pulled</p>
                  <p className="mt-1">Core pulls allowlisted customer, transaction, aggregates, and sanctions hit data.</p>
                </li>
                <li className="rounded-xl border border-black/10 bg-white p-4 text-sm text-slate-700">
                  <p className="font-semibold text-slate-900">3. Evidence graph built</p>
                  <p className="mt-1">Nodes + pointers are created; missing fields are marked NOT PROVIDED.</p>
                </li>
                <li className="rounded-xl border border-black/10 bg-white p-4 text-sm text-slate-700">
                  <p className="font-semibold text-slate-900">4. Case file generated</p>
                  <p className="mt-1">Case JSON + Markdown are produced with integrity hashes and audit timeline.</p>
                </li>
              </ol>
            </div>
          </CardContent>
        </Card>

        <Card className="border-black/10 bg-white/90 lg:col-span-5">
          <div className="border-b border-black/10 bg-slate-50/80 px-6 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Quick Answers</p>
            <p className="text-sm text-slate-700">What bank reviewers typically ask first.</p>
          </div>
          <CardContent className="space-y-4 p-6">
            <div className="rounded-2xl border border-black/10 bg-white p-4">
              <p className="text-sm font-semibold text-slate-900">Does the model invent facts?</p>
              <p className="mt-1 text-sm text-slate-700">
                Outputs are evidence-first. If something is missing from the evidence graph, the platform should emit{" "}
                <span className="font-mono text-[12px]">NOT PROVIDED</span>.
              </p>
            </div>
            <div className="rounded-2xl border border-black/10 bg-white p-4">
              <p className="text-sm font-semibold text-slate-900">Can you reproduce a result?</p>
              <p className="mt-1 text-sm text-slate-700">
                Case files store evidence hash, casefile hash, and version metadata so outputs can be replayed and diffed.
              </p>
            </div>
            <div className="rounded-2xl border border-black/10 bg-white p-4">
              <p className="text-sm font-semibold text-slate-900">What runs inside the bank?</p>
              <p className="mt-1 text-sm text-slate-700">
                The connector service runs bank-side and exposes normalized evidence APIs with allowlisting and request
                logging.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      <Card className="border-black/10 bg-white/90">
        <div className="border-b border-black/10 bg-slate-50/80 px-6 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-600">Controls Matrix</p>
          <p className="text-sm text-slate-700">Clear “implemented vs roadmap” for diligence.</p>
        </div>
        <CardContent className="p-6">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <div className="rounded-2xl border border-black/10 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <ClipboardCheck className="h-4 w-4 text-emerald-700" />
                  <p className="text-sm font-semibold text-slate-900">Audit Events</p>
                </div>
                <StatusBadge value="Implemented" />
              </div>
              <p className="mt-2 text-sm text-slate-700">
                Immutable audit events for generation steps and human actions.
              </p>
            </div>

            <div className="rounded-2xl border border-black/10 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <FileLock2 className="h-4 w-4 text-sky-700" />
                  <p className="text-sm font-semibold text-slate-900">Integrity Hashes</p>
                </div>
                <StatusBadge value="Implemented" />
              </div>
              <p className="mt-2 text-sm text-slate-700">
                Evidence hash + casefile hash stored to support replay and tamper detection.
              </p>
            </div>

            <div className="rounded-2xl border border-black/10 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Network className="h-4 w-4 text-rose-700" />
                  <p className="text-sm font-semibold text-slate-900">Request Signing</p>
                </div>
                <StatusBadge value="Implemented" />
              </div>
              <p className="mt-2 text-sm text-slate-700">
                Signed request option between core and connector (demo uses API key).
              </p>
            </div>

            <div className="rounded-2xl border border-black/10 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4 text-slate-700" />
                  <p className="text-sm font-semibold text-slate-900">RBAC + SSO</p>
                </div>
                <StatusBadge value="Roadmap" />
              </div>
              <p className="mt-2 text-sm text-slate-700">
                SAML/OIDC, granular permissions, and tenant isolation for bank rollouts.
              </p>
            </div>

            <div className="rounded-2xl border border-black/10 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-slate-700" />
                  <p className="text-sm font-semibold text-slate-900">mTLS Enforcement</p>
                </div>
                <StatusBadge value="Roadmap" />
              </div>
              <p className="mt-2 text-sm text-slate-700">
                Certificate-based auth, rotation, and IP allowlists for connector traffic.
              </p>
            </div>

            <div className="rounded-2xl border border-black/10 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Wrench className="h-4 w-4 text-slate-700" />
                  <p className="text-sm font-semibold text-slate-900">Retention Policies</p>
                </div>
                <StatusBadge value="Configurable" />
              </div>
              <p className="mt-2 text-sm text-slate-700">
                Per-deployment retention and export policies (roadmap: TTL + WORM options).
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-black/10 bg-slate-50/80 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="text-sm font-semibold text-slate-900">Want a bank onboarding checklist?</p>
                <p className="text-sm text-slate-700">
                  We can tailor controls and deployment posture to your environment (VPC, on-prem, hybrid).
                </p>
              </div>
              <a href="mailto:rishikeshadh4@gmail.com">
                <Button className="gap-2">
                  <ShieldCheck className="h-4 w-4" />
                  Contact
                </Button>
              </a>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
