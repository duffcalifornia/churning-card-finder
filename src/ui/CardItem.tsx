import type { RankBy } from "../engine/recommend";
import type { ResultEntry } from "../engine/types";
import { engineData } from "../data/engineData";
import { describeBonus } from "./bonusText";

export const money = (n: number) => `${n < 0 ? "-" : ""}$${Math.abs(Math.round(n)).toLocaleString("en-US")}`;

function joinNames(names: string[]): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

function playerLabel(p: ResultEntry["players"][number]): string {
  return p.viaNllOnly ? `${p.name} (via NLL only)` : p.name;
}

/** One card in a results or cheat-sheet list. `single` hides the player-name line (one player, or a hypothetical persona). */
export function CardItem({ entry, single, rankBy }: { entry: ResultEntry; single: boolean; rankBy: RankBy }) {
  const card = engineData.catalog.find((c) => c.id === entry.cardId)!;
  const backups = entry.players.filter((p) => p.backup).map((p) => p.name);
  const main = entry.players.filter((p) => !p.backup);
  return (
    <li>
      <div className="cardname">{card.name}</div>
      {!single && main.length > 0 && <div className="who">{joinNames(main.map(playerLabel))}</div>}
      {backups.length > 0 && (
        <div className="backup">Backup for {joinNames(backups)}, in case the offer you get is lower than the maximum shown</div>
      )}
      <div className="bonus">{describeBonus(card, engineData.currencies, engineData.programs).join(" + ")}</div>
      <div className="values">
        <span className={rankBy === "raw" ? "value ranked" : "value"}>Bonus value {money(entry.bonusValue)}</span>
        <span className={rankBy === "net" ? "value ranked" : "value"}>
          Net value {money(entry.netValue)}
          {entry.annualFee > 0 && entry.firstYearFeeWaived ? " (first-year fee waived)" : entry.annualFee > 0 ? " after the annual fee" : ""}
        </span>
      </div>
      <div className="facts">
        <span>
          Annual fee {money(entry.annualFee)}
          {entry.firstYearFeeWaived ? ", waived the first year" : ""}
        </span>
        {entry.minSpend && (
          <span>
            Minimum spend {money(entry.minSpend.amount)} in {entry.minSpend.months} months
          </span>
        )}
      </div>
      {entry.ceiling && <div className="ceiling">The offer shown on the issuer's site is an "as high as" maximum. Yours may be lower.</div>}
    </li>
  );
}
