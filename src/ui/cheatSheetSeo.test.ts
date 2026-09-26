import { describe, expect, it } from "vitest";
import { CHEAT_SHEET_PRESETS } from "../state/cheatSheetPresets";
import { cheatSheetPresetPath, presetIdFromPath, seoForPreset } from "./cheatSheetSeo";

describe("cheatSheetPresetPath", () => {
  it("builds a path under /cheatsheet for a preset id", () => {
    expect(cheatSheetPresetPath("under-cashback")).toBe("/cheatsheet/under-cashback");
  });
});

describe("presetIdFromPath", () => {
  it("returns null for a path that isn't a cheat sheet path at all", () => {
    expect(presetIdFromPath("/")).toBeNull();
    expect(presetIdFromPath("/finder")).toBeNull();
  });

  it("returns the first preset's id for the bare /cheatsheet path (with or without a trailing slash)", () => {
    expect(presetIdFromPath("/cheatsheet")).toBe(CHEAT_SHEET_PRESETS[0]!.id);
    expect(presetIdFromPath("/cheatsheet/")).toBe(CHEAT_SHEET_PRESETS[0]!.id);
  });

  it("returns the matching preset id for each real preset path", () => {
    for (const preset of CHEAT_SHEET_PRESETS) {
      expect(presetIdFromPath(`/cheatsheet/${preset.id}`)).toBe(preset.id);
    }
  });

  it("falls back to the first preset for an unrecognized sub-path instead of returning null", () => {
    // A typo, or a bookmark to a preset that's since been removed, still lands on the cheat sheet rather than
    // falling through to the site's hash routing (which would show the homepage under a /cheatsheet/whatever URL).
    expect(presetIdFromPath("/cheatsheet/not-a-real-preset")).toBe(CHEAT_SHEET_PRESETS[0]!.id);
  });

  it("does not match a path that merely starts with /cheatsheet as a prefix of a different route", () => {
    expect(presetIdFromPath("/cheatsheetsomethingelse")).toBeNull();
  });
});

describe("seoForPreset", () => {
  it("gives every real preset a distinct, non-empty title and description", () => {
    const seen = new Set<string>();
    for (const preset of CHEAT_SHEET_PRESETS) {
      const seo = seoForPreset(preset.id);
      expect(seo.title.length).toBeGreaterThan(0);
      expect(seo.description.length).toBeGreaterThan(0);
      expect(seen.has(seo.title)).toBe(false);
      seen.add(seo.title);
    }
  });

  it("falls back to a generic title for an unrecognized id, rather than throwing", () => {
    expect(() => seoForPreset("not-a-real-preset")).not.toThrow();
    expect(seoForPreset("not-a-real-preset").title).toContain("Signup Offer Cheat Sheet");
  });
});
