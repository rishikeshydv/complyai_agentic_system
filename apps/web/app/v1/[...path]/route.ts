import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const HOP_BY_HOP_HEADERS = [
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
];

function resolveCoreApiBase(): string {
  const candidates = [
    process.env.CORE_API_INTERNAL_URL,
    process.env.BACKEND_API_URL,
    process.env.NEXT_PUBLIC_CORE_API_URL,
    "http://core-api:8000",
    "http://core-api.railway.internal:8000",
  ]
    .map((value) => (value || "").trim())
    .filter((value) => value.length > 0)
    .map((value) => value.replace(/\/$/, ""));

  if (candidates.length === 0) {
    throw new Error("CORE_API_INTERNAL_URL is not configured");
  }

  return candidates[0];
}

async function proxyRequest(
  request: NextRequest,
  params: { path: string[] },
): Promise<NextResponse> {
  const base = resolveCoreApiBase();
  const upstreamPath = params.path.join("/");
  const rootPath = params.path.length === 1 && params.path[0] === "health";
  const upstreamUrl = `${base}${rootPath ? `/${upstreamPath}` : `/v1/${upstreamPath}`}${request.nextUrl.search}`;

  const headers = new Headers(request.headers);
  for (const header of HOP_BY_HOP_HEADERS) {
    headers.delete(header);
  }

  headers.set("x-forwarded-host", request.headers.get("host") || "");
  headers.set("x-forwarded-proto", request.nextUrl.protocol.replace(":", ""));

  const response = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
    redirect: "manual",
    cache: "no-store",
  });

  const responseHeaders = new Headers(response.headers);
  for (const header of HOP_BY_HOP_HEADERS) {
    responseHeaders.delete(header);
  }

  return new NextResponse(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

async function handler(
  request: NextRequest,
  context: { params: { path: string[] } },
): Promise<NextResponse> {
  try {
    return await proxyRequest(request, context.params);
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown proxy error";
    return NextResponse.json(
      { message: "Core API proxy request failed", detail },
      { status: 502 },
    );
  }
}

export async function GET(
  request: NextRequest,
  context: { params: { path: string[] } },
): Promise<NextResponse> {
  return handler(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: { path: string[] } },
): Promise<NextResponse> {
  return handler(request, context);
}

export async function PUT(
  request: NextRequest,
  context: { params: { path: string[] } },
): Promise<NextResponse> {
  return handler(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: { params: { path: string[] } },
): Promise<NextResponse> {
  return handler(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: { params: { path: string[] } },
): Promise<NextResponse> {
  return handler(request, context);
}

export async function OPTIONS(
  request: NextRequest,
  context: { params: { path: string[] } },
): Promise<NextResponse> {
  return handler(request, context);
}
