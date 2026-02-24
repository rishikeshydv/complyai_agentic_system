import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const response = NextResponse.redirect(new URL(request.url), 307);
  response.headers.set("Location", "/v1/docs");
  return response;
}
