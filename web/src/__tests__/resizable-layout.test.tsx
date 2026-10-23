import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import { ChatHistorySidebar } from "@/components/chat/chat-history-sidebar";
import { DashboardSidebar } from "@/components/dashboard/sidebar";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard/chat",
}));

describe("Resizable UI Components", () => {
  it("renders ResizablePanelGroup with panels and handles", () => {
    const { container } = render(
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel defaultSize={20}>
          <div>Sidebar Panel</div>
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={80}>
          <div>Content Panel</div>
        </ResizablePanel>
      </ResizablePanelGroup>
    );

    expect(screen.getByText("Sidebar Panel")).toBeDefined();
    expect(screen.getByText("Content Panel")).toBeDefined();
    // Handle should be rendered
    const handle = container.querySelector("[data-panel-resize-handle-id]");
    expect(handle).not.toBeNull();
  });
});

describe("DashboardSidebar", () => {
  it("renders navigation items and branding", () => {
    render(<DashboardSidebar />);
    expect(screen.getByText("Cortex")).toBeDefined();
    expect(screen.getByText("Repositories")).toBeDefined();
    expect(screen.getByText("Code Chat")).toBeDefined();
  });

  it("renders collapse button and triggers onCollapse when enabled", () => {
    const onCollapse = vi.fn();
    render(
      <DashboardSidebar showCollapseButton={true} onCollapse={onCollapse} />
    );

    const collapseBtn = screen.getByLabelText(/Collapse Main Sidebar/i);
    expect(collapseBtn).toBeDefined();
    fireEvent.click(collapseBtn);
    expect(onCollapse).toHaveBeenCalledTimes(1);
  });
});

describe("ChatHistorySidebar", () => {
  const mockRepos = [
    {
      id: "r1",
      name: "cortex",
      owner: "lakshya",
      default_branch: "main",
      status: "ready",
    },
  ];

  const mockConversations = [
    {
      id: "c1",
      repository_id: "r1",
      title: "Architecture Discussion",
      created_at: "2026-10-23T10:00:00Z",
    },
    {
      id: "c2",
      repository_id: "r1",
      title: "Bug Fix Thread",
      created_at: "2026-10-23T10:15:00Z",
    },
  ];

  it("renders repository select and thread list", () => {
    render(
      <ChatHistorySidebar
        repositories={mockRepos}
        selectedRepoId="r1"
        onSelectRepo={() => {}}
        conversations={mockConversations}
        activeConvId="c1"
        onSelectConv={() => {}}
        onNewConv={() => {}}
        onDeleteConv={() => {}}
      />
    );

    expect(screen.getByText("lakshya/cortex")).toBeDefined();
    expect(screen.getByText("Architecture Discussion")).toBeDefined();
    expect(screen.getByText("Bug Fix Thread")).toBeDefined();
  });

  it("handles new conversation button click", () => {
    const onNewConv = vi.fn();
    render(
      <ChatHistorySidebar
        repositories={mockRepos}
        selectedRepoId="r1"
        onSelectRepo={() => {}}
        conversations={mockConversations}
        activeConvId="c1"
        onSelectConv={() => {}}
        onNewConv={onNewConv}
        onDeleteConv={() => {}}
      />
    );

    const newBtn = screen.getByRole("button", { name: /New chat thread/i });
    fireEvent.click(newBtn);
    expect(onNewConv).toHaveBeenCalledTimes(1);
  });

  it("handles conversation selection and deletion", () => {
    const onSelectConv = vi.fn();
    const onDeleteConv = vi.fn();

    render(
      <ChatHistorySidebar
        repositories={mockRepos}
        selectedRepoId="r1"
        onSelectRepo={() => {}}
        conversations={mockConversations}
        activeConvId="c1"
        onSelectConv={onSelectConv}
        onNewConv={() => {}}
        onDeleteConv={onDeleteConv}
      />
    );

    fireEvent.click(screen.getByText("Bug Fix Thread"));
    expect(onSelectConv).toHaveBeenCalledWith("c2");

    const deleteBtn = screen.getByLabelText(/Delete thread Architecture Discussion/i);
    fireEvent.click(deleteBtn);
    expect(onDeleteConv).toHaveBeenCalledWith("c1");
  });

  it("renders collapse button and triggers onCollapse when showCollapseButton is true", () => {
    const onCollapse = vi.fn();
    render(
      <ChatHistorySidebar
        repositories={mockRepos}
        selectedRepoId="r1"
        onSelectRepo={() => {}}
        conversations={mockConversations}
        activeConvId="c1"
        onSelectConv={() => {}}
        onNewConv={() => {}}
        onDeleteConv={() => {}}
        showCollapseButton={true}
        onCollapse={onCollapse}
      />
    );

    const collapseBtn = screen.getByLabelText(/Collapse Chat History/i);
    expect(collapseBtn).toBeDefined();
    fireEvent.click(collapseBtn);
    expect(onCollapse).toHaveBeenCalledTimes(1);
  });
});
