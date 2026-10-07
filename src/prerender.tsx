import { renderToString } from "react-dom/server";
import { App } from "./App";
import { engineData } from "./data/engineData";
import { CHEAT_SHEET_PRESETS, rankForPreset } from "./state/cheatSheetPresets";
import { cheatSheetPresetPath, seoForPreset } from "./ui/cheatSheetSeo";
import { oldestVerifiedOn } from "./ui/staleness";

/**
 * Build-time prerendering (see scripts/prerender.mjs): the homepage and the four cheat sheet pages are written out
 * as static HTML with their real content, so a crawler (or a link preview, or a slow connection) sees card names
 * and values without running any JavaScript. The browser still boots the normal app on top of it afterwards.
 * Everything else on the site is a hash on "/" and so shares the homepage's URL; there is nothing to prerender.
 */
export const SITE_URL = "https://www.whichcreditcardshouldiget.com";
const HOME_TITLE = "Which card should I get? | r/churning card finder";
const HOME_DESCRIPTION =
  "A free, impartial, logic based tool for determining which credit card to apply for. A deterministic rules engine ranks welcome-bonus credit cards by value, based on your real card history and 5/24, lifetime, and family rules.";

export interface PageHead {
  path: string;
  title: string;
  description: string;
  jsonLd: object[];
}

/** The newest date anything on the site was reviewed: the honest "last modified" for the sitemap. */
export function newestVerifiedOn(): string {
  const dates = [...engineData.catalog.map((c) => c.verifiedOn), engineData.valuations.verifiedOn].filter(Boolean) as string[];
  return dates.reduce((a, b) => (a > b ? a : b));
}

export function prerenderedPaths(): string[] {
  return ["/", ...CHEAT_SHEET_PRESETS.map((p) => cheatSheetPresetPath(p.id))];
}

export function headFor(path: string): PageHead {
  const website = { "@context": "https://schema.org", "@type": "WebSite", name: "Which Credit Card Should I Get", url: `${SITE_URL}/` };
  if (path === "/") {
    return {
      path, title: HOME_TITLE, description: HOME_DESCRIPTION,
      jsonLd: [
        website,
        {
          "@context": "https://schema.org", "@type": "WebApplication", name: "Which Credit Card Should I Get",
          url: `${SITE_URL}/`, applicationCategory: "FinanceApplication", operatingSystem: "Any",
          description: HOME_DESCRIPTION, offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        },
      ],
    };
  }
  const preset = CHEAT_SHEET_PRESETS.find((p) => cheatSheetPresetPath(p.id) === path)!;
  const seo = seoForPreset(preset.id);
  const ranked = rankForPreset(preset, engineData, "net");
  return {
    path, title: seo.title, description: seo.description,
    jsonLd: [
      {
        "@context": "https://schema.org", "@type": "WebPage", name: seo.title, description: seo.description,
        url: `${SITE_URL}${path}`, dateModified: newestVerifiedOn(), isPartOf: { "@type": "WebSite", url: `${SITE_URL}/` },
      },
      {
        "@context": "https://schema.org", "@type": "ItemList", name: preset.label,
        itemListElement: ranked.slice(0, 10).map((e, i) => ({
          "@type": "ListItem", position: i + 1,
          name: engineData.catalog.find((c) => c.id === e.cardId)!.name,
        })),
      },
    ],
  };
}

/** The app's own markup for a path, rendered the way the browser's first paint would be (default rank-by). */
export function renderBody(path: string): string {
  // App reads window.location while choosing its first page; only the pathname and hash matter here. Everything
  // else it touches during a render (localStorage, sessionStorage) is already guarded for being unavailable.
  const g = globalThis as unknown as { window?: unknown };
  const previous = g.window;
  g.window = { location: { pathname: path, hash: "", search: "" } };
  try {
    return renderToString(<App />);
  } finally {
    if (previous === undefined) delete g.window;
    else g.window = previous;
  }
}

export function sitemapXml(): string {
  const lastmod = newestVerifiedOn();
  const urls = prerenderedPaths().map((p) => `  <url>\n    <loc>${SITE_URL}${p === "/" ? "/" : p}</loc>\n    <lastmod>${lastmod}</lastmod>\n  </url>`);
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join("\n")}\n</urlset>\n`;
}

export { oldestVerifiedOn };
