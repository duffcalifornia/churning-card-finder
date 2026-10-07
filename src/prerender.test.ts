import { describe, expect, it } from "vitest";
import { headFor, newestVerifiedOn, prerenderedPaths, renderBody, sitemapXml } from "./prerender";
import { CHEAT_SHEET_PRESETS } from "./state/cheatSheetPresets";

describe("prerendering", () => {
  it("covers the homepage and exactly the cheat sheet's presets", () => {
    expect(prerenderedPaths()).toEqual(["/", ...CHEAT_SHEET_PRESETS.map((p) => `/cheatsheet/${p.id}`)]);
  });

  it("renders real card content for a cheat sheet page, with no global window left behind", () => {
    const html = renderBody("/cheatsheet/under-cashback");
    expect(html).toContain("Signup Offer Cheat Sheet");
    expect(html).toContain("resultcard");
    expect((globalThis as { window?: unknown }).window).toBeUndefined();
  });

  it("renders the homepage's own content at /", () => {
    expect(renderBody("/")).toContain("Two ways to use this site");
  });

  it("gives each cheat sheet page its own title and an ItemList of its top cards", () => {
    const heads = prerenderedPaths().filter((p) => p !== "/").map(headFor);
    expect(new Set(heads.map((h) => h.title)).size).toBe(heads.length);
    for (const h of heads) {
      const list = h.jsonLd.find((o) => (o as { "@type": string })["@type"] === "ItemList") as { itemListElement: unknown[] };
      expect(list.itemListElement.length).toBeGreaterThan(0);
    }
  });

  it("describes the homepage as a free web application", () => {
    const types = headFor("/").jsonLd.map((o) => (o as { "@type": string })["@type"]);
    expect(types).toEqual(["WebSite", "WebApplication"]);
  });

  it("lists every prerendered URL in the sitemap with a real lastmod date", () => {
    const xml = sitemapXml();
    for (const p of prerenderedPaths()) expect(xml).toContain(`<loc>https://www.whichcreditcardshouldiget.com${p}</loc>`);
    expect(newestVerifiedOn()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(xml).toContain(`<lastmod>${newestVerifiedOn()}</lastmod>`);
  });
});
