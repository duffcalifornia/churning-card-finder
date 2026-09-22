import { computeDerived } from "./computeDerived";
import { hardExclusion, type ExclusionContext } from "./hardExclusion";
import { bonusValue, firstYearFee } from "./netValue";
import { nllBlock } from "./nllBlock";
import { targetsProgram } from "./targets";
import { unlockStatus } from "./unlockStatus";
import type { Card, EngineData, Player, Profile, ResultEntry, Results } from "./types";

export type RankBy = "net" | "raw";

interface Candidate {
  card: Card;
  /** Bonus value, and bonus value minus the first-year fee. `value` is whichever the list is ranked by. */
  bonus: number;
  net: number;
  value: number;
  viaNllOnly: boolean;
  /** The card leads to a program the household is targeting. */
  targeted: boolean;
}

interface Listing {
  cardId: string;
  bonus: number;
  net: number;
  value: number;
  viaNllOnly: boolean;
  backup: boolean;
  targeted: boolean;
}

const BEST_PERSONAL_COUNT = 3;

/**
 * Every card the player could apply for, best first: cards nothing hides, valued net of the first-year annual fee, with cards
 * that only an NLL offer would allow kept in place and marked. Cards that lead to a targeted program come first, then by
 * value. Ties break on the card id so the order is stable.
 */
function candidatesFor(player: Player, data: EngineData, ctx: ExclusionContext, rankBy: RankBy): Candidate[] {
  const currencyOf = (card: Card) => data.currencies.find((c) => c.id === card.currency);
  const out: Candidate[] = [];
  for (const card of data.catalog) {
    if (hardExclusion(player, card, ctx) !== null) continue;
    // The unlocker cards themselves are valued at the with-unlocker rate: getting one unlocks the currency.
    const currency = currencyOf(card);
    const unlocked = currency !== undefined && (ctx.unlock.get(currency.id) === true || currency.unlockerCards.includes(card.id));
    const bonus = bonusValue(card, data.valuations, unlocked);
    const net = bonus - firstYearFee(card);
    out.push({
      card,
      bonus,
      net,
      value: rankBy === "raw" ? bonus : net,
      viaNllOnly: nllBlock(player, ctx.derived, card, data.catalog, data.marriottMatrix) !== null,
      targeted: targetsProgram(player, card, ctx),
    });
  }
  return out.sort((a, b) => Number(b.targeted) - Number(a.targeted) || b.value - a.value || (a.card.id < b.card.id ? -1 : 1));
}

function entryFor(card: Card, players: ResultEntry["players"], bonus: number, net: number): ResultEntry {
  const entry: ResultEntry = { cardId: card.id, players, annualFee: card.annualFee ?? 0, bonusValue: bonus, netValue: net };
  if (card.firstYearFeeWaived) entry.firstYearFeeWaived = true;
  if (card.typicalMinSpend) entry.minSpend = { amount: card.typicalMinSpend.amount, months: card.typicalMinSpend.months };
  if (card.welcomeBonus?.ceiling) entry.ceiling = true;
  return entry;
}

/**
 * The results for a profile: one ranked list of cards, each labelled with the players who can apply.
 *
 * Per player: take the top `perPlayer` (default 5) eligible cards by net value (bonus minus the first-year fee), or by raw bonus
 * value when `rankBy` is "raw". For each "as high as" card among them,
 * add one backup: the best-ranked card below the cutoff whose offer is not a ceiling and does not need an NLL offer.
 * Cards that lead to a program the household targets come first, then value. Then combine the players' lists into one and rank it by value (the highest value any player gets from a card; ties by id).
 * Players who want to get or stay under 5/24 and are at 4/24 or more also get a "Best Personal Cards" section.
 * Pure: the inputs are never changed. docs/questionnaire-design.md, Results.
 */
export function recommend(profile: Profile, data: EngineData, opts: { perPlayer?: number; rankBy?: RankBy } = {}): Results {
  const perPlayer = opts.perPlayer ?? 5;
  const rankBy = opts.rankBy ?? "net";
  const unlocks = unlockStatus(profile.players, data.currencies);

  const standings: Results["players"] = [];
  const listingsByPlayer = new Map<string, Listing[]>();
  const bestPersonal: Results["bestPersonal"] = [];

  for (const player of profile.players) {
    const derived = computeDerived(player, data.catalog);
    const ctx: ExclusionContext = {
      household: profile.household, derived, catalog: data.catalog, currencies: data.currencies, programs: data.programs,
      unlock: unlocks.get(player.name)!, marriottMatrix: data.marriottMatrix,
    };
    standings.push({
      name: player.name, x24: derived.x24, overFiveTwentyFour: derived.overFiveTwentyFour,
      amexCredit: derived.amexCredit, amexCharge: derived.amexCharge, chaseBusinessOpen: derived.chaseBusinessOpen,
    });

    const candidates = candidatesFor(player, data, ctx, rankBy);
    const listing = (c: Candidate, backup: boolean): Listing => ({
      cardId: c.card.id, bonus: c.bonus, net: c.net, value: c.value, viaNllOnly: c.viaNllOnly, backup, targeted: c.targeted,
    });
    const top = candidates.slice(0, perPlayer);
    const list = top.map((c) => listing(c, false));
    const ceilings = top.filter((c) => c.card.welcomeBonus?.ceiling).length;
    const backups = candidates
      .slice(perPlayer)
      .filter((c) => !c.card.welcomeBonus?.ceiling && !c.viaNllOnly)
      .slice(0, ceilings);
    for (const c of backups) list.push(listing(c, true));
    listingsByPlayer.set(player.name, list);

    if (player.wantsUnder524 && derived.x24 >= 4) {
      // The main list hides cards that would count toward 5/24; these are the best personal cards to consider instead.
      const relaxed = { ...player, wantsUnder524: false };
      const cards = candidatesFor(relaxed, data, ctx, rankBy).filter((c) => c.card.kind === "personal").slice(0, BEST_PERSONAL_COUNT);
      bestPersonal.push({
        player: player.name,
        cards: cards.map((c) => entryFor(c.card, [c.viaNllOnly ? { name: player.name, viaNllOnly: true } : { name: player.name }], c.bonus, c.net)),
      });
    }
  }

  // Combine the players' lists into one, then rank it by value. A card several players have is ranked at the highest
  // value any of them gets from it (values differ with each player's unlocked currencies).
  const merged = new Map<string, { bonus: number; net: number; value: number; targeted: boolean; players: ResultEntry["players"] }>();
  for (const player of profile.players) {
    for (const l of listingsByPlayer.get(player.name)!) {
      const label: ResultEntry["players"][number] = { name: player.name };
      if (l.viaNllOnly) label.viaNllOnly = true;
      if (l.backup) label.backup = true;
      const seen = merged.get(l.cardId);
      if (!seen) merged.set(l.cardId, { bonus: l.bonus, net: l.net, value: l.value, targeted: l.targeted, players: [label] });
      else {
        seen.bonus = Math.max(seen.bonus, l.bonus);
        seen.net = Math.max(seen.net, l.net);
        seen.value = Math.max(seen.value, l.value);
        seen.targeted = seen.targeted || l.targeted;
        seen.players.push(label);
      }
    }
  }
  const byId = new Map(data.catalog.map((c) => [c.id, c]));
  const ranked = [...merged.entries()]
    .sort(([ai, a], [bi, b]) => Number(b.targeted) - Number(a.targeted) || b.value - a.value || (ai < bi ? -1 : 1))
    .map(([id, m]) => entryFor(byId.get(id)!, m.players, m.bonus, m.net));

  return { players: standings, ranked, bestPersonal };
}
