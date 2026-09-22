import type { RankBy } from "../engine/recommend";

/** The net-vs-raw value toggle, shared by the results step and the cheat sheet. */
export function RankBySelector({ rankBy, onChange }: { rankBy: RankBy; onChange: (r: RankBy) => void }) {
  return (
    <fieldset className="rankby">
      <legend>Rank by</legend>
      <label>
        <input type="radio" name="rankby" checked={rankBy === "net"} onChange={() => onChange("net")} /> Best net value
        <span className="hint">The welcome bonus's value minus the annual fee you would pay in the first year.</span>
      </label>
      <label>
        <input type="radio" name="rankby" checked={rankBy === "raw"} onChange={() => onChange("raw")} /> Best raw value
        <span className="hint">The welcome bonus's value alone, ignoring the annual fee.</span>
      </label>
    </fieldset>
  );
}
