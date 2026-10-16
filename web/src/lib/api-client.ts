/**
 * Typed client utilities for frontend components.
 * Calls Next.js server-side route handlers, never exposing backend secret credentials.
 */

export interface SystemHealth {
  frontend: {
    status: string;
    timestamp: string;
  };
  backend: {
    url: string;
    reachable: boolean;
    info?: {
      status: string;
      app: string;
      version: string;
      environment?: string;
    } | null;
  };
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const response = await fetch("/api/health", {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch system health: ${response.statusText}`);
  }

  return response.json();
}
