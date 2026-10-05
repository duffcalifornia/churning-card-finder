import { useEffect, useRef, useState } from "react";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/react";
import type { Profile } from "./engine/types";
import type { RankBy } from "./engine/recommend";
import { defaultProfile, parseStoredProfile } from "./state/profile";
import { PlayersStep } from "./ui/PlayersStep";
import { HistoryStep } from "./ui/HistoryStep";
import { QuestionsStep } from "./ui/QuestionsStep";
import { HouseholdStep } from "./ui/HouseholdStep";
import { ResultsStep } from "./ui/ResultsStep";
import { MethodologyPage } from "./ui/MethodologyPage";
import { HomePage } from "./ui/HomePage";
import { CheatSheetPage } from "./ui/CheatSheetPage";
import { ChangelogPage } from "./ui/ChangelogPage";
import { SuggestionsPage } from "./ui/SuggestionsPage";
import { ReferralsPage, BMAC_URL } from "./ui/ReferralsPage";
import { CHEAT_SHEET_PRESETS } from "./state/cheatSheetPresets";
import { cheatSheetPresetPath, presetIdFromPath } from "./ui/cheatSheetSeo";

const STORAGE_KEY = "churning-card-finder:profile:v1";
const RANK_KEY = "churning-card-finder:rankBy:v1";
const FOOTER_COLLAPSED_KEY = "churning-card-finder:footerCollapsed:v1";
const WIZARD_STEPS = ["People", "Card history", "About you", "Spending", "Your cards"];

type Page = "home" | "cheatsheet" | "finder" | "methodology" | "changelog" | "suggestions" | "referrals";

// Every destination's hash, including "referrals", which is deliberately left out of NAV (below) so it only
// shows up in the footer and isn't part of the site's visible navigation.
const PAGE_HASHES: Record<Page, string> = {
  home: "",
  cheatsheet: "#cheatsheet",
  finder: "#finder",
  methodology: "#methodology",
  changelog: "#changelog",
  suggestions: "#suggestions",
  referrals: "#referrals",
};

const NAV: { page: Page; label: string }[] = [
  { page: "home", label: "Home" },
  { page: "cheatsheet", label: "Signup Offer Cheat Sheet" },
  { page: "finder", label: "Card Finder" },
  { page: "methodology", label: "Ranking Methodology" },
  { page: "changelog", label: "Changelog" },
  { page: "suggestions", label: "Suggestions" },
];

// Browser storage can be missing or blocked (private windows), so every use is guarded and the site works without it.
function loadProfile(): Profile {
  try {
    return parseStoredProfile(localStorage.getItem(STORAGE_KEY)) ?? defaultProfile(1);
  } catch {
    return defaultProfile(1);
  }
}

function loadRankBy(): RankBy {
  try {
    return localStorage.getItem(RANK_KEY) === "raw" ? "raw" : "net";
  } catch {
    return "net";
  }
}

// Session-only (not localStorage): collapsing the footer to reclaim mobile screen space is remembered for the
// rest of this browsing session, but a new visit starts with it expanded again — someone who collapses it once
// should not have "support this project" quietly hidden from them forever.
function loadFooterCollapsed(): boolean {
  try {
    return sessionStorage.getItem(FOOTER_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

// Every destination is a plain hash (home is no hash), so every one of them, including the unlisted referrals
// page, can be linked to and bookmarked directly, without pulling in a router.
function pageFromHash(): Page {
  const hash = window.location.hash;
  const entry = (Object.entries(PAGE_HASHES) as [Page, string][]).find(([, h]) => h === hash && h !== "");
  return entry?.[0] ?? "home";
}

// The cheat sheet is the one exception to "every page is a hash": its four presets get real, indexable URLs
// (/cheatsheet/<preset>) instead, since that's the one page whose content directly matches how people phrase
// these searches ("best cash back card under 5/24") - a hash fragment never reaches the server, so Google treats
// every #hash page as the same URL as the homepage, which is fine for pages nobody searches for by name but
// defeats the purpose here.
//
// A recognized hash wins over a cheat sheet path when both are present, not the other way around: the footer's
// referral link and Methodology's "back" link are plain <a href="#..."> tags rendered on every page, including
// the cheat sheet, and a plain hash link click only ever changes the hash - clicking one while on
// /cheatsheet/under-travel lands on /cheatsheet/under-travel#referrals, leaving that pathname stale. If the
// pathname were checked first, that click would silently do nothing (still "cheatsheet", still that preset)
// instead of going to Referrals.
function deriveCurrentPage(): { page: Page; cheatSheetPreset: string } {
  const hashPage = pageFromHash();
  if (window.location.hash && hashPage !== "home") return { page: hashPage, cheatSheetPreset: CHEAT_SHEET_PRESETS[0]!.id };
  const presetFromPath = presetIdFromPath(window.location.pathname);
  if (presetFromPath !== null) return { page: "cheatsheet", cheatSheetPreset: presetFromPath };
  return { page: "home", cheatSheetPreset: CHEAT_SHEET_PRESETS[0]!.id };
}

// Every non-cheat-sheet page's target URL is "/" plus its hash (home's hash is "", so this is just "/" for home).
// Kept as one real pathname ("/") throughout so that navigating between these pages from a cheat sheet URL
// correctly leaves the cheat sheet's own path behind, rather than stacking a hash onto it.
function urlForPage(p: Page): string {
  if (p === "cheatsheet") return cheatSheetPresetPath(CHEAT_SHEET_PRESETS[0]!.id);
  return `/${PAGE_HASHES[p]}`;
}

export function App() {
  const [profile, setProfile] = useState<Profile>(loadProfile);
  const [rankBy, setRankBy] = useState<RankBy>(loadRankBy);
  const [step, setStep] = useState(0);
  const [page, setPage] = useState<Page>(() => deriveCurrentPage().page);
  const [cheatSheetPreset, setCheatSheetPreset] = useState<string>(() => deriveCurrentPage().cheatSheetPreset);
  const [navOpen, setNavOpen] = useState(false);
  const [footerCollapsed, setFooterCollapsed] = useState(loadFooterCollapsed);

  // Two listeners, for two different kinds of navigation this page never fully controls:
  // - hashchange: a plain <a href="#..."> click (the footer's referrals link, Methodology's "back" link) changes
  //   only the hash, without going through goToPage, and fires this event but never popstate.
  // - popstate: the browser's own back/forward buttons, which is how a cheat sheet URL (set via history.pushState
  //   in goToPage/goToCheatSheetPreset below, which never fires either event on its own tab) is ever revisited.
  // Both re-derive from scratch rather than assuming which one fired for which reason, since either can in
  // principle leave the address bar pointing at a cheat sheet path or a hash page.
  useEffect(() => {
    const onNavigation = () => {
      const derived = deriveCurrentPage();
      setPage(derived.page);
      setCheatSheetPreset(derived.cheatSheetPreset);
    };
    window.addEventListener("hashchange", onNavigation);
    window.addEventListener("popstate", onNavigation);
    return () => {
      window.removeEventListener("hashchange", onNavigation);
      window.removeEventListener("popstate", onNavigation);
    };
  }, []);

  // The footer stays fixed to the bottom of the viewport everywhere except the questionnaire steps of the Card
  // Finder (People through Spending), which are already dense with inputs and need the space; it reappears once
  // the results step generates a list.
  const footerFixed = !(page === "finder" && step < WIZARD_STEPS.length - 1);
  const footerRef = useRef<HTMLElement>(null);
  const [footerHeight, setFooterHeight] = useState(0);
  useEffect(() => {
    const el = footerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setFooterHeight(el.getBoundingClientRect().height));
    ro.observe(el);
    return () => ro.disconnect();
  }, [footerFixed]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
    } catch {
      /* storage unavailable: the answers simply are not remembered */
    }
  }, [profile]);

  useEffect(() => {
    try {
      localStorage.setItem(RANK_KEY, rankBy);
    } catch {
      /* storage unavailable */
    }
  }, [rankBy]);

  useEffect(() => {
    try {
      sessionStorage.setItem(FOOTER_COLLAPSED_KEY, footerCollapsed ? "1" : "0");
    } catch {
      /* storage unavailable */
    }
  }, [footerCollapsed]);

  const goToPage = (p: Page) => {
    const url = urlForPage(p);
    // pushState never fires hashchange or popstate on its own tab (only back/forward does), so state is always
    // set directly here rather than waiting on an event - unlike the old hash-only version of this function, which
    // relied on hashchange firing and had to special-case "already at this hash" for when it wouldn't.
    if (`${window.location.pathname}${window.location.hash}` !== url) history.pushState(null, "", url);
    setPage(p);
    if (p === "cheatsheet") setCheatSheetPreset(CHEAT_SHEET_PRESETS[0]!.id);
    window.scrollTo(0, 0);
    setNavOpen(false); // closes the mobile hamburger menu; a no-op on desktop, where it is always open
  };
  const goToCheatSheetPreset = (presetId: string) => {
    // replaceState, not pushState: switching between the cheat sheet's four presets is one logical "stop" for the
    // back button, not four. Landing on the cheat sheet at all (goToPage, above) still pushes - that's a real
    // navigation, from Home or the nav bar - but flipping through presets once you're there shouldn't make back
    // walk through every preset you looked at before it takes you back to wherever you actually came from
    // (including off-site, if you arrived via a search result straight onto one preset's own URL).
    const url = cheatSheetPresetPath(presetId);
    if (window.location.pathname !== url) history.replaceState(null, "", url);
    setPage("cheatsheet");
    setCheatSheetPreset(presetId);
    window.scrollTo(0, 0);
  };
  const goToStep = (n: number) => {
    setStep(n);
    window.scrollTo(0, 0);
  };
  const startOver = () => {
    setProfile(defaultProfile(1));
    goToStep(0);
  };

  return (
    <main>
      <Analytics />
      <SpeedInsights />
      <a href="#main-content" className="skip-link">Skip to content</a>

      <header>
        <h1>Which credit card should I get?</h1>
        <p className="tagline">A free, impartial, logic based tool for determining which credit card to apply for.</p>
        <button
          type="button"
          className="hamburger"
          aria-label={navOpen ? "Close menu" : "Menu"}
          aria-expanded={navOpen}
          aria-controls="site-nav-list"
          onClick={() => setNavOpen((v) => !v)}
        >
          <span className="hamburger-icon" aria-hidden="true" />
        </button>

        {/* Nested inside header (rather than a header sibling) so the dropdown, on mobile, can be positioned
            relative to header and drop straight down from the button instead of from below the tagline text. */}
        <nav aria-label="Site">
          <ol id="site-nav-list" className={navOpen ? "steps open" : "steps"}>
            {NAV.map((n) => (
              <li key={n.page}>
                <button type="button" className={n.page === page ? "step current" : "step"} aria-current={n.page === page ? "page" : undefined} onClick={() => goToPage(n.page)}>
                  {n.label}
                </button>
              </li>
            ))}
          </ol>
        </nav>
      </header>

      <div id="main-content" style={footerFixed ? { paddingBottom: footerHeight + 16 } : undefined}>
        {page === "home" && <HomePage onGoToCheatSheet={() => goToPage("cheatsheet")} onGoToFinder={() => goToPage("finder")} />}

        {page === "cheatsheet" && (
          <CheatSheetPage
            rankBy={rankBy}
            onRankByChange={setRankBy}
            onGoToFinder={() => goToPage("finder")}
            selectedPreset={cheatSheetPreset}
            onPresetChange={goToCheatSheetPreset}
          />
        )}

        {page === "methodology" && <MethodologyPage />}

        {page === "changelog" && <ChangelogPage />}

        {page === "suggestions" && <SuggestionsPage />}

        {page === "referrals" && <ReferralsPage />}

        {page === "finder" && (
          <>
            <nav aria-label="Steps">
              <ol className="steps substeps">
                {WIZARD_STEPS.map((name, i) => (
                  <li key={name}>
                    <button type="button" className={i === step ? "step current" : "step"} aria-current={i === step ? "step" : undefined} onClick={() => goToStep(i)}>
                      <span className="num">{i + 1}</span> {name}
                    </button>
                  </li>
                ))}
              </ol>
            </nav>

            {step === 0 && <PlayersStep profile={profile} onChange={setProfile} />}
            {step === 1 && <HistoryStep profile={profile} onChange={setProfile} />}
            {step === 2 && <QuestionsStep profile={profile} onChange={setProfile} />}
            {step === 3 && <HouseholdStep profile={profile} onChange={setProfile} />}
            {step === 4 && <ResultsStep profile={profile} rankBy={rankBy} onRankByChange={setRankBy} />}

            <div className="buttons">
              {step > 0 && <button type="button" className="secondary" onClick={() => goToStep(step - 1)}>Back</button>}
              {step < WIZARD_STEPS.length - 1 && <button type="button" className="primary" onClick={() => goToStep(step + 1)}>Next</button>}
              {step === WIZARD_STEPS.length - 1 && <button type="button" className="secondary" onClick={startOver}>Start over</button>}
            </div>
          </>
        )}
      </div>

      <footer ref={footerRef} className={[footerFixed && "footer-fixed", footerCollapsed && "collapsed"].filter(Boolean).join(" ") || undefined}>
        {/* Only shown (see .footer-toggle in styles.css) at the same narrow widths where a fixed footer costs
            real screen space; collapsing is remembered for this browsing session only (see loadFooterCollapsed). */}
        <button type="button" className="footer-toggle" aria-expanded={!footerCollapsed} onClick={() => setFooterCollapsed((v) => !v)}>
          {footerCollapsed ? "Show footer" : "Hide footer"}
        </button>
        <div className="footer-body">
          <p>
            The information presented on this site does not constitute financial advice. Please use credit cards responsibly. Card offers and bank rules can change; check the issuer before you apply.{" "}
            <span className="footerlinks">
              If you want to support this project, you can{" "}
              <a href={BMAC_URL} target="_blank" rel="noreferrer">buy me a coffee</a>
            </span>
          </p>
        </div>
      </footer>
    </main>
  );
}
