interface Props {
  onGoToCheatSheet: () => void;
  onGoToFinder: () => void;
}

export function HomePage({ onGoToCheatSheet, onGoToFinder }: Props) {
  return (
    <section>
      <p>
        Most credit card sites push cards that make them money rather than what fits your needs. This site is
        different: no affiliate links or sponsored placement influences the rankings you see in any way. It's
        free, and it always will be. To learn how the cards get ranked, see the{" "}
        <a href="#methodology">Ranking Methodology</a> page.
      </p>

      <h2>Two ways to use this site</h2>
      <p>
        Both are built on the same rules engine and the same card data, but the difference is how much they know about
        you. Pick whichever fits what you need right now.
      </p>

      <div className="homecards">
        <div className="homecard">
          <h3>Signup Offer Cheat Sheet</h3>
          <p>
            A fast reference: four lists, split by 5/24 status and reward type, each showing every card.
            It assumes you've never had any of them and can meet any minimum spend. Good if you already know your own
            situation and just want the generic answer to start from.
          </p>
          <button type="button" className="primary" onClick={onGoToCheatSheet}>Open the Cheat Sheet</button>
        </div>
        <div className="homecard">
          <h3>Card Finder</h3>
          <p>
            Tell it your (or your household's) real card history, spending ability, and preferences, and it shows
            you the most valuable cards to apply for right now while taking all applicable bank rules into
            account. Your information never leaves your web browser.
          </p>
          <button type="button" className="primary" onClick={onGoToFinder}>Start the Card Finder</button>
        </div>
      </div>
    </section>
  );
}
