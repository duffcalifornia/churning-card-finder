import type { RankBy } from "../engine/recommend";
import type { ResultEntry } from "../engine/types";
import { engineData } from "../data/engineData";
import { describeBonus } from "./bonusText";
import { issuerLabel } from "../state/profile";
import { AlertIcon, ClockIcon, FeeIcon, WarningIcon } from "./icons";

export const money = (n: number) => `${n < 0 ? "-" : ""}$${Math.abs(Math.round(n)).toLocaleString("en-US")}`;

function joinNames(names: string[]): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

function playerLabel(p: ResultEntry["players"][number]): string {
  return p.viaNllOnly ? `${p.name} (via NLL only)` : p.name;
}

/** One card in a results or cheat-sheet list. `single` hides the player-name line (one player, or a hypothetical
 * persona). `rank` (1-based) draws the numbered badge; omit it to leave the badge off (e.g. an unordered list). */
export function CardItem({ entry, single, rankBy, rank }: { entry: ResultEntry; single: boolean; rankBy: RankBy; rank?: number }) {
  const card = engineData.catalog.find((c) => c.id === entry.cardId)!;
  const backups = entry.players.filter((p) => p.backup).map((p) => p.name);
  const main = entry.players.filter((p) => !p.backup);
  const isBackup = backups.length > 0;
  const nllPlayers = main.filter((p) => p.viaNllOnly).map((p) => p.name);
  return (
    <li className={isBackup ? "resultcard backup" : "resultcard"}>
      {rank !== undefined && <div className="rankbadge" aria-hidden="true">{rank}</div>}
      <div className="resultcard-body">
        <div className="cardhead">
          <span className="cardname">{card.name}</span>
          <span className="badge issuer">{issuerLabel(card.issuer)}</span>
          {isBackup && (
            <span className="badge backuptag">
              Backup for {joinNames(backups)}
            </span>
          )}
        </div>
        {isBackup && <div className="backupnote">In case an offer you get is lower than the maximum shown.</div>}
        {!single && main.length > 0 && <div className="who">{joinNames(main.map(playerLabel))}</div>}
        {nllPlayers.length > 0 && (
          <div className="nllnote">
            <AlertIcon />
            {single
              ? 'This is normally a once-per-lifetime bonus, and the player already has or has had this card (or a higher card in its family). It would take a targeted "no lifetime language" (NLL) offer to earn this bonus.'
              : nllPlayers.length === main.length
                ? 'This is normally a once-per-lifetime bonus, and everyone listed already has or has had this card (or a higher card in its family). It would take a targeted "no lifetime language" (NLL) offer to earn this bonus.'
                : `This is normally a once-per-lifetime bonus, and ${joinNames(nllPlayers)} already ${nllPlayers.length === 1 ? "has" : "have"} or had this card (or a higher card in its family). It would take a targeted "no lifetime language" (NLL) offer to earn this bonus.`}
          </div>
        )}
        <div className="bonus">{describeBonus(card, engineData.currencies, engineData.programs).join(" + ")}</div>
        <div className="values">
          <span className={rankBy === "raw" ? "value ranked" : "value"}>Bonus value {money(entry.bonusValue)}</span>
          <span className={rankBy === "net" ? "value ranked" : "value"}>
            Net value {money(entry.netValue)}
            {entry.annualFee > 0 && (
              <span className="value-suffix">{entry.firstYearFeeWaived ? " (first-year fee waived)" : " after the annual fee"}</span>
            )}
          </span>
        </div>
        <div className="facts">
          <span>
            <FeeIcon />
            Annual fee {money(entry.annualFee)}
            {entry.firstYearFeeWaived ? ", waived the first year" : ""}
          </span>
          {entry.minSpend && (
            <span>
              <ClockIcon />
              Minimum spend {money(entry.minSpend.amount)} in {entry.minSpend.months} months
            </span>
          )}
        </div>
        {entry.ceiling && (
          <div className="ceiling">
            <WarningIcon />
            The offer shown on the issuer's site is an "as high as" maximum. Yours may be lower.
          </div>
        )}
      </div>
    </li>
  );
}
