import { useMemo } from "react";
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
  onChange: (n: number | null) => void;
}

function Money({ label, hint, value, allowBlank, onChange }: MoneyProps) {
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
          placeholder={allowBlank ? "No limit" : "0"}
          value={value ?? ""}
          onChange={(e) => {
            if (e.target.value === "") onChange(allowBlank ? null : 0);
            else onChange(Math.max(0, Number(e.target.value) || 0));
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
        value={h.spend3Months}
        onChange={(n) => set({ spend3Months: n ?? 0 })}
      />
      <Money label="The same, for the next 6 months" value={h.spend6Months} onChange={(n) => set({ spend6Months: n ?? 0 })} />
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
