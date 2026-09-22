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

const STORAGE_KEY = "churning-card-finder:profile:v1";
const RANK_KEY = "churning-card-finder:rankBy:v1";
const STEPS = ["People", "Card history", "About you", "Spending", "Your cards"];

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

// The Methodology page is a second, static "page" alongside the wizard, reachable by a plain link (#methodology) so
// it can be shared and bookmarked, without pulling in a router for what is otherwise a single-page wizard.
function isMethodologyHash(): boolean {
  return window.location.hash === "#methodology";
}

export function App() {
  const [profile, setProfile] = useState<Profile>(loadProfile);
  const [rankBy, setRankBy] = useState<RankBy>(loadRankBy);
  const [step, setStep] = useState(0);
  const [showMethodology, setShowMethodology] = useState(isMethodologyHash);

  useEffect(() => {
    const onHashChange = () => setShowMethodology(isMethodologyHash());
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

  const go = (n: number) => {
    setStep(n);
    window.scrollTo(0, 0);
  };
  const startOver = () => {
    setProfile(defaultProfile(1));
    go(0);
  };

  return (
    <main>
      <header>
        <h1>Which credit card should I get?</h1>
        <p className="tagline">A free tool for r/churning that replaces the credit card recommendation flowchart.</p>
      </header>

      {showMethodology ? (
        <MethodologyPage />
      ) : (
        <>
          <nav aria-label="Steps">
            <ol className="steps">
              {STEPS.map((name, i) => (
                <li key={name}>
                  <button type="button" className={i === step ? "step current" : "step"} aria-current={i === step ? "step" : undefined} onClick={() => go(i)}>
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
            {step > 0 && <button type="button" className="secondary" onClick={() => go(step - 1)}>Back</button>}
            {step < STEPS.length - 1 && <button type="button" className="primary" onClick={() => go(step + 1)}>Next</button>}
            {step === STEPS.length - 1 && <button type="button" className="secondary" onClick={startOver}>Start over</button>}
          </div>
        </>
      )}

      <footer>
        Based on the r/churning credit card recommendation flowchart. Not financial advice. Card offers and bank rules change often; check the issuer before you apply.
        {" "}<a href="#methodology">Ranking Methodology</a>.
      </footer>
    </main>
  );
}
