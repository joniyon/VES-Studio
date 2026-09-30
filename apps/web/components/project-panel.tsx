"use client";

import { FolderOpen, Download, FilePlus2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { HistoryEvent, ProjectMeta, StationMeta } from "@/lib/project";
import { Pick } from "./pick";

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-2">
      <Label className="grid gap-2">
        <span>{label}</span>
        {children}
      </Label>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

export function ProjectPanel({
  project, station, errors, history, onProject, onStation, onNew, onImport, onExportFile,
}: {
  project: ProjectMeta;
  station: StationMeta;
  errors: Record<string, string>;
  history: HistoryEvent[];
  onProject: (p: ProjectMeta) => void;
  onStation: (s: StationMeta) => void;
  onNew: () => void;
  onImport: (f: File | undefined) => void;
  onExportFile: () => void;
}) {
  const P = (k: keyof ProjectMeta) => ({
    value: project[k], onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onProject({ ...project, [k]: e.target.value }),
  });
  const S = (k: keyof StationMeta) => ({
    value: station[k], onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onStation({ ...station, [k]: e.target.value }),
  });
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Project</CardTitle>
          <CardDescription>Saved automatically in this browser. Use a project file to move or back it up.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <Field label="Project name"><Input placeholder="Araromi VES Survey" {...P("name")} /></Field>
          <Field label="Location"><Input placeholder="Araromi, Ondo State, Nigeria" {...P("location")} /></Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Client / organisation"><Input {...P("client")} /></Field>
            <Field label="Researcher"><Input {...P("researcher")} /></Field>
            <Field label="Survey date"><Input type="date" {...P("survey_date")} /></Field>
            <Field label="Status">
              <Pick label="Status" value={project.status} onChange={(v) => onProject({ ...project, status: v })}
                options={["Draft", "In progress", "Complete"].map((s) => ({ value: s, label: s }))} />
            </Field>
          </div>
          <Field label="Description"><Textarea rows={2} {...P("description")} /></Field>
          <Field label="Notes"><Textarea rows={2} {...P("notes")} /></Field>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button variant="outline" size="sm" onClick={onExportFile}><Download /> Save project file</Button>
            <Button variant="outline" size="sm" nativeButton={false} render={<label />}>
              <FolderOpen /> Open project file
              <input type="file" accept=".json,.ves.json" className="sr-only" onChange={(e) => { onImport(e.target.files?.[0]); e.target.value = ""; }} />
            </Button>
            <Button variant="outline" size="sm" onClick={onNew}><FilePlus2 /> New project</Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid content-start gap-4">
        <Card>
          <CardHeader>
            <CardTitle>VES station</CardTitle>
            <CardDescription>One station per project in V1; multiple stations arrive in V2.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Station ID" error={errors.id}><Input {...S("id")} /></Field>
              <Field label="Survey date"><Input type="date" {...S("survey_date")} /></Field>
              <Field label="Latitude (°)" error={errors.latitude}><Input inputMode="decimal" placeholder="7.2" {...S("latitude")} /></Field>
              <Field label="Longitude (°)" error={errors.longitude}><Input inputMode="decimal" placeholder="5.2" {...S("longitude")} /></Field>
              <Field label="Elevation (m)" error={errors.elevation}><Input inputMode="decimal" {...S("elevation")} /></Field>
            </div>
            <Field label="Location description"><Input {...S("location_description")} /></Field>
            <Field label="Notes"><Textarea rows={2} {...S("notes")} /></Field>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Processing history</CardTitle>
            <CardDescription>What was done to this data, in order.</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-40">
              {history.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nothing yet.</p>
              ) : (
                <ol className="grid gap-1.5 pr-3 text-xs">
                  {history.map((h, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="shrink-0 text-muted-foreground">{h.t.slice(11, 19)}</span>
                      <span>{h.text}</span>
                    </li>
                  ))}
                </ol>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
