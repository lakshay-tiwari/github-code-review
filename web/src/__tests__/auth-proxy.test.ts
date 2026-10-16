import { describe, it, expect, vi, beforeEach } from "vitest";

const mockAuth = vi.fn();

vi.mock("@clerk/nextjs/server", () => ({
  auth: () => mockAuth(),
}));

describe("Next.js Auth Me Proxy Route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns 401 when user is not signed in", async () => {
    mockAuth.mockResolvedValue({
      userId: null,
      getToken: vi.fn(),
    });

    const { GET } = await import("@/app/api/auth/me/route");
    const response = await GET();

    expect(response.status).toBe(401);
    const body = await response.json();
    expect(body.error).toContain("No active Clerk user session");
  });

  it("returns 401 when token retrieval returns null", async () => {
    mockAuth.mockResolvedValue({
      userId: "user_test_123",
      getToken: vi.fn().mockResolvedValue(null),
    });

    const { GET } = await import("@/app/api/auth/me/route");
    const response = await GET();

    expect(response.status).toBe(401);
    const body = await response.json();
    expect(body.error).toContain("Failed to retrieve Clerk session token");
  });

  it("forwards token to FastAPI backend and returns backend response", async () => {
    mockAuth.mockResolvedValue({
      userId: "user_test_123",
      getToken: vi.fn().mockResolvedValue("mock_jwt_session_token"),
    });

    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      json: async () => ({
        user_id: "user_test_123",
        session_id: "sess_test_123",
        claims: { sub: "user_test_123" },
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { GET } = await import("@/app/api/auth/me/route");
    const response = await GET();

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.user_id).toBe("user_test_123");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/auth/me",
      expect.objectContaining({
        headers: {
          Accept: "application/json",
          Authorization: "Bearer mock_jwt_session_token",
        },
      })
    );
  });
});
