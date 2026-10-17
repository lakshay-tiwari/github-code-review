import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

export async function GET() {
  const { userId, getToken } = await auth();

  if (!userId) {
    return NextResponse.json(
      { error: "Unauthorized: No active Clerk user session" },
      { status: 401 }
    );
  }

  const token = await getToken();
  if (!token) {
    return NextResponse.json(
      { error: "Unauthorized: Failed to retrieve Clerk session token" },
      { status: 401 }
    );
  }

  const backendUrl = process.env.FASTAPI_INTERNAL_URL || "http://localhost:8000";

  try {
    const res = await fetch(`${backendUrl}/api/v1/repositories`, {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    return NextResponse.json(
      {
        error: "Failed to connect to Cortex API backend",
        details: err instanceof Error ? err.message : String(err),
      },
      { status: 502 }
    );
  }
}

export async function POST(req: NextRequest) {
  const { userId, getToken } = await auth();

  if (!userId) {
    return NextResponse.json(
      { error: "Unauthorized: No active Clerk user session" },
      { status: 401 }
    );
  }

  const token = await getToken();
  if (!token) {
    return NextResponse.json(
      { error: "Unauthorized: Failed to retrieve Clerk session token" },
      { status: 401 }
    );
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON request payload" },
      { status: 400 }
    );
  }

  const backendUrl = process.env.FASTAPI_INTERNAL_URL || "http://localhost:8000";

  try {
    const res = await fetch(`${backendUrl}/api/v1/repositories`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    return NextResponse.json(
      {
        error: "Failed to connect to Cortex API backend",
        details: err instanceof Error ? err.message : String(err),
      },
      { status: 502 }
    );
  }
}
