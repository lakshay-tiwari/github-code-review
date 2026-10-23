"use client";

import * as React from "react";
import { GripVertical } from "lucide-react";
import * as ResizablePrimitive from "react-resizable-panels";
import { cn } from "@/lib/utils";

const ResizablePanelGroup = ({
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.PanelGroup>) => (
  <ResizablePrimitive.PanelGroup
    className={cn(
      "flex h-full w-full data-[panel-group-direction=vertical]:flex-col",
      className
    )}
    {...props}
  />
);

const ResizablePanel = ResizablePrimitive.Panel;

const ResizableHandle = ({
  withHandle,
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.PanelResizeHandle> & {
  withHandle?: boolean;
}) => (
  <ResizablePrimitive.PanelResizeHandle
    className={cn(
      "relative flex w-[1px] items-center justify-center bg-slate-200/90 hover:bg-indigo-500/80 active:bg-indigo-500 dark:bg-zinc-800 dark:hover:bg-indigo-500/80 dark:active:bg-indigo-500 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-500 data-[panel-group-direction=vertical]:h-[1px] data-[panel-group-direction=vertical]:w-full after:absolute after:inset-y-0 after:left-1/2 after:w-3 after:-translate-x-1/2 data-[panel-group-direction=vertical]:after:left-0 data-[panel-group-direction=vertical]:after:h-3 data-[panel-group-direction=vertical]:after:w-full data-[panel-group-direction=vertical]:after:-translate-y-1/2 data-[panel-group-direction=vertical]:after:translate-x-0 cursor-col-resize data-[panel-group-direction=vertical]:cursor-row-resize select-none shrink-0",
      className
    )}
    {...props}
  >
    {withHandle && (
      <div className="z-10 flex h-6 w-3 items-center justify-center rounded-sm border border-slate-300/80 bg-white shadow-xs dark:border-zinc-700 dark:bg-zinc-900 transition-colors hover:border-indigo-400">
        <GripVertical className="h-2.5 w-2.5 text-slate-400 dark:text-zinc-400" />
      </div>
    )}
  </ResizablePrimitive.PanelResizeHandle>
);

export { ResizablePanelGroup, ResizablePanel, ResizableHandle };
