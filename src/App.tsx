import { useEffect, useState } from "react";
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

const STORAGE_KEY = "churning-card-finder:profile:v1";
const RANK_KEY = "churning-card-finder:rankBy:v1";
const WIZARD_STEPS = ["People", "Card history", "About you", "Spending", "Your cards"];

type Page = "home" | "cheatsheet" | "finder" | "methodology";
const NAV: { page: Page; hash: string; label: string }[] = [
  { page: "home", hash: "", label: "Home" },
  { page: "cheatsheet", hash: "#cheatsheet", label: "Signup Offer Cheat Sheet" },
  { page: "finder", hash: "#finder", label: "Card Finder" },
  { page: "methodology", hash: "#methodology", label: "Ranking Methodology" },
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

// Each top-level destination is a plain hash (#cheatsheet, #finder, #methodology; home is no hash), so every one of
// them can be linked to and bookmarked directly, without pulling in a router.
function pageFromHash(): Page {
  const hash = window.location.hash;
  return NAV.find((n) => n.hash === hash && n.hash !== "")?.page ?? "home";
}

export function App() {
  const [profile, setProfile] = useState<Profile>(loadProfile);
  const [rankBy, setRankBy] = useState<RankBy>(loadRankBy);
  const [step, setStep] = useState(0);
  const [page, setPage] = useState<Page>(pageFromHash);

  useEffect(() => {
    const onHashChange = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

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

  const goToPage = (p: Page) => {
    const hash = NAV.find((n) => n.page === p)!.hash;
    if (window.location.hash !== hash) window.location.hash = hash;
    else setPage(p); // same hash as already set: hashchange would not fire, so update directly
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
      <header>
        <h1>Which credit card should I get?</h1>
        <p className="tagline">A free tool for r/churning that replaces the credit card recommendation flowchart.</p>
      </header>

      <nav aria-label="Site">
        <ol className="steps">
          {NAV.map((n) => (
            <li key={n.page}>
              <button type="button" className={n.page === page ? "step current" : "step"} aria-current={n.page === page ? "page" : undefined} onClick={() => goToPage(n.page)}>
                {n.label}
              </button>
            </li>
          ))}
        </ol>
      </nav>

      {page === "home" && <HomePage onGoToCheatSheet={() => goToPage("cheatsheet")} onGoToFinder={() => goToPage("finder")} />}

      {page === "cheatsheet" && <CheatSheetPage rankBy={rankBy} onRankByChange={setRankBy} onGoToFinder={() => goToPage("finder")} />}

      {page === "methodology" && <MethodologyPage />}

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

      <footer>
        Based on the r/churning credit card recommendation flowchart. Not financial advice. Card offers and bank rules change often; check the issuer before you apply.
      </footer>
    </main>
  );
}
