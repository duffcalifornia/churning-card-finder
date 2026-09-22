import { useMemo, useState } from "react";
import type { RankBy } from "../engine/recommend";
import { CHEAT_SHEET_PRESETS, rankForPreset } from "../state/cheatSheetPresets";
import { engineData } from "../data/engineData";
import { CardItem } from "./CardItem";
import { RankBySelector } from "./RankBySelector";

interface Props {
  rankBy: RankBy;
  onRankByChange: (r: RankBy) => void;
  onGoToFinder: () => void;
}

/**
 * A fast, no-questions reference: the same four boxes the r/churning flowchart used (5/24 status x reward type),
 * each showing every eligible card, not a top few — for someone who already knows their own real situation and
 * just wants the generic "best right now" answer to start from. See src/state/cheatSheetPresets.ts for what each
 * column assumes (never held any of these cards, unlimited spend) and why.
 */
export function CheatSheetPage({ rankBy, onRankByChange, onGoToFinder }: Props) {
  const [mobileSelected, setMobileSelected] = useState(CHEAT_SHEET_PRESETS[0]!.id);

  const columns = useMemo(
    () => CHEAT_SHEET_PRESETS.map((preset) => ({ preset, entries: rankForPreset(preset, engineData, rankBy) })),
    [rankBy],
  );

  return (
    <section>
      <h2>Signup Offer Cheat Sheet</h2>
      <p>
        A quick reference, not a personalized recommendation: each column assumes you have never had any of these
        cards and can meet any minimum spend, and only splits on 5/24 status and reward type. For a personalized
        list based on your actual card history,{" "}
        <button type="button" className="linklike" onClick={onGoToFinder}>use the Card Finder</button>.
      </p>

      <RankBySelector rankBy={rankBy} onChange={onRankByChange} />

      <label className="cheatsheet-mobile-select">
        View
        <select value={mobileSelected} onChange={(e) => setMobileSelected(e.target.value)}>
          {CHEAT_SHEET_PRESETS.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
      </label>

      <div className="cheatsheet-grid">
        {columns.map(({ preset, entries }) => (
          <div key={preset.id} className={preset.id === mobileSelected ? "cheatsheet-column" : "cheatsheet-column mobile-hidden"}>
            <h3>{preset.label}</h3>
            {entries.length === 0 ? (
              <p className="note">No eligible cards for this combination.</p>
            ) : (
              <ol className="results">
                {entries.map((entry, i) => <CardItem key={entry.cardId} entry={entry} single rankBy={rankBy} rank={i + 1} />)}
              </ol>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
