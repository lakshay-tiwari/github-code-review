import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

const mockAuth = vi.fn();

vi.mock("@clerk/nextjs/server", () => ({
  auth: () => mockAuth(),
}));

describe("Next.js Repositories Proxy Routes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("GET /api/repositories returns 401 when not signed in", async () => {
    mockAuth.mockResolvedValue({ userId: null, getToken: vi.fn() });
    const { GET } = await import("@/app/api/repositories/route");
    const response = await GET();
    expect(response.status).toBe(401);
  });

  it("POST /api/repositories returns 401 when not signed in", async () => {
    mockAuth.mockResolvedValue({ userId: null, getToken: vi.fn() });
    const { POST } = await import("@/app/api/repositories/route");
    const req = new NextRequest("http://localhost:3000/api/repositories", {
      method: "POST",
      body: JSON.stringify({ github_url: "https://github.com/fastapi/fastapi" }),
    });
    const response = await POST(req);
    expect(response.status).toBe(401);
  });

  it("GET /api/repositories forwards token to FastAPI backend", async () => {
    mockAuth.mockResolvedValue({
      userId: "user_test_123",
      getToken: vi.fn().mockResolvedValue("mock_jwt_token"),
    });

    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      json: async () => ({
        repositories: [{ id: "repo-1", name: "fastapi" }],
        total: 1,
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { GET } = await import("@/app/api/repositories/route");
    const response = await GET();

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.repositories).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/repositories",
      expect.objectContaining({
        headers: {
          Accept: "application/json",
          Authorization: "Bearer mock_jwt_token",
        },
      })
    );
  });

  it("POST /api/repositories forwards payload to FastAPI backend", async () => {
    mockAuth.mockResolvedValue({
      userId: "user_test_123",
      getToken: vi.fn().mockResolvedValue("mock_jwt_token"),
    });

    const mockFetch = vi.fn().mockResolvedValue({
      status: 201,
      json: async () => ({
        id: "repo-1",
        name: "fastapi",
        status: "pending",
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { POST } = await import("@/app/api/repositories/route");
    const req = new NextRequest("http://localhost:3000/api/repositories", {
      method: "POST",
      body: JSON.stringify({ github_url: "https://github.com/fastapi/fastapi" }),
    });
    const response = await POST(req);

    expect(response.status).toBe(201);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/repositories",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ github_url: "https://github.com/fastapi/fastapi" }),
        headers: expect.objectContaining({
          Authorization: "Bearer mock_jwt_token",
        }),
      })
    );
  });
});
