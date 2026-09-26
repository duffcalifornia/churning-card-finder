import { useMemo, useState } from "react";
import type { RankBy } from "../engine/recommend";
import { CHEAT_SHEET_PRESETS, rankForPreset } from "../state/cheatSheetPresets";
import { engineData } from "../data/engineData";
import { CardItem } from "./CardItem";
import { RankBySelector } from "./RankBySelector";
import { cheatSheetPresetPath, seoForPreset } from "./cheatSheetSeo";
import { useSeo } from "./useSeo";

interface Props {
  rankBy: RankBy;
  onRankByChange: (r: RankBy) => void;
  onGoToFinder: () => void;
  selectedPreset: string;
  onPresetChange: (id: string) => void;
}

/**
 * A fast, no-questions reference: the same four lists the r/churning flowchart used (5/24 status x reward type),
 * each showing every eligible card, not a top few — for someone who already knows their own real situation and
 * just wants the generic "best right now" answer to start from. See src/state/cheatSheetPresets.ts for what each
 * list assumes (never held any of these cards, unlimited spend) and why. Only one list is shown at a time, picked
 * from a dropdown, at every screen width: fitting all four side by side would squeeze each one too narrow to read.
 */
const KIND_FILTERS = [
  { id: "all", label: "All cards" },
  { id: "personal", label: "Personal only" },
  { id: "business", label: "Business only" },
] as const;
type KindFilter = (typeof KIND_FILTERS)[number]["id"];

export function CheatSheetPage({ rankBy, onRankByChange, onGoToFinder, selectedPreset, onPresetChange }: Props) {
  const [kindFilter, setKindFilter] = useState<KindFilter>("all");
  const preset = CHEAT_SHEET_PRESETS.find((p) => p.id === selectedPreset) ?? CHEAT_SHEET_PRESETS[0]!;

  const seo = seoForPreset(preset.id);
  useSeo(seo.title, seo.description, `https://www.whichcreditcardshouldiget.com${cheatSheetPresetPath(preset.id)}`);

  const allEntries = useMemo(() => rankForPreset(preset, engineData, rankBy), [preset, rankBy]);
  const entries = useMemo(
    () =>
      kindFilter === "all"
        ? allEntries
        : allEntries.filter((entry) => engineData.catalog.find((c) => c.id === entry.cardId)?.kind === kindFilter),
    [allEntries, kindFilter],
  );

  return (
    <section>
      <h2>Signup Offer Cheat Sheet</h2>
      <p>
        This is only a quick reference guide. The lists are separated by 5/24 status and redemption goals only -
        they assume you're eligible for every card on them and that you can meet any spending requirements. For a
        personalized list based on your actual card history,{" "}
        <button type="button" className="linklike" onClick={onGoToFinder}>use the Card Finder</button>.
      </p>

      <RankBySelector rankBy={rankBy} onChange={onRankByChange} />

      <label className="cheatsheet-select">
        View
        <select value={preset.id} onChange={(e) => onPresetChange(e.target.value)}>
          {CHEAT_SHEET_PRESETS.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
      </label>

      <label className="cheatsheet-select">
        Cards to show
        <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value as KindFilter)}>
          {KIND_FILTERS.map((f) => (
            <option key={f.id} value={f.id}>{f.label}</option>
          ))}
        </select>
      </label>

      <div className="cheatsheet-column">
        <h3>{preset.label}</h3>
        {entries.length === 0 ? (
          <p className="note">No eligible cards for this combination.</p>
        ) : (
          <ol className="results">
            {entries.map((entry, i) => <CardItem key={entry.cardId} entry={entry} single rankBy={rankBy} rank={i + 1} />)}
          </ol>
        )}
      </div>
    </section>
  );
}
