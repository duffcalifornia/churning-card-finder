import { engineData } from "../data/engineData";
import { formatDate, oldestVerifiedOn } from "./staleness";

const FM_RRV = "https://frequentmiler.com/reasonable-redemption-values-rrvs/";
const FM_RULES = "https://frequentmiler.com/complete-guide-to-credit-card-application-rules-by-bank/";
const FLOWCHART = "https://imgur.com/a/r-churning-cc-recommendation-flowchart-june-2025-LjDGPk2";

export function MethodologyPage() {
  const cardsFreshness = oldestVerifiedOn(engineData.catalog);
  const valuesFreshness = engineData.valuations.verifiedOn;

  return (
    <section>
      <h2>Ranking Methodology</h2>

      <p>
        Each card issuer has its own rules about which cards you can be approved for, and when. You don't need to know those
        rules: this site looks at the cards you've already had, works out which cards you're currently eligible for, and
        ranks the eligible ones by the value of their welcome bonus. If you tell it you're targeting a specific points
        program, cards that lead there are moved to the top of the list, even if another card is objectively worth more.
      </p>

      <h3>How a bonus is valued</h3>
      <p>
        A card's bonus value is its points times a cents-per-point value, plus any cash back or statement credit, plus any
        free night certificates, added together. Points are valued using{" "}
        <a href={FM_RRV} target="_blank" rel="noreferrer">Frequent Miler's Reasonable Redemption Values</a>, which the site
        treats as the definitive source; free night certificates use Frequent Miler's own discounted values for them too.
      </p>
      <p>
        The <strong>net value</strong> shown for each card, which the list is ranked by unless you switch to raw value, is the
        bonus value minus what you'd pay in the card's <em>first year</em>: a card whose annual fee is waived the first year
        is ranked as if it had no fee at all, even though the fee returns in later years.
      </p>
      <p>
        Some cards show "as high as" or "up to" on their bonus. That's the issuer's own ceiling for a targeted range, and many
        applicants get less. Those cards are still ranked at their ceiling value, but the list adds one backup card for each
        one you're shown, so you have a real alternative if your own offer comes in lower.
      </p>

      <h3>What this site checks, and what it doesn't</h3>
      <p>
        This list assumes you have an established credit history and an above-average credit score. A thinner credit
        history or a lower score will limit which cards you can be approved for; if you're new to churning, the{" "}
        <a href={FLOWCHART} target="_blank" rel="noreferrer">r/churning flowchart</a>'s own newbie notes and the r/churning
        wiki are a good place to start.
      </p>
      <p>
        Some bank rules depend on windows shorter than this site asks about (days, not months), so they can't be checked
        precisely and aren't built in: Chase's 2 cards per 30 days and 1 business card per 30 days, Amex's 2 cards per 90
        days and 1 charge card per 5 days, Citi's 1 card per 8 days and 2 per 65 days, and Bank of America's 2 cards per 2
        months. Before you apply, check your own history against{" "}
        <a href={FM_RULES} target="_blank" rel="noreferrer">Frequent Miler's guide to application rules by bank</a>, which
        covers these and more.
      </p>

      <details className="issuer">
        <summary>The eligibility rules this site does check</summary>

        <h4>How many cards you can hold or have recently opened</h4>
        <ul>
          <li>Chase: 5 or more of its cards (personal or business) opened in 24 months hides every Chase card; Ink cards use a stricter 3, checked first.</li>
          <li>Barclays: 6 or more cards (any issuer) in 24 months.</li>
          <li>US Bank: 5 or more cards (any issuer) in 12 months.</li>
          <li>Bank of America: more than 6 cards in 12 months with a BoA deposit account, more than 2 without one.</li>
          <li>Amex: 5 open credit cards and 10 open charge cards, counted separately (Schwab and Morgan Stanley Amex-branded cards count too).</li>
          <li>Discover: a wait of 12 months after a first Discover card, and at most 2 held.</li>
          <li>Only Capital One and Discover business cards show up on your personal credit report and count toward the personal-card rules above; every other issuer's business cards don't.</li>
        </ul>

        <h4>Whether you can earn a card's bonus again</h4>
        <ul>
          <li>Chase Sapphire cards, Chase Ink cards, Citi Strata cards, and every Amex card: once you've been approved for one, you can't earn its bonus again (personal and business Sapphire cards are independent of each other).</li>
          <li>Amex family rules: having had a higher card in a family (for example Platinum over Gold, or a higher Delta or Hilton tier) blocks a bonus on a lower one. Amex cards blocked this way, or by the once-ever rule above, still appear on the list marked "via NLL only": they're worth applying for only if you find a targeted offer without that lifetime language.</li>
          <li>Capital One's Venture family (VentureOne, Venture, Venture X) works the same way as Amex's, ordered by annual fee, and Citi and Capital One personal cards separately can't earn a bonus on the exact same card again within 48 months.</li>
          <li>Chase, Southwest, IHG, and Bank of America personal cards: a 24-month wait, either from the bonus (Chase, Southwest, IHG) or from when you last held the exact card (Bank of America). Southwest and IHG personal cards share one clock across their whole family.</li>
          <li>Chase Ink: if you've had an Ink card before, this site asks whether you'd be willing to apply again through a newly formed LLC in a state where that's free or cheap, which gets around the once-ever rule.</li>
        </ul>

        <h4>Marriott cards</h4>
        <p>
          Marriott cards are issued by both Chase and Amex, with an unusually tangled set of rules for which prior Marriott
          card blocks which new one, on 30-day, 90-day, 24-month, or lifetime windows depending on the pair. This site
          encodes that matrix directly rather than approximating it.
        </p>

        <h4>What you're looking for</h4>
        <ul>
          <li>A card is hidden if its minimum spend is more than you said your household can realistically put on it.</li>
          <li>A card is hidden if every way of using its points is on your "don't want" list, or if none of its bonus types (cash back, hotel, airline) match what you said you want.</li>
          <li>A card whose points only become useful through a transfer (for example Chase Ultimate Rewards) is hidden unless you or your household hold a card that unlocks transfers for that currency, since otherwise its points can't reach anywhere useful.</li>
        </ul>
      </details>

      <h3>Known simplifications</h3>
      <ul>
        <li>Bonuses shown are typical public offers, not elevated or targeted ones you might see logged in or by invitation.</li>
        <li>Each points currency uses one cents-per-point value, regardless of how you'd actually redeem it.</li>
        <li>Ranking uses the first-year annual fee only; a card's fee in later years is shown but not ranked on.</li>
        <li>Authorized-user accounts aren't counted anywhere, including toward Chase's 5/24.</li>
      </ul>

      <h3>Data freshness</h3>
      <p className="note">
        {cardsFreshness ? <>Card offers and fees last reviewed on {formatDate(cardsFreshness)}. </> : null}
        {valuesFreshness ? <>Point values last reviewed on {formatDate(valuesFreshness)}, against Frequent Miler's RRVs.</> : null}
      </p>

      <h3>Credits</h3>
      <p>
        Built on the structure of the{" "}
        <a href={FLOWCHART} target="_blank" rel="noreferrer">r/churning credit card recommendation flowchart</a>, maintained
        by /u/m16p and originally by /u/kevlarlover. Point and mile values come from{" "}
        <a href={FM_RRV} target="_blank" rel="noreferrer">Frequent Miler's Reasonable Redemption Values</a>. See also{" "}
        <a href={FM_RULES} target="_blank" rel="noreferrer">Frequent Miler's application rules by bank</a>,{" "}
        <a href="https://www.doctorofcredit.com/" target="_blank" rel="noreferrer">Doctor of Credit</a>, and{" "}
        <a href="https://www.reddit.com/r/churning/" target="_blank" rel="noreferrer">r/churning</a> for more.
      </p>

      <p><a href="#">&larr; Back to the wizard</a></p>
    </section>
  );
}
