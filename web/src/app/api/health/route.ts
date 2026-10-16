import { NextResponse } from "next/server";

interface BackendHealthResponse {
  status: string;
  app: string;
  version: string;
  environment?: string;
}

export async function GET() {
  const backendUrl = process.env.FASTAPI_INTERNAL_URL || "http://localhost:8000";
  let backendStatus: BackendHealthResponse | null = null;
  let backendReachable = false;

  try {
    const res = await fetch(`${backendUrl}/health`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });

    if (res.ok) {
      backendStatus = await res.json();
      backendReachable = true;
    }
  } catch {
    backendReachable = false;
  }

  return NextResponse.json({
    frontend: {
      status: "ok",
      timestamp: new Date().toISOString(),
    },
    backend: {
      url: backendUrl,
      reachable: backendReachable,
      info: backendStatus,
    },
  });
}
