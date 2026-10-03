"use client"

import * as React from "react"
import { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip"
import { cn } from "@/lib/utils"

function TooltipProvider({ delay = 300, ...props }: TooltipPrimitive.Provider.Props) {
  return <TooltipPrimitive.Provider data-slot="tooltip-provider" delay={delay} {...props} />
}

/** Shows `label` (and an optional keyboard-shortcut chip) on hover and keyboard focus of its single child. */
function Tip({
  label, shortcut, side = "bottom", children,
}: {
  label: React.ReactNode
  shortcut?: string
  side?: "top" | "bottom" | "left" | "right"
  children: React.ReactElement<Record<string, unknown>>
}) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger render={children} />
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Positioner side={side} sideOffset={8} className="z-50">
          <TooltipPrimitive.Popup
            data-slot="tooltip-content"
            className={cn(
              "flex max-w-64 items-center gap-2 rounded-md bg-foreground px-2 py-1 text-xs text-background shadow-[var(--shadow-float)]",
              "origin-(--transform-origin) transition-[opacity,transform] duration-150 data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0"
            )}
          >
            <span>{label}</span>
            {shortcut && <kbd className="rounded border border-background/30 px-1 font-mono text-[10px] opacity-80">{shortcut}</kbd>}
          </TooltipPrimitive.Popup>
        </TooltipPrimitive.Positioner>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  )
}

export { TooltipProvider, Tip }
