import { useId } from "react";
import { computeDerived } from "../engine/computeDerived";
import type { Player, Profile } from "../engine/types";
import { engineData } from "../data/engineData";

interface Props {
  profile: Profile;
  onChange: (p: Profile) => void;
}

const SHUTDOWN_ISSUERS: { id: string; name: string }[] = [
  { id: "chase", name: "Chase" },
  { id: "amex", name: "American Express" },
  { id: "citi", name: "Citi" },
  { id: "wellsfargo", name: "Wells Fargo" },
  { id: "barclays", name: "Barclays" },
  { id: "capone", name: "Capital One" },
  { id: "discover", name: "Discover" },
  { id: "boa", name: "Bank of America" },
  { id: "usbank", name: "U.S. Bank" },
];

function YesNo({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  // A plain group (not <fieldset>/<legend>) because a native legend assumes a single short line: once the
  // question text wraps to several lines (the Ink LLC question below is four), browsers still only reserve
  // room for one line of it on the border, so the fieldset's top border renders straight through the wrapped
  // text instead of above it. A labelled group with a normal paragraph renders correctly at any label length.
  const id = useId();
  return (
    <div className="yesno" role="group" aria-labelledby={id}>
      <p id={id} className="yesno-label">{label}</p>
      <label><input type="radio" checked={value} onChange={() => onChange(true)} /> Yes</label>
      <label><input type="radio" checked={!value} onChange={() => onChange(false)} /> No</label>
    </div>
  );
}

export function QuestionsStep({ profile, onChange }: Props) {
  const update = (i: number, change: Partial<Player>) =>
    onChange({ ...profile, players: profile.players.map((p, j) => (j === i ? { ...p, ...change } : p)) });

  return (
    <section>
      <h2>About {profile.players.length > 1 ? "each person" : "you"}</h2>
      {profile.players.map((p, i) => {
        const holdsBusinessPlatinum = (p.history.cards?.["amex-business-platinum"]?.current ?? 0) > 0;
        // Ask about the LLC workaround only if it would matter: the player has an Ink card in their "ever had" set,
        // which is what triggers Chase's Ink lifetime block (K7).
        const everHadInk = [...computeDerived(p, engineData.catalog).everHad].some((id) => id.startsWith("chase-ink-"));
        return (
          <div key={p.name} className="playerblock">
            {profile.players.length > 1 && <h3>{p.name}</h3>}

            <fieldset>
              <legend>Has any of these issuers shut {profile.players.length > 1 ? "this person" : "you"} down (closed all accounts)?</legend>
              <div className="checks">
                {SHUTDOWN_ISSUERS.map((s) => (
                  <label key={s.id}>
                    <input
                      type="checkbox"
                      checked={p.shutdownIssuers.includes(s.id)}
                      onChange={(e) =>
                        update(i, { shutdownIssuers: e.target.checked ? [...p.shutdownIssuers, s.id] : p.shutdownIssuers.filter((x) => x !== s.id) })
                      }
                    />{" "}
                    {s.name}
                  </label>
                ))}
              </div>
              <p className="note">Leave all boxes empty if none.</p>
            </fieldset>

            <YesNo label="Are you banned from earning American Airlines AAdvantage miles?" value={p.bannedFromAA} onChange={(v) => update(i, { bannedFromAA: v })} />
            <YesNo label="Are you comfortable applying for business cards?" value={p.openToBusinessCards} onChange={(v) => update(i, { openToBusinessCards: v })} />
            <YesNo
              label="Are you interested in trying to get under 5/24 (if over) or stay under 5/24 (if under)?"
              value={p.wantsUnder524}
              onChange={(v) => update(i, { wantsUnder524: v })}
            />
            <YesNo label="Do you have an open Bank of America deposit account (checking or savings)?" value={p.hasBoaDepositAccount ?? false} onChange={(v) => update(i, { hasBoaDepositAccount: v })} />
            {holdsBusinessPlatinum && (
              <YesNo label="Do you have an Amex Business Checking account in your own name?" value={p.hasAmexBusinessChecking ?? false} onChange={(v) => update(i, { hasAmexBusinessChecking: v })} />
            )}
            {everHadInk && (
              <YesNo
                label={"You've had a Chase Ink business card before, which normally means you can't get that bonus again. You can get around this by applying through a newly formed LLC with its own EIN, but this only makes sense in a state where forming an LLC is free or cheap.\nDo you live in one of the states in the below list, and if so, would you be willing to form an LLC in order to allow you to apply for a new Ink card?\nAZ, CO, HI, IA, ID, MI, MN, MO, MS, MT, NM, OH, PA, WI, UT"}
                value={p.willingToFormLlcForInk ?? false}
                onChange={(v) => update(i, { willingToFormLlcForInk: v })}
              />
            )}
          </div>
        );
      })}
    </section>
  );
}
