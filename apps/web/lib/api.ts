function resolveCoreApiBase(): string {
  const raw = (process.env.NEXT_PUBLIC_CORE_API_URL || "").trim().replace(/\/$/, "");
  if (!raw) return "";
  if (/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(raw)) return "";
  return raw;
}

const CORE_API = resolveCoreApiBase();

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const initHeaders =
    init.headers instanceof Headers
      ? Object.fromEntries(init.headers.entries())
      : ((init.headers as Record<string, string> | undefined) ?? {});
  const headers: Record<string, string> = {
    ...initHeaders
  };
  if (init.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${CORE_API}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return (await response.text()) as T;
}
