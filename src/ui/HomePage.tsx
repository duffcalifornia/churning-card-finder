import { CompassIcon, ListIcon } from "./icons";

interface Props {
  onGoToCheatSheet: () => void;
  onGoToFinder: () => void;
}

export function HomePage({ onGoToCheatSheet, onGoToFinder }: Props) {
  return (
    <section>
      <h2>Two ways to use this site</h2>
      <p>
        Both are built on the same rules engine and the same card data — the difference is how much they know about
        you. Pick whichever fits what you need right now.
      </p>

      <div className="homecards">
        <div className="homecard">
          <div className="homecard-icon"><ListIcon /></div>
          <h3>Signup Offer Cheat Sheet</h3>
          <p>
            A fast reference: four lists, split by 5/24 status and reward type, each showing every eligible card
            assuming you've never had any of them and can meet any minimum spend. Good if you already know your own
            situation and just want the generic answer to start from.
          </p>
          <button type="button" className="primary" onClick={onGoToCheatSheet}>Open the Cheat Sheet</button>
        </div>
        <div className="homecard">
          <div className="homecard-icon"><CompassIcon /></div>
          <h3>Card Finder</h3>
          <p>
            Tell it your (or your household's) real card history, spending, and preferences, and it works out
            exactly which cards you're eligible for right now, accounting for 5/24, lifetime and family rules,
            the Marriott matrix, and more, then ranks them by value.
          </p>
          <button type="button" className="primary" onClick={onGoToFinder}>Start the Card Finder</button>
        </div>
      </div>

      <p className="note">
        Your answers, if you use the Card Finder, stay in this browser only. Nothing is sent to a server. See the{" "}
        <a href="#methodology">Ranking Methodology</a> page for how cards are valued and which rules are checked.
      </p>
    </section>
  );
}
