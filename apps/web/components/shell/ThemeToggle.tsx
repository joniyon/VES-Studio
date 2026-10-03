"use client";

import { useEffect } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tip } from "@/components/ui/tooltip";

/** Follows the system until the user picks a theme; an explicit choice is kept in localStorage. */
export function ThemeToggle() {
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => {
      try { if (localStorage.getItem("ves-theme")) return; } catch {}
      document.documentElement.classList.toggle("dark", e.matches);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  const toggle = () => {
    const dark = document.documentElement.classList.toggle("dark");
    try { localStorage.setItem("ves-theme", dark ? "dark" : "light"); } catch {}
  };
  return (
    <Tip label="Toggle light / dark theme">
      <Button variant="ghost" size="icon-sm" onClick={toggle} aria-label="Toggle theme">
        <Sun className="hidden size-4 dark:block" />
        <Moon className="size-4 dark:hidden" />
      </Button>
    </Tip>
  );
}
