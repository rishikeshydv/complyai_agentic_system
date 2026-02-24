"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, BookOpenText, FlaskConical, LayoutGrid, ShieldCheck, Shield } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Home", icon: LayoutGrid },
  { href: "/law_search", label: "Law Search", icon: BookOpenText },
  { href: "/cases", label: "Cases", icon: ShieldCheck },
  { href: "/playground", label: "Playground", icon: FlaskConical },
  { href: "/security", label: "Security", icon: Shield },
  { href: "/pilot", label: "Pilot", icon: ArrowUpRight },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 px-3 py-3 md:px-5">
      <div className="container">
        <div className="relative overflow-hidden rounded-2xl border border-black/10 bg-white/80 shadow-[0_14px_40px_rgba(15,23,42,0.10)] backdrop-blur-xl">
          <div className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full bg-emerald-200/40 blur-2xl" />
          <div className="pointer-events-none absolute -left-8 bottom-0 h-24 w-24 rounded-full bg-sky-200/40 blur-2xl" />

          <div className="relative flex items-center justify-between gap-3 px-4 py-3 md:px-5">
            <Link href="/" className="group flex shrink-0 items-center gap-3">
              <Image
                src="/logo/comply-ai-logo.png"
                alt="Comply AI"
                width={120}
                height={32}
                priority
                className="h-8 w-auto"
              />
              <div className="hidden border-l border-black/10 pl-3 md:block">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700/90">Evidence-First</p>
                <p className="text-xs text-slate-600">Agentic AML + Sanctions</p>
              </div>
            </Link>

            <nav className="hidden min-w-0 flex-1 items-center justify-center md:flex">
              <div className="flex max-w-full items-center gap-1 overflow-x-auto rounded-full border border-black/10 bg-white/85 p-1">
                {navItems.map((item) => {
                  const active = isActive(pathname, item.href);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-all",
                        active
                          ? "bg-gradient-to-r from-emerald-400 to-teal-500 text-white shadow-sm"
                          : "text-slate-700 hover:bg-slate-100 hover:text-slate-900",
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </nav>

            <a href="/api/docs" target="_blank" rel="noreferrer">
              <Button
                variant="outline"
                size="sm"
                className="h-9 shrink-0 rounded-full border-black/15 bg-white/90 px-3 text-slate-900 shadow-sm hover:shadow-md md:px-4"
              >
                <span className="hidden sm:inline">API Docs</span>
                <ArrowUpRight className="h-4 w-4" />
              </Button>
            </a>
          </div>

          <nav className="border-t border-black/10 px-3 pb-3 pt-2 md:hidden">
            <div className="flex items-center gap-2 overflow-x-auto pb-1">
              {navItems.map((item) => {
                const active = isActive(pathname, item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "inline-flex shrink-0 items-center justify-center gap-1 rounded-lg px-3 py-2 text-xs font-semibold transition-all",
                      active
                        ? "bg-gradient-to-r from-emerald-400 to-teal-500 text-white"
                        : "bg-white text-slate-700 hover:bg-slate-100",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
