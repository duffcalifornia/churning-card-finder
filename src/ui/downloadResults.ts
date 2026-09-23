import type { ResultEntry } from "../engine/types";
import { engineData } from "../data/engineData";
import { describeBonus } from "./bonusText";
import { issuerLabel } from "../state/profile";
import { money } from "./CardItem";

function csvField(value: string | number): string {
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** A CSV of the recommended cards, one row per entry, in the order they're ranked on screen. */
export function resultsToCsv(entries: ResultEntry[]): string {
  const header = ["Rank", "Card", "Issuer", "Bonus", "Annual fee", "Minimum spend", "Bonus value", "Net value"];
  const rows = entries.map((entry, i) => {
    const card = engineData.catalog.find((c) => c.id === entry.cardId)!;
    const minSpend = entry.minSpend ? `${money(entry.minSpend.amount)} in ${entry.minSpend.months} months` : "";
    return [
      i + 1,
      card.name,
      issuerLabel(card.issuer),
      describeBonus(card, engineData.currencies, engineData.programs).join(" + "),
      money(entry.annualFee) + (entry.firstYearFeeWaived ? " (first-year fee waived)" : ""),
      minSpend,
      money(entry.bonusValue),
      money(entry.netValue),
    ].map(csvField).join(",");
  });
  return [header.join(","), ...rows].join("\n");
}

export function downloadResultsCsv(entries: ResultEntry[], filename: string): void {
  const blob = new Blob([resultsToCsv(entries)], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
