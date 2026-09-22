import { useMemo } from "react";
import { recommend, type RankBy } from "../engine/recommend";
import type { Profile, ResultEntry, Results } from "../engine/types";
import { engineData } from "../data/engineData";
import { describeBonus } from "./bonusText";

interface Props {
  profile: Profile;
  rankBy: RankBy;
  onRankByChange: (r: RankBy) => void;
}

const FM_RULES = "https://frequentmiler.com/complete-guide-to-credit-card-application-rules-by-bank/";

const money = (n: number) => `${n < 0 ? "-" : ""}$${Math.abs(Math.round(n)).toLocaleString("en-US")}`;

function joinNames(names: string[]): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

function playerLabel(p: ResultEntry["players"][number]): string {
  return p.viaNllOnly ? `${p.name} (via NLL only)` : p.name;
}

function CardItem({ entry, single, rankBy }: { entry: ResultEntry; single: boolean; rankBy: RankBy }) {
  const card = engineData.catalog.find((c) => c.id === entry.cardId)!;
  const backups = entry.players.filter((p) => p.backup).map((p) => p.name);
  const main = entry.players.filter((p) => !p.backup);
  return (
    <li>
      <div className="cardname">{card.name}</div>
      {!single && main.length > 0 && <div className="who">{joinNames(main.map(playerLabel))}</div>}
      {backups.length > 0 && (
        <div className="backup">Backup for {joinNames(backups)}, in case the offer you get is lower than the maximum shown</div>
      )}
      <div className="bonus">{describeBonus(card, engineData.currencies, engineData.programs).join(" + ")}</div>
      <div className="values">
        <span className={rankBy === "raw" ? "value ranked" : "value"}>Bonus value {money(entry.bonusValue)}</span>
        <span className={rankBy === "net" ? "value ranked" : "value"}>
          Net value {money(entry.netValue)}
          {entry.annualFee > 0 && entry.firstYearFeeWaived ? " (first-year fee waived)" : entry.annualFee > 0 ? " after the annual fee" : ""}
        </span>
      </div>
      <div className="facts">
        <span>
          Annual fee {money(entry.annualFee)}
          {entry.firstYearFeeWaived ? ", waived the first year" : ""}
        </span>
        {entry.minSpend && (
          <span>
            Minimum spend {money(entry.minSpend.amount)} in {entry.minSpend.months} months
          </span>
        )}
      </div>
      {entry.ceiling && <div className="ceiling">The offer shown on the issuer's site is an "as high as" maximum. Yours may be lower.</div>}
    </li>
  );
}

export function ResultsStep({ profile, rankBy, onRankByChange }: Props) {
  const outcome = useMemo((): { results: Results } | { error: string } => {
    try {
      return { results: recommend(profile, engineData, { rankBy }) };
    } catch (e) {
      return { error: e instanceof Error ? e.message : String(e) };
    }
  }, [profile, rankBy]);

  if ("error" in outcome) {
    return (
      <section>
        <h2>Something went wrong</h2>
        <p>We could not work out your list: {outcome.error}</p>
      </section>
    );
  }
  const { results } = outcome;
  const single = profile.players.length === 1;

  return (
    <section>
      <h2>Your cards</h2>

      <div className="banner">
        Before you apply, confirm you will not be denied by a bank-specific rule that this list does not check, such as Chase 2/30, Amex 1/5
        and 2/90, Citi 8/65, and BoA 2/3/4. <a href={FM_RULES} target="_blank" rel="noreferrer">Frequent Miler's guide to application rules by bank</a> lists them.
      </div>

      <p className="note">
        This list assumes you have an established credit history and an above-average credit score. A thinner credit history or a lower score will
        limit which cards you can be approved for. If you are new to churning, read the notes on the r/churning flowchart and the r/churning wiki first.
      </p>

      <fieldset className="rankby">
        <legend>Rank the list by</legend>
        <label>
          <input type="radio" name="rankby" checked={rankBy === "net"} onChange={() => onRankByChange("net")} /> Best net value
          <span className="hint">The welcome bonus's value minus the annual fee you would pay in the first year.</span>
        </label>
        <label>
          <input type="radio" name="rankby" checked={rankBy === "raw"} onChange={() => onRankByChange("raw")} /> Best raw value
          <span className="hint">The welcome bonus's value alone, ignoring the annual fee.</span>
        </label>
      </fieldset>

      <div className="counters">
        {results.players.map((p) => (
          <span key={p.name} className={p.overFiveTwentyFour ? "counter warn" : "counter"}>
            {!single && <strong>{p.name}: </strong>}
            {p.x24}/24
          </span>
        ))}
      </div>

      {results.ranked.length === 0 ? (
        <p>No cards match your answers. Try raising the annual fee or spending amounts, or allowing more reward types.</p>
      ) : (
        <ol className="results">
          {results.ranked.map((entry) => <CardItem key={entry.cardId} entry={entry} single={single} rankBy={rankBy} />)}
        </ol>
      )}

      {results.bestPersonal.map((b) => (
        <div key={b.player} className="bestpersonal">
          <h3>Best Personal Cards{single ? "" : `: ${b.player}`}</h3>
          <p>
            We realize that you said you are trying to get/stay under 5/24, but here are the three highest ranked personal cards you're eligible for.
            Only you know how close you are to being under 5/24, or when you'd be back to 4/24 if this card would make you 5/24, so only you can say whether
            or not any of these offers are worth applying for a personal card for.
          </p>
          <ol className="results">
            {b.cards.map((entry) => <CardItem key={entry.cardId} entry={{ ...entry, players: entry.players.map((p) => ({ ...p, backup: false })) }} single rankBy={rankBy} />)}
          </ol>
        </div>
      ))}

      <p className="note">
        The complexities of the Bilt 2.0 program make it hard to determine whether this card makes sense for you. You will need to research this program and
        see if it makes sense for your spending habits and your redemption goals.
      </p>
    </section>
  );
}
