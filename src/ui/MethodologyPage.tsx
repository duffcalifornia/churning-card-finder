import { engineData } from "../data/engineData";
import { formatDate, oldestVerifiedOn } from "./staleness";

const FM_RRV = "https://frequentmiler.com/reasonable-redemption-values-rrvs/";
const FM_RULES = "https://frequentmiler.com/complete-guide-to-credit-card-application-rules-by-bank/";
const FLOWCHART = "https://imgur.com/a/r-churning-cc-recommendation-flowchart-june-2025-LjDGPk2";
const USCCG = "https://www.uscreditcardguide.com";

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
        program, cards whose points end up in that program are moved to the top of the list, even if another card is objectively worth more. These rankings only consider the value of the welcome bonus. If you're looking for a credit card for some other reason, such as building credit or having a low interest rate, this site won't help you. Please use credit cards responsibly.
      </p>

      <h3>How a bonus is valued</h3>
      <p>
        A card's bonus value is its points times a cents-per-point value, plus any cash back or statement credit, plus any
        free night certificates, added together. Points are valued using{" "}
        <a href={FM_RRV} target="_blank" rel="noreferrer">Frequent Miler's Reasonable Redemption Values</a>, which the site
        treats as the definitive source; free night certificates use Frequent Miler's own discounted values for them too.
      </p>
      <p>
        The <strong>net value</strong> shown for each card is the value of the bonus minus the first year annual fee. It does
        not consider whether or not the annual fee changes if you keep the card longer than one year. All rankings are
        determined using a card's net value, though you can view them using only the value of the bonus if you want.
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
        There are some rules that banks apply that the card finder tool does not ask about in order to simplify the history
        entry process. Examples include the American Express rule where you can only get 2 credit cards in 90 days, or
        Citi's rule where you can only get 1 card in 8 days. Before you apply, check your own history against{" "}
        <a href={FM_RULES} target="_blank" rel="noreferrer">Frequent Miler's guide to application rules by bank</a>, which
        covers these and more.
      </p>

      <details className="issuer">
        <summary>The eligibility rules this site does check</summary>

        <h4>How many cards you can hold or have recently opened</h4>
        <ul>
          <li>Chase: 5 or more cards from any issuer reported to your personal credit report in the last 24 months hides every Chase card. Ink cards use a stricter threshold of 3 cards reporting to your personal credit report; this threshold is applied before the five card rule.</li>
          <li>Barclays: 6 or more cards (any issuer) in 24 months.</li>
          <li>US Bank: 5 or more cards (any issuer) in 12 months.</li>
          <li>Bank of America: more than 6 cards in 12 months with a BoA deposit account, more than 2 without one.</li>
          <li>Amex: 5 open credit cards and 10 open charge cards, counted separately (Schwab and Morgan Stanley Amex-branded cards count too).</li>
          <li>Discover: a wait of 12 months after a first Discover card, and at most 2 held.</li>
          <li>Only Discover and certain Capital One business cards show up on your personal credit report and count toward the personal-card rules above; every other issuer's business cards don't.</li>
        </ul>

        <h4>Whether you can earn a card's bonus again</h4>
        <ul>
          <li>Chase Sapphire cards, Chase Ink cards, Citi Strata cards, and every Amex card: once you've been approved for one, you can't earn its bonus again (personal and business Sapphire cards are independent of each other).</li>
          <li>Amex family rules: having had a higher card in a family (for example Platinum over Gold, or a higher Delta or Hilton tier) blocks a bonus on a lower one. Amex cards blocked this way, or by the once-ever rule above, still appear on the list marked "via NLL only" because these offers also omit the family restrictions: they're worth applying for if you find an NLL offer.</li>
          <li>Amex lifetime language: normal Amex applications state that you're only eligible for a welcome bonus if you've never had the card before (earning the bonus or not does not change this limitation). It is superseded by the Amex family rule if it could apply to the card. Amex cards you've had before can still show in the list with a note that the bonus can only be obtained by applying using an NLL offer.</li>
          <li>Capital One's Venture family rule (VentureOne, Venture, Venture X) works the same way as Amex's, ordered by annual fee, and Citi and Capital One personal cards separately can't earn a bonus on the exact same card again within 48 months.</li>
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
          <li>A card whose points only become useful through a transfer (for example, transferring Chase Ultimate Rewards points to travel partners like United or Hyatt) is hidden unless you or your household hold a card that unlocks transfers for that currency, since otherwise its points can't reach anywhere useful.</li>
        </ul>
      </details>

      <h3>Known simplifications</h3>
      <ul>
        <li>
          Bonuses shown are what is publicly available through each issuer's homepage. You might be able to find better offers
          (higher bonuses, different spending requirements) through invitation offers, offers you only see after logging into
          a site, referral offers, or through affiliate links (found on major credit card sites like The Points Guy). Please
          research these offers yourself to make sure you're applying for the best offer possible.
        </li>
        <li>
          Transferable points such as Ultimate Rewards and Membership Rewards can have different valuations depending on how
          the points are redeemed. Since there are too many variables for this tool to accurately determine the value based on
          how each individual person might use the points, they are instead given the flat valuation Frequent Miler provides.
          The value you get from those points could be higher or lower than their assigned value.
        </li>
        <li>Cards that award transferrable points are only shown in cash only lists if you can cash your points out for at least one cent per point. They're too flexible and too valuable to treat them as cash back cards otherwise.</li>
        <li>Ranking uses the first-year annual fee only; a card's fee in later years is shown but not ranked on.</li>
        <li>Authorized-user accounts aren't counted anywhere, including toward Chase's 5/24.</li>
      </ul>

      <h3>Data freshness</h3>
      <p className="note">
        {cardsFreshness ? <>Card offers and fees last reviewed on {formatDate(cardsFreshness)}. </> : null}
        {valuesFreshness ? <>Point values last reviewed on {formatDate(valuesFreshness)}, against Frequent Miler's RRVs.</> : null}
      </p>

      <h3>Credits</h3>
      <ul>
        <li>
          This site is inspired by the{" "}
          <a href={FLOWCHART} target="_blank" rel="noreferrer">r/churning credit card recommendation flowchart</a>, originally
          conceived by /u/kevlarlover and most recently maintained by /u/m16p.
        </li>
        <li>
          For information on the bonus offer history for all credit cards, visit the{" "}
          <a href={USCCG} target="_blank" rel="noreferrer">US Credit Card Guide</a>.
        </li>
        <li>
          Point and mile values come from{" "}
          <a href={FM_RRV} target="_blank" rel="noreferrer">Frequent Miler's Reasonable Redemption Values</a>.
        </li>
        <li>
          See also{" "}
          <a href={FM_RULES} target="_blank" rel="noreferrer">Frequent Miler's application rules by bank</a>,{" "}
          <a href="https://www.doctorofcredit.com/" target="_blank" rel="noreferrer">Doctor of Credit</a>, and{" "}
          <a href="https://www.reddit.com/r/churning/" target="_blank" rel="noreferrer">r/churning</a> for more.
        </li>
      </ul>

      <p><a href="#">&larr; Back to the wizard</a></p>
    </section>
  );
}
