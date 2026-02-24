import { NextResponse } from "next/server";

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

async function postWithBackendFallback(path: string, payload: unknown): Promise<Response> {
  let lastError: unknown = null;
  for (const base of backendBaseCandidates()) {
    try {
      return await fetch(`${base}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError ?? new Error("No reachable backend base URL");
}

export async function POST(request: Request) {
  try {
    const payload = await request.json();
    const response = await postWithBackendFallback("/v1/laws/map-event", payload);

    const body = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ message: "Map event request failed", detail }, { status: 502 });
  }
}
