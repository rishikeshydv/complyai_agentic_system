import { NextResponse } from "next/server";

type LawResult = {
  obligation_id: string;
  agency: string;
  citation: string;
  excerpt: string;
  title: string;
  instrument_type: string;
  jurisdiction: string;
  source_url: string;
  must_do: string;
  conditions: string | null;
  artifacts_required: string[];
  summary_bullets: string[];
  review_status: string;
  confidence: number | null;
};

type RawLawItem = {
  obligation_id?: string;
  agency?: string;
  citation?: string;
  excerpt?: string;
  title?: string;
  instrument_type?: string;
  jurisdiction?: string;
  source_url?: string;
  must_do?: string;
  conditions?: string | null;
  artifacts_required?: string[];
  summary_bullets?: string[];
  review_status?: string;
  confidence?: number | null;
};

const GENERIC_SENTENCE_RE = /\b(not provided|general compliance|n\/a)\b/i;

function cleanText(value: unknown): string {
  if (typeof value !== "string") return "";
  return value
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function cleanExcerpt(value: unknown): string {
  if (typeof value !== "string") return "";
  return value
    .replace(/<(?!\/?mark\b)[^>]+>/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function deriveCondition(item: RawLawItem): string {
  const explicit = cleanText(item.conditions || "");
  if (explicit && !GENERIC_SENTENCE_RE.test(explicit)) return explicit;

  const mustDo = cleanText(item.must_do || "");
  const lower = mustDo.toLowerCase();
  for (const token of [" if ", " when ", " unless ", " upon "]) {
    const idx = lower.indexOf(token);
    if (idx >= 0) return mustDo.slice(idx + 1).trim();
  }

  const citation = cleanText(item.citation || "");
  if (citation) return `Applies to entities and activities governed by ${citation}.`;
  return "Applies when the facts or activity described by this obligation are present.";
}

function deriveSummaryBullets(item: RawLawItem, condition: string, artifacts: string[]): string[] {
  const bullets = (Array.isArray(item.summary_bullets) ? item.summary_bullets : [])
    .map((entry) => cleanText(entry))
    .filter((entry) => entry.length > 0 && !GENERIC_SENTENCE_RE.test(entry))
    .slice(0, 3);
  if (bullets.length >= 2) return bullets;

  const mustDo = cleanText(item.must_do || "");
  const citation = cleanText(item.citation || "");
  const fallback = [
    mustDo ? `Required action: ${mustDo}` : citation ? `Citation: ${citation}` : "",
    `When it applies: ${condition}`,
    artifacts.length ? `Retain evidence: ${artifacts.slice(0, 3).join(", ")}.` : "Retain evidence: Control execution evidence.",
  ].filter((entry) => entry.length > 0);
  return fallback.slice(0, 3);
}

function backendBaseCandidates(): string[] {
  const candidates = [
    process.env.LAW_SEARCH_API_URL,
    process.env.BACKEND_API_URL,
    process.env.CORE_API_INTERNAL_URL,
    process.env.NEXT_PUBLIC_CORE_API_URL,
    "http://core-api:8000",
    "http://localhost:8000",
  ]
    .map((value) => (value || "").trim())
    .filter((value) => value.length > 0)
    .map((value) => value.replace(/\/$/, ""));

  return Array.from(new Set(candidates));
}

async function fetchWithBackendFallback(pathWithQuery: string): Promise<Response> {
  let lastError: unknown = null;
  for (const base of backendBaseCandidates()) {
    try {
      return await fetch(`${base}${pathWithQuery}`, { method: "GET", cache: "no-store" });
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError ?? new Error("No reachable backend base URL");
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("query") || "";
  const jurisdiction = searchParams.get("jurisdiction") || "";

  if (!query.trim()) {
    return NextResponse.json({ message: "Query is required", data: [] }, { status: 400 });
  }

  const target = new URL("http://backend-placeholder/v1/laws/search");
  target.searchParams.set("q", query);
  if (jurisdiction) target.searchParams.set("jurisdiction", jurisdiction);

  try {
    const response = await fetchWithBackendFallback(`${target.pathname}${target.search}`);
    const body = await response.json();
    const rows: RawLawItem[] = Array.isArray(body?.results) ? body.results : [];

    const normalizeJurisdiction = (value?: string): string => {
      const raw = (value || "").trim().toLowerCase();
      if (raw === "us" || raw === "usa" || raw.includes("federal") || raw.includes("united states")) {
        return "Federal";
      }
      if (raw === "nj" || raw.includes("new jersey")) {
        return "New Jersey";
      }
      return value || "NOT PROVIDED";
    };

    const data: LawResult[] = rows.map((item) => {
      const artifacts = Array.from(
        new Set(
          (Array.isArray(item.artifacts_required) ? item.artifacts_required : [])
            .map((entry) => cleanText(entry))
            .filter((entry) => entry.length > 0),
        ),
      );
      const condition = deriveCondition(item);
      const summary = deriveSummaryBullets(item, condition, artifacts);

      return {
        obligation_id: item.obligation_id || "",
        agency: item.agency || "NOT PROVIDED",
        citation: cleanText(item.citation) || "NOT PROVIDED",
        excerpt: cleanExcerpt(item.excerpt) || "NOT PROVIDED",
        title: cleanText(item.title) || "NOT PROVIDED",
        instrument_type:
          cleanText(item.instrument_type) ||
          ((item.citation || "").toUpperCase().startsWith("SANCTIONS-") ? "SANCTIONS" : "AML"),
        jurisdiction: normalizeJurisdiction(item.jurisdiction),
        source_url: item.source_url || "",
        must_do: cleanText(item.must_do) || "NOT PROVIDED",
        conditions: condition,
        artifacts_required: artifacts,
        summary_bullets: summary,
        review_status: item.review_status || "unreviewed",
        confidence: typeof item.confidence === "number" ? item.confidence : null,
      };
    });

    return NextResponse.json({ message: "Success", data }, { status: response.status });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { message: "Law search request failed", detail, data: [] },
      { status: 502 },
    );
  }
}
