import { useEffect, useMemo, useState } from "react";
import { computeDerived } from "../engine/computeDerived";
import type { Card, Profile } from "../engine/types";
import { engineData } from "../data/engineData";
import {
  ISSUER_SECTIONS, clearHistory, historyCardsByIssuer, setCardCount, setMarriottFlag, setOtherCount,
  type CountField,
} from "../state/profile";
import { Count } from "./Count";

interface Props {
  profile: Profile;
  onChange: (p: Profile) => void;
}

const WINDOWS: { field: Exclude<CountField, "current">; label: string }[] = [
  { field: "lt12", label: "Approved under 12 months ago" },
  { field: "m12to24", label: "Approved 12 to 24 months ago" },
  { field: "m24to48", label: "Approved 24 to 48 months ago" },
  { field: "gt48", label: "Approved over 48 months ago" },
];

export function HistoryStep({ profile, onChange }: Props) {
  const [active, setActive] = useState(0);
  const index = Math.min(active, profile.players.length - 1);
  const player = profile.players[index]!;
  const derived = useMemo(() => computeDerived(player, engineData.catalog), [player]);
  const sections = useMemo(() => historyCardsByIssuer(engineData.catalog, engineData.marriottMatrix), []);
  const marriottIds = useMemo(() => new Set((engineData.marriottMatrix.cards ?? []).map((c) => c.id)), []);
  const cards = player.history.cards ?? {};

  // iOS Safari and Chrome (both WebKit) have a long-standing bug where a `position: sticky` element inside the
  // page that contains a focused input stops being sticky for the rest of the scroll session: focusing a Count
  // field below shrinks the browser's URL bar, and WebKit fails to recompute the sticky elements' stuck state
  // afterward, so they scroll away with the page instead of re-pinning - visually, they scroll up past where the
  // URL bar collapsed to, rather than staying pinned just below it. There is no CSS-only fix; the documented
  // workaround is to force a reflow of the sticky element by briefly clearing `position` and restoring it, right
  // when the viewport actually changes size (`visualViewport`'s resize event fires exactly then, covering both
  // the URL bar collapsing and a keyboard opening, regardless of which input triggered it).
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const resetStickiness = () => {
      document.querySelectorAll<HTMLElement>(".issuer[open] > summary, .issuer[open] thead th").forEach((el) => {
        el.style.position = "static";
        void el.offsetHeight; // force a reflow between the two assignments, or the browser coalesces them into a no-op
        el.style.position = "sticky";
      });
    };
    vv.addEventListener("resize", resetStickiness);
    return () => vv.removeEventListener("resize", resetStickiness);
  }, []);

  return (
    <section>
      <h2>Your card history</h2>
      <p>
        List every card you have had, from the issuers below. For each card, enter how many copies you hold now and how many you were
        approved for in each period. For Southwest and Marriott cards, use the date you received the bonus instead of the approval date.
        Leave cards you have never had blank.
      </p>

      {profile.players.length > 1 && (
        <div className="tabs" role="tablist" aria-label="Player">
          {profile.players.map((p, i) => (
            <button key={p.name} role="tab" aria-selected={i === index} className={i === index ? "tab active" : "tab"} onClick={() => setActive(i)}>
              {p.name}
            </button>
          ))}
        </div>
      )}

      <div className="counters" aria-live="polite">
        <span className={derived.overFiveTwentyFour ? "counter warn" : "counter"}>
          <strong>{derived.x24}/24</strong> cards on your credit report in 24 months
        </span>
        <span className="counter"><strong>{derived.amexCredit}</strong> of 5 Amex credit cards</span>
        <span className="counter"><strong>{derived.amexCharge}</strong> of 10 Amex charge cards</span>
        <span className="counter"><strong>{derived.chaseBusinessOpen}</strong> Chase business cards open</span>
      </div>

      <p>
        <button type="button" className="secondary" onClick={() => onChange(clearHistory(profile, index))}>
          {player.name} has never had any of these cards
        </button>
      </p>

      {ISSUER_SECTIONS.map((section) => {
        const list = sections.get(section.id) ?? [];
        const used = list.filter((c) => cards[c.id]).length + (player.history.otherPersonalByIssuer?.[section.id] ? 1 : 0);
        return (
          <details key={section.id} className="issuer">
            <summary>
              {section.name}
              {used > 0 && <span className="badge">{used} entered</span>}
            </summary>
            {list.length > 0 && (
              <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Card</th>
                      <th scope="col">Hold now</th>
                      {WINDOWS.map((w) => <th key={w.field} scope="col">{w.label}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((card) => (
                      <CardRows key={card.id} card={card} profile={profile} index={index} marriott={marriottIds.has(card.id)} onChange={onChange} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="other">
              <span>Other {section.name} personal cards, not listed above:</span>
              <label>Approved under 12 months ago
                <Count label={`Other ${section.name} cards approved under 12 months ago`} value={player.history.otherPersonalByIssuer?.[section.id]?.lt12 ?? 0}
                  onChange={(n) => onChange(setOtherCount(profile, index, section.id, "lt12", n))} />
              </label>
              <label>Approved 12 to 24 months ago
                <Count label={`Other ${section.name} cards approved 12 to 24 months ago`} value={player.history.otherPersonalByIssuer?.[section.id]?.m12to24 ?? 0}
                  onChange={(n) => onChange(setOtherCount(profile, index, section.id, "m12to24", n))} />
              </label>
            </div>
          </details>
        );
      })}

      <details className="issuer">
        <summary>Other issuers not listed</summary>
        <div className="other">
          <span>Personal cards from any other issuer:</span>
          <label>Approved under 12 months ago
            <Count label="Other issuers' cards approved under 12 months ago" value={player.history.otherIssuersPersonal?.lt12 ?? 0}
              onChange={(n) => onChange(setOtherCount(profile, index, "other", "lt12", n))} />
          </label>
          <label>Approved 12 to 24 months ago
            <Count label="Other issuers' cards approved 12 to 24 months ago" value={player.history.otherIssuersPersonal?.m12to24 ?? 0}
              onChange={(n) => onChange(setOtherCount(profile, index, "other", "m12to24", n))} />
          </label>
        </div>
      </details>
    </section>
  );
}

interface RowProps {
  card: Card;
  profile: Profile;
  index: number;
  marriott: boolean;
  onChange: (p: Profile) => void;
}

function CardRows({ card, profile, index, marriott, onChange }: RowProps) {
  const entry = profile.players[index]!.history.cards?.[card.id];
  const set = (field: CountField) => (n: number) => onChange(setCardCount(profile, index, card.id, field, n));
  return (
    <>
      <tr>
        <th scope="row">
          {card.name}
          {card.kind === "business" && <span className="tag">business</span>}
        </th>
        <td data-label="Hold now"><Count label={`${card.name}: hold now`} value={entry?.current ?? 0} onChange={set("current")} /></td>
        {WINDOWS.map((w) => (
          <td key={w.field} data-label={w.label}>
            <Count label={`${card.name}: ${w.label.toLowerCase()}`} value={entry?.approved?.[w.field] ?? 0} onChange={set(w.field)} />
          </td>
        ))}
      </tr>
      {marriott && (
        <tr className="extra">
          <td colSpan={6}>
            <label>
              <input type="checkbox" checked={entry?.marriott?.closedWithin30Days ?? false}
                onChange={(e) => onChange(setMarriottFlag(profile, index, card.id, "closedWithin30Days", e.target.checked))} />
              I held {card.name} in the last 30 days
            </label>
            <label>
              <input type="checkbox" checked={entry?.marriott?.approvedWithin90Days ?? false}
                onChange={(e) => onChange(setMarriottFlag(profile, index, card.id, "approvedWithin90Days", e.target.checked))} />
              I was approved for {card.name} in the last 90 days
            </label>
          </td>
        </tr>
      )}
    </>
  );
}
