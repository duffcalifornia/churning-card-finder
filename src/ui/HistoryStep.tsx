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

  // iOS Safari and Chrome (both WebKit) break header pinning on this page once a Count field below is focused:
  // the issuer name bar (e.g. "Chase") ends up above the visible screen instead of pinned below the URL bar. Two
  // earlier attempts (a compositing-layer hint, then forcing a sticky reflow) didn't fix it: neither did a first
  // cut at this same JS-driven `position: fixed` approach, which is the key clue - a *manually computed* fixed
  // position failing the same way means the bug isn't in how the header is positioned, it's in what "top: 0"
  // even means right then. iOS does not resize the layout viewport when the keyboard opens or the URL bar
  // collapses - only the *visual* viewport shifts - but `getBoundingClientRect()` and `position: fixed` are both
  // anchored to the layout viewport. So "top: 0" pins to the top of a viewport that may no longer be the part of
  // the page actually on screen. `window.visualViewport.offsetTop` is the documented way to read that gap, so
  // pinning has to track it instead of a hardcoded 0 - and every rect this code reads has to be adjusted by the
  // same amount, or "is this issuer's top above the visible area" would still be judged against the wrong frame.
  useEffect(() => {
    const BORDER_WIDTH = 1; // .issuer's own border-width (border: 1px solid var(--line))
    let raf = 0;

    // Column widths have to be frozen before any header cell is ever pinned, or the table's own layout drifts out
    // from under the pinned copy in two ways: (1) `getBoundingClientRect()` forces a synchronous layout pass, so
    // measuring cell N's width *after* cell N-1 has already gone `position: fixed` reads an already-shifted table;
    // (2) with the default `table-layout: auto`, column widths are computed from every row together, header
    // included - once every header cell has left the flow, the tbody's own narrower content (a small number input
    // vs. a long column label) is free to win, so the body's columns end up narrower than the frozen header still
    // shown above them. `table-layout: fixed` plus an explicit <colgroup> makes column widths independent of
    // which cells are actually present in a given row, so removing the header from flow can't affect the body.
    const freezeColumns = () => {
      document.querySelectorAll<HTMLTableElement>(".issuer table").forEach((table) => {
        const row = table.querySelector<HTMLTableRowElement>("thead tr");
        if (!row) return;
        const cells = Array.from(row.querySelectorAll<HTMLElement>("th"));
        // Release any previous freeze/pin first, so this always measures the table's true natural (auto-layout)
        // widths rather than compounding an earlier, possibly-stale freeze.
        table.style.tableLayout = "";
        cells.forEach((c) => {
          c.style.position = "";
          c.style.width = "";
        });
        const widths = cells.map((c) => c.getBoundingClientRect().width);
        table.style.tableLayout = "fixed";
        let colgroup = table.querySelector("colgroup");
        if (!colgroup) {
          colgroup = document.createElement("colgroup");
          table.prepend(colgroup);
        }
        colgroup.replaceChildren(
          ...widths.map((w) => {
            const col = document.createElement("col");
            col.style.width = `${w}px`;
            return col;
          }),
        );
      });
    };

    const update = () => {
      raf = 0;
      const vv = window.visualViewport;
      const offsetTop = vv?.offsetTop ?? 0;
      const offsetLeft = vv?.offsetLeft ?? 0;
      document.querySelectorAll<HTMLDetailsElement>(".issuer").forEach((issuer) => {
        const summary = issuer.querySelector<HTMLElement>(":scope > summary");
        if (!summary) return;
        // A closed issuer's <summary> stays visible (it's the toggle control), so it must be explicitly excluded
        // here rather than relying on a `.issuer[open]` selector - otherwise closing an issuer while its header
        // is pinned would leave that header stuck in fixed position, floating over the page forever.
        const rect = issuer.getBoundingClientRect();
        const summaryHeight = summary.offsetHeight || 44;
        const shouldPin = issuer.open && rect.top < offsetTop && rect.bottom > offsetTop + summaryHeight;
        if (shouldPin) {
          summary.style.position = "fixed";
          summary.style.top = `${offsetTop}px`;
          summary.style.left = `${rect.left + BORDER_WIDTH - offsetLeft}px`;
          summary.style.width = `${issuer.clientWidth}px`;
          issuer.classList.add("js-pinned");
        } else {
          summary.style.position = "";
          summary.style.top = "";
          summary.style.left = "";
          summary.style.width = "";
          issuer.classList.remove("js-pinned");
        }

        // The column headers pin the same way, right below the issuer bar, and for the same reason: native
        // `position: sticky` on <thead> cells was confirmed broken on real hardware too. Individual <th> cells
        // (not the whole <thead>) are pinned because `position: fixed` on the whole row would drop it out of the
        // table layout algorithm entirely, misaligning it with the tbody's own column widths.
        //
        // Below 600px (the same breakpoint the mobile @media block below uses), <thead> is deliberately hidden
        // from sighted users - clipped to 1px via overflow: hidden, screen-reader only - because each row becomes
        // a labelled card instead of a table row. `position: fixed` on a th would escape that overflow clipping
        // (fixed elements aren't clipped by an ancestor's overflow unless that ancestor is itself a fixed-position
        // containing block, which .issuer thead isn't), popping the "hidden" headers back into view, so this has
        // to be skipped there entirely rather than relying on the clip to still hide a fixed-positioned child.
        const isNarrowLayout = window.innerWidth <= 600;
        const table = issuer.querySelector<HTMLTableElement>("table");
        const row = table?.querySelector<HTMLTableRowElement>("thead tr");
        const cells = row ? Array.from(row.querySelectorAll<HTMLElement>("th")) : [];
        const colWidths = table
          ? Array.from(table.querySelectorAll<HTMLElement>("colgroup col")).map((c) => parseFloat(c.style.width) || 0)
          : [];
        if (shouldPin && !isNarrowLayout && table && row && cells.length && colWidths.length === cells.length) {
          // Reserve the row's own space now that its cells leave table flow. Read from the frozen column widths,
          // never from the cells themselves mid-loop below - see the comment on freezeColumns for why.
          row.style.height = row.style.height || `${row.getBoundingClientRect().height}px`;
          const tableLeft = table.getBoundingClientRect().left;
          let x = tableLeft;
          cells.forEach((cell, i) => {
            const width = colWidths[i]!;
            cell.style.position = "fixed";
            cell.style.top = `${offsetTop + summaryHeight}px`;
            cell.style.left = `${x - offsetLeft}px`;
            cell.style.width = `${width}px`;
            x += width;
          });
        } else {
          row?.style.removeProperty("height");
          cells.forEach((cell) => {
            cell.style.position = "";
            cell.style.top = "";
            cell.style.left = "";
            cell.style.width = "";
          });
        }
      });
    };
    const schedule = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    // Re-freeze only on the layout viewport actually changing width (orientation change, split view, etc.), not
    // on a plain scroll or on visualViewport's resize event, which also fires for the keyboard opening/closing -
    // that changes height and the visible offset, never the columns' natural widths, so re-measuring there would
    // just be a wasted flash of unpinned layout on every keystroke's focus change.
    const onResize = () => {
      freezeColumns();
      schedule();
    };

    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", onResize);
    window.visualViewport?.addEventListener("resize", schedule);
    window.visualViewport?.addEventListener("scroll", schedule);
    // Opening or closing an issuer moves every rect below it, so re-measure right away rather than waiting for
    // the next scroll (a click doesn't scroll the page on its own).
    const detailsEls = Array.from(document.querySelectorAll<HTMLDetailsElement>(".issuer"));
    detailsEls.forEach((d) => d.addEventListener("toggle", schedule));
    freezeColumns();
    schedule();

    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", onResize);
      window.visualViewport?.removeEventListener("resize", schedule);
      window.visualViewport?.removeEventListener("scroll", schedule);
      detailsEls.forEach((d) => d.removeEventListener("toggle", schedule));
      document.querySelectorAll<HTMLElement>(".issuer > summary").forEach((s) => {
        s.style.position = "";
        s.style.top = "";
        s.style.left = "";
        s.style.width = "";
      });
      document.querySelectorAll(".issuer").forEach((d) => d.classList.remove("js-pinned"));
      document.querySelectorAll<HTMLTableElement>(".issuer table").forEach((table) => {
        table.style.tableLayout = "";
        table.querySelector("colgroup")?.remove();
      });
      document.querySelectorAll<HTMLElement>(".issuer thead tr").forEach((row) => row.style.removeProperty("height"));
      document.querySelectorAll<HTMLElement>(".issuer thead th").forEach((cell) => {
        cell.style.position = "";
        cell.style.top = "";
        cell.style.left = "";
        cell.style.width = "";
      });
    };
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
