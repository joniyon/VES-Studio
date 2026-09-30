"use client";

import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

export type Option = { value: string; label: string };

/** Small labelled-option wrapper around shadcn Select (Base UI needs `items` to show labels). */
export function Pick({
  value, onChange, options, className, placeholder, label,
}: {
  value: string;
  onChange: (v: string) => void;
  options: Option[];
  className?: string;
  placeholder?: string;
  label?: string;
}) {
  return (
    <Select value={value} onValueChange={(v) => v != null && onChange(String(v))} items={options}>
      <SelectTrigger className={className} aria-label={label}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
