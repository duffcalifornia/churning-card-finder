import { useMemo } from "react";
import { recommend, type RankBy } from "../engine/recommend";
import type { Profile, Results } from "../engine/types";
import { engineData } from "../data/engineData";
import { CardItem, money } from "./CardItem";
import { RankBySelector } from "./RankBySelector";

interface Props {
  profile: Profile;
  rankBy: RankBy;
  onRankByChange: (r: RankBy) => void;
}

const FM_RULES = "https://frequentmiler.com/complete-guide-to-credit-card-application-rules-by-bank/";

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

      <RankBySelector rankBy={rankBy} onChange={onRankByChange} />

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
          {results.ranked.map((entry, i) => <CardItem key={entry.cardId} entry={entry} single={single} rankBy={rankBy} rank={i + 1} />)}
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
            {b.cards.map((entry, i) => (
              <CardItem
                key={entry.cardId}
                entry={{ ...entry, players: entry.players.map((p) => ({ ...p, backup: false })) }}
                single
                rankBy={rankBy}
                rank={i + 1}
              />
            ))}
          </ol>
        </div>
      ))}
    </section>
  );
}
