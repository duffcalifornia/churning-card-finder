import { useEffect, useMemo, useRef, useState } from "react";
import type { Household, Profile } from "../engine/types";
import { engineData } from "../data/engineData";
import { programOptions } from "../state/programOptions";
import { setProgramChoice } from "../state/profile";

interface Props {
  profile: Profile;
  onChange: (p: Profile) => void;
}

const BONUS_TYPES = [
  { id: "cashback", label: "Cash back" },
  { id: "hotel", label: "Hotel points" },
  { id: "airline", label: "Airline miles" },
];

interface MoneyProps {
  label: string;
  hint?: string;
  value: number | null;
  /** Blank means "no value" (null) instead of zero. */
  allowBlank?: boolean;
  /** Shows a stored 0 as an empty box (with `placeholder` in its place) instead of a literal "0" — for a field
   * whose real answer is never usefully $0, so 0 just means "not answered yet" rather than a meaningful value. */
  hideZero?: boolean;
  placeholder?: string;
  onChange: (n: number | null) => void;
}

function Money({ label, hint, value, allowBlank, hideZero, placeholder, onChange }: MoneyProps) {
  const fmt = (v: number | null) => (v === null || (hideZero && v === 0) ? "" : String(v));
  // Local text, not derived straight from `value` on every render: otherwise clearing the box to type a new
  // number calls onChange(0), the parent stores 0, and the next render snaps a literal "0" back into the box
  // before the next keystroke lands, so it can never actually be cleared (the bug this fixes). Text is only
  // resynced from `value` when it changed for a reason other than this input's own last edit (e.g. Start Over).
  const [text, setText] = useState(() => fmt(value));
  const lastEmitted = useRef(value);
  useEffect(() => {
    if (value !== lastEmitted.current) {
      setText(fmt(value));
      lastEmitted.current = value;
    }
    // fmt/hideZero are effectively constant per field; only `value` (an external change) should resync text.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <label className="field">
      {label}
      {hint && <span className="hint">{hint}</span>}
      <span className="money">
        $
        <input
          type="number"
          min={0}
          step={100}
          inputMode="numeric"
          placeholder={placeholder ?? (allowBlank ? "No limit" : "0")}
          value={text}
          onChange={(e) => {
            const raw = e.target.value;
            setText(raw);
            const n = raw === "" ? (allowBlank ? null : 0) : Math.max(0, Number(raw) || 0);
            lastEmitted.current = n;
            onChange(n);
          }}
        />
      </span>
    </label>
  );
}

interface ProgramListProps {
  title: string;
  subtitle?: string;
  list: "excluded" | "targeted";
  profile: Profile;
  onChange: (p: Profile) => void;
  /** Whether "Cash back" is offered as a choice (it can be excluded, but is not a program to target). */
  cashBack: boolean;
}

function ProgramList({ title, subtitle, list, profile, onChange, cashBack }: ProgramListProps) {
  const options = useMemo(() => programOptions(engineData.programs), []);
  const chosen = list === "excluded" ? profile.household.excludedPrograms : profile.household.targetPrograms ?? [];
  const box = (value: string, label: string) => (
    <label key={value}>
      <input type="checkbox" checked={chosen.includes(value)} onChange={(e) => onChange(setProgramChoice(profile, list, value, e.target.checked))} /> {label}
    </label>
  );
  return (
    <details className="issuer" open={chosen.length > 0}>
      <summary>
        {title}
        {chosen.length > 0 && <span className="badge">{chosen.length} selected</span>}
      </summary>
      {subtitle && <p className="note">{subtitle}</p>}
      <div className="checks columns">
        {cashBack && box("cashback", "Cash back")}
        {options.map((o) => box(o.value, o.label))}
      </div>
    </details>
  );
}

export function HouseholdStep({ profile, onChange }: Props) {
  const h = profile.household;
  const set = (change: Partial<Household>) => onChange({ ...profile, household: { ...h, ...change } });
  const toggle = (list: string[], id: string, on: boolean) => (on ? [...list, id] : list.filter((x) => x !== id));

  return (
    <section>
      <h2>Your spending and preferences</h2>
      <p>These apply to everyone in the household.</p>

      <Money
        label="The highest annual fee you would pay on a single card"
        hint="This is what you would pay in a card's first year, so a card whose annual fee is waived that year counts as $0. Leave this blank if there is no limit on the annual fee you would pay."
        allowBlank
        value={h.maxAnnualFee}
        onChange={(n) => set({ maxAnnualFee: n })}
      />
      <Money
        label="If you were to put all of your day-to-day, non-housing spending on one card for the next three months, how much would that be?"
        hint="Required — the tool can't tell which minimum spends you could reach without this."
        hideZero
        placeholder="3000"
        value={h.spend3Months}
        onChange={(n) => set({ spend3Months: n ?? 0 })}
      />
      <Money
        label="The same, for the next 6 months"
        hint="Leave this blank to assume double your three-month answer."
        hideZero
        placeholder={h.spend3Months > 0 ? String(h.spend3Months * 2) : "6000"}
        value={h.spend6Months}
        onChange={(n) => set({ spend6Months: n ?? 0 })}
      />
      <Money
        label="How much extra could you realistically spend over the next three months via supplemental spending?"
        value={h.supplementalSpend3Months}
        onChange={(n) => set({ supplementalSpend3Months: n ?? 0 })}
      />

      <fieldset>
        <legend>What kind of rewards do you want?</legend>
        <div className="checks">
          {BONUS_TYPES.map((t) => (
            <label key={t.id}>
              <input type="checkbox" checked={h.bonusTypes.includes(t.id)} onChange={(e) => set({ bonusTypes: toggle(h.bonusTypes, t.id, e.target.checked) })} /> {t.label}
            </label>
          ))}
        </div>
        <p className="note">Leave all boxes empty to see every type.</p>
      </fieldset>

      <ProgramList title="(Optional) Points or miles programs you do NOT want to consider" list="excluded" cashBack profile={profile} onChange={onChange} />
      <ProgramList
        title="(Optional) Points or Miles programs to target"
        subtitle="If you are planning for a very specific redemption, select all points programs you'd like to target if possible"
        list="targeted"
        cashBack={false}
        profile={profile}
        onChange={onChange}
      />
    </section>
  );
}
