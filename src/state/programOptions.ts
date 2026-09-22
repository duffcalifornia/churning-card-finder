import type { Program } from "../engine/types";

export interface ProgramOption {
  /** What is stored in the profile: the program's group if it has one (Avios), otherwise its id. */
  value: string;
  label: string;
  kind: string;
}

/** One checkbox per loyalty program, with programs that are one currency under several names listed once. */
export function programOptions(programs: Program[]): ProgramOption[] {
  const seen = new Map<string, ProgramOption>();
  for (const p of programs) {
    const value = p.group ?? p.id;
    if (!seen.has(value)) seen.set(value, { value, label: p.name, kind: p.kind });
  }
  return [...seen.values()].sort((a, b) => a.kind.localeCompare(b.kind) || a.label.localeCompare(b.label));
}
