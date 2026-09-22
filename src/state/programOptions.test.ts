import { describe, expect, it } from "vitest";
import { programOptions } from "./programOptions";
import type { Program } from "../engine/types";
import programsJson from "../../data/programs.json";

const programs = programsJson as unknown as Program[];

describe("programOptions", () => {
  const options = programOptions(programs);

  it("lists the Avios airlines once, under their group name", () => {
    const avios = options.filter((o) => o.value === "Avios");
    expect(avios).toHaveLength(1);
    expect(options.some((o) => o.value === "avios")).toBe(false);
  });
  it("covers every program", () => {
    for (const p of programs) expect(options.some((o) => o.value === (p.group ?? p.id)), p.id).toBe(true);
  });
  it("has no duplicates", () => {
    expect(new Set(options.map((o) => o.value)).size).toBe(options.length);
  });
  it("puts airlines before hotels, each sorted by name", () => {
    const kinds = options.map((o) => o.kind);
    expect(kinds).toEqual([...kinds].sort());
    const airlines = options.filter((o) => o.kind === "airline").map((o) => o.label);
    expect(airlines).toEqual([...airlines].sort((a, b) => a.localeCompare(b)));
  });
});
