import { CHEAT_SHEET_PRESETS } from "../state/cheatSheetPresets";

/**
 * Real, path-based URLs and per-page titles for the cheat sheet's four presets, so each one is something Google
 * can actually index and rank separately - a hash fragment like #cheatsheet never reaches the server and Google
 * treats it as the same URL as the homepage, and a single shared title/description would leave all four presets
 * competing for the same generic snippet. Scoped to just the cheat sheet: it's the one page on this site whose
 * content directly matches how people actually phrase these searches ("best cash back card under 5/24"), unlike
 * the Card Finder (session-specific results, nothing stable to index) or Methodology (written as "how this tool
 * works", not as a standalone answer to "what is 5/24").
 */
export const CHEATSHEET_BASE_PATH = "/cheatsheet";

export function cheatSheetPresetPath(presetId: string): string {
  return `${CHEATSHEET_BASE_PATH}/${presetId}`;
}

/** The preset id from a URL path, or null if the path isn't a cheat sheet path at all (falls through to the
 * site's normal hash routing). An unrecognized sub-path (a typo, an old bookmark to a removed preset) falls back
 * to the first preset rather than 404ing, same as the bare /cheatsheet path does. */
export function presetIdFromPath(pathname: string): string | null {
  if (pathname === CHEATSHEET_BASE_PATH || pathname === `${CHEATSHEET_BASE_PATH}/`) return CHEAT_SHEET_PRESETS[0]!.id;
  const prefix = `${CHEATSHEET_BASE_PATH}/`;
  if (!pathname.startsWith(prefix)) return null;
  const id = pathname.slice(prefix.length);
  return CHEAT_SHEET_PRESETS.some((p) => p.id === id) ? id : CHEAT_SHEET_PRESETS[0]!.id;
}

const SITE_TITLE = "Which Credit Card Should I Get";

interface PresetSeo {
  title: string;
  description: string;
}

const PRESET_SEO: Record<string, PresetSeo> = {
  "under-cashback": {
    title: `Best Cash Back Credit Card Under 5/24 | ${SITE_TITLE}`,
    description: "The best current cash back credit card sign-up bonus if you're under Chase's 5/24 rule, ranked by real dollar value, not just the headline number.",
  },
  "under-travel": {
    title: `Best Travel Credit Card Under 5/24 | ${SITE_TITLE}`,
    description: "The best current travel credit card sign-up bonus if you're under Chase's 5/24 rule, ranked by real dollar value, not just the headline number.",
  },
  "over-cashback": {
    title: `Best Cash Back Credit Card at 5/24 or Over | ${SITE_TITLE}`,
    description: "The best current cash back credit card sign-up bonus still available once you're at Chase's 5/24 limit or over it, ranked by real dollar value.",
  },
  "over-travel": {
    title: `Best Travel Credit Card at 5/24 or Over | ${SITE_TITLE}`,
    description: "The best current travel credit card sign-up bonus still available once you're at Chase's 5/24 limit or over it, ranked by real dollar value.",
  },
};

export function seoForPreset(presetId: string): PresetSeo {
  return PRESET_SEO[presetId] ?? { title: `Signup Offer Cheat Sheet | ${SITE_TITLE}`, description: "" };
}
