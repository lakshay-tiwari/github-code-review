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

export interface CurrentUser {
  user_id: string;
  session_id?: string | null;
  email?: string | null;
  authorized_party?: string | null;
  claims: Record<string, unknown>;
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const response = await fetch("/api/auth/me", {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch current user: ${response.statusText}`);
  }

  return response.json();
}

