import { ChevronRight } from "lucide-react";

/** Breadcrumb plus empty pill slots (actions arrive in a later stage). */
export function SubBar({ projectName, stationId, runLabel }: { projectName: string; stationId: string; runLabel: string | null }) {
  const crumbs = [projectName || "Untitled project", stationId || "No station", runLabel ?? "No run"];
  return (
    <div className="flex h-10 shrink-0 items-center justify-between gap-3 border-b bg-background px-3">
      <nav aria-label="Breadcrumb" className="min-w-0">
        <ol className="flex items-center gap-1 text-xs text-muted-foreground">
          {crumbs.map((c, i) => (
            <li key={i} className="flex min-w-0 items-center gap-1">
              {i > 0 && <ChevronRight className="size-3 shrink-0" aria-hidden />}
              <span className={i === crumbs.length - 1 ? "truncate font-medium text-foreground" : "truncate"} aria-current={i === crumbs.length - 1 ? "page" : undefined}>{c}</span>
            </li>
          ))}
        </ol>
      </nav>
      <div className="flex items-center gap-2 max-sm:hidden" aria-hidden>
        <span className="h-6 w-20 rounded-full border border-dashed" />
        <span className="h-6 w-20 rounded-full border border-dashed" />
      </div>
    </div>
  );
}
